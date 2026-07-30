import unittest
from pathlib import Path

from tools.workflow_lib.tickets import (
    TicketGraphError,
    TicketParseError,
    TicketSelectionError,
    build_ticket_graph,
    completion_problems,
    implementation_candidates,
    parse_ticket,
    select_implementation_ticket,
    select_wayfinder_ticket,
    ticket_eligibility,
    wayfinder_candidates,
    wayfinder_eligibility,
)


def ticket_text(
    *,
    identifier: str,
    title: str,
    ticket_kind: str | None = "implementation",
    status: str = "ready-for-agent",
    blocked_by: str = "[]",
    claimed_by: str = "",
    tags: str = "[]",
    sequence: int | None = None,
    acceptance: str = "- [ ] works",
) -> str:
    kind_line = "" if ticket_kind is None else f"ticket_kind: {ticket_kind}\n"
    sequence_line = "" if sequence is None else f"sequence: {sequence}\n"
    return (
        "---\n"
        f"id: {identifier}\n"
        f"title: {title}\n"
        f"{kind_line}"
        f"status: {status}\n"
        f"blocked_by: {blocked_by}\n"
        f"claimed_by: {claimed_by}\n"
        f"tags: {tags}\n"
        f"{sequence_line}"
        "---\n\n"
        f"# {title}\n\n"
        "## Acceptance criteria\n\n"
        f"{acceptance}\n"
    )


def parse(
    identifier: str,
    *,
    path: str | None = None,
    **kwargs: object,
):
    return parse_ticket(
        ticket_text(identifier=identifier, title=kwargs.pop("title", identifier), **kwargs),
        path=Path(path or f"tickets/{identifier}.md"),
    )


class TicketParsingTests(unittest.TestCase):
    def test_blocked_by_requires_structured_yaml_list(self):
        with self.assertRaisesRegex(TicketParseError, "blocked_by.*YAML list"):
            parse("first", blocked_by="first-ticket")

    def test_blocked_by_cannot_be_omitted(self):
        text = ticket_text(identifier="first", title="First").replace(
            "blocked_by: []\n", ""
        )

        with self.assertRaisesRegex(TicketParseError, "blocked_by.*YAML list"):
            parse_ticket(text, path=Path("tickets/first.md"))

    def test_claimed_by_cannot_be_omitted(self):
        text = ticket_text(identifier="first", title="First").replace(
            "claimed_by: \n", ""
        )

        with self.assertRaisesRegex(TicketParseError, "claimed_by.*required"):
            parse_ticket(text, path=Path("tickets/first.md"))

    def test_explicit_empty_claimed_by_is_unclaimed(self):
        ticket = parse("first", claimed_by="")

        self.assertIsNone(ticket.claimed_by)

    def test_claimed_by_must_be_a_scalar(self):
        with self.assertRaisesRegex(TicketParseError, "claimed_by.*string"):
            parse("first", claimed_by="[]")

    def test_parses_block_lists_and_checkbox_states(self):
        ticket = parse(
            "next",
            blocked_by="\n  - first",
            acceptance="- [x] one\n- [ ] two",
        )

        self.assertEqual(("first",), ticket.blocked_by)
        self.assertEqual(1, ticket.checked_acceptance)
        self.assertEqual(1, ticket.unchecked_acceptance)

    def test_legacy_missing_kind_remains_ambiguous(self):
        ticket = parse("legacy", ticket_kind=None)

        self.assertIsNone(ticket.ticket_kind)

    def test_rejects_unknown_ticket_kind(self):
        with self.assertRaisesRegex(TicketParseError, "ticket_kind"):
            parse("unknown", ticket_kind="research")


class TicketGraphTests(unittest.TestCase):
    def test_resolves_unambiguous_id_path_and_title_references(self):
        base = parse(
            "base",
            title="Prepare storage",
            path="tickets/01-base.md",
            status="complete",
        )
        by_id = parse("by-id", blocked_by="[base]")
        by_path = parse("by-path", blocked_by="[./tickets/01-base.md]")
        by_title = parse("by-title", blocked_by="[Prepare storage]")

        graph = build_ticket_graph((base, by_id, by_path, by_title))

        for ticket in (by_id, by_path, by_title):
            with self.subTest(ticket=ticket.identifier):
                self.assertEqual((base,), graph.blockers[ticket])

    def test_rejects_orphan_blocker_reference(self):
        with self.assertRaisesRegex(
            TicketGraphError, r"next.*orphan.*missing"
        ):
            build_ticket_graph((parse("next", blocked_by="[missing]"),))

    def test_rejects_ambiguous_title_reference(self):
        first = parse("first", title="Shared title")
        second = parse("second", title="Shared title")
        dependent = parse("dependent", blocked_by="[Shared title]")

        with self.assertRaisesRegex(
            TicketGraphError, r"dependent.*ambiguous.*Shared title"
        ):
            build_ticket_graph((first, second, dependent))

    def test_rejects_blocker_cycles(self):
        first = parse("first", blocked_by="[second]")
        second = parse("second", blocked_by="[first]")

        with self.assertRaisesRegex(
            TicketGraphError, r"cycle.*first.*second.*first"
        ):
            build_ticket_graph((first, second))


class TicketSelectionTests(unittest.TestCase):
    def test_requires_all_implementation_eligibility_gates(self):
        complete = parse("complete", status="complete")
        eligible = parse(
            "eligible",
            sequence=2,
            blocked_by="[complete]",
        )
        blocked = parse("blocked", blocked_by="[eligible]")
        claimed = parse("claimed", claimed_by="agent-a")
        legacy = parse("legacy", ticket_kind=None)
        no_acceptance = parse("no-acceptance", acceptance="- [x] done")
        wayfinder_kind = parse(
            "decision", ticket_kind="wayfinder-decision", status="ready-for-agent"
        )
        wayfinder_tag = parse("tagged", tags="[wayfinder:research]")
        graph = build_ticket_graph(
            (
                complete,
                eligible,
                blocked,
                claimed,
                legacy,
                no_acceptance,
                wayfinder_kind,
                wayfinder_tag,
            )
        )

        self.assertTrue(ticket_eligibility(eligible, graph).eligible)
        self.assertFalse(ticket_eligibility(blocked, graph).eligible)
        self.assertFalse(ticket_eligibility(claimed, graph).eligible)
        self.assertIn(
            "ticket_kind is missing or ambiguous",
            ticket_eligibility(legacy, graph).reasons,
        )
        self.assertFalse(ticket_eligibility(no_acceptance, graph).eligible)
        self.assertFalse(ticket_eligibility(wayfinder_kind, graph).eligible)
        self.assertFalse(ticket_eligibility(wayfinder_tag, graph).eligible)

    def test_automatic_selection_sorts_sequence_then_identifier(self):
        later = parse("later", sequence=3)
        second = parse("z-second", sequence=1)
        first = parse("a-first", sequence=1)
        no_sequence = parse("none")

        candidates = implementation_candidates((later, second, first, no_sequence))

        self.assertEqual(
            ["a-first", "z-second", "later", "none"],
            [ticket.identifier for ticket in candidates],
        )
        self.assertEqual("a-first", select_implementation_ticket(candidates).identifier)

    def test_explicit_invalid_selection_does_not_fall_back(self):
        claimed = parse("claimed", claimed_by="agent-a")
        ready = parse("ready")

        with self.assertRaisesRegex(
            TicketSelectionError, r"claimed.*already claimed"
        ):
            select_implementation_ticket((claimed, ready), selected="claimed")

    def test_completion_requires_checked_acceptance(self):
        pending = parse("pending")
        complete = parse("complete", acceptance="- [x] one\n- [x] two")

        self.assertIn(
            "acceptance checkboxes remain unchecked",
            completion_problems(pending),
        )
        self.assertEqual((), completion_problems(complete))


class WayfinderSelectionTests(unittest.TestCase):
    def test_frontier_requires_open_unclaimed_unblocked_decision_tickets(self):
        completed = parse(
            "completed",
            ticket_kind="wayfinder-decision",
            status="complete",
        )
        eligible = parse(
            "eligible",
            ticket_kind="wayfinder-decision",
            status="open",
            blocked_by="[completed]",
        )
        blocked = parse(
            "blocked",
            ticket_kind="wayfinder-decision",
            status="open",
            blocked_by="[eligible]",
        )
        claimed = parse(
            "claimed",
            ticket_kind="wayfinder-decision",
            status="open",
            claimed_by="agent-a",
        )
        wrong_kind = parse("implementation", ticket_kind="implementation", status="open")
        missing_kind = parse("legacy", ticket_kind=None, status="open")
        wrong_status = parse(
            "ready",
            ticket_kind="wayfinder-decision",
            status="ready-for-agent",
        )
        missing_status = parse_ticket(
            ticket_text(
                identifier="missing-status",
                title="missing-status",
                ticket_kind="wayfinder-decision",
            ).replace("status: ready-for-agent\n", ""),
            path=Path("tickets/missing-status.md"),
        )
        graph = build_ticket_graph(
            (
                completed,
                eligible,
                blocked,
                claimed,
                wrong_kind,
                missing_kind,
                wrong_status,
                missing_status,
            )
        )

        self.assertTrue(wayfinder_eligibility(eligible, graph).eligible)
        self.assertFalse(wayfinder_eligibility(blocked, graph).eligible)
        self.assertFalse(wayfinder_eligibility(claimed, graph).eligible)
        self.assertFalse(wayfinder_eligibility(wrong_kind, graph).eligible)
        self.assertFalse(wayfinder_eligibility(missing_kind, graph).eligible)
        self.assertFalse(wayfinder_eligibility(wrong_status, graph).eligible)
        self.assertFalse(wayfinder_eligibility(missing_status, graph).eligible)

    def test_frontier_sorts_and_selects_by_sequence_then_identifier(self):
        later = parse(
            "later",
            ticket_kind="wayfinder-decision",
            status="open",
            sequence=3,
        )
        second = parse(
            "z-second",
            ticket_kind="wayfinder-decision",
            status="open",
            sequence=1,
        )
        first = parse(
            "a-first",
            ticket_kind="wayfinder-decision",
            status="open",
            sequence=1,
        )
        no_sequence = parse(
            "none",
            ticket_kind="wayfinder-decision",
            status="open",
        )

        candidates = wayfinder_candidates((later, second, first, no_sequence))

        self.assertEqual(
            ["a-first", "z-second", "later", "none"],
            [ticket.identifier for ticket in candidates],
        )
        self.assertEqual(
            "a-first", select_wayfinder_ticket(candidates).identifier
        )

    def test_explicit_invalid_wayfinder_selection_does_not_fall_back(self):
        claimed = parse(
            "claimed",
            ticket_kind="wayfinder-decision",
            status="open",
            claimed_by="agent-a",
        )
        ready = parse(
            "ready",
            ticket_kind="wayfinder-decision",
            status="open",
        )

        with self.assertRaisesRegex(
            TicketSelectionError, r"claimed.*already claimed"
        ):
            select_wayfinder_ticket((claimed, ready), selected="claimed")
