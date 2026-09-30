"""Capture immutable inputs before the workflow simplification removes v1."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


OLD_CHAIN = (
    "my-grill-with-docs", "my-grilling", "my-domain-modeling",
    "my-requirement-analysis", "my-to-spec", "my-to-tickets", "my-implement",
    "my-tdd", "my-code-review", "my-review-design",
)
_LINK = re.compile(r"!?\[[^\]]*\]\((<[^>]+>|[^)\s]+)(?:\s+[^)]*)?\)")


def _link_text(text: str) -> str:
    """Fenced examples contribute characters but are not live Markdown links."""
    lines = []
    fence = None
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return "\n".join(lines)


def measure_markdown(skills_root: Path, names: list[str] | tuple[str, ...]) -> dict:
    """Count the in-Skill Markdown closure, deduplicating decoded file content."""
    contents: set[str] = set()
    inventory = []
    for name in names:
        root = (skills_root / name).resolve()
        pending = [root / "SKILL.md"]
        seen: set[Path] = set()
        while pending:
            path = pending.pop()
            if path in seen:
                continue
            seen.add(path)
            text = path.read_text(encoding="utf-8")
            contents.add(text)
            inventory.append({
                "path": f"{name}/{path.relative_to(root).as_posix()}",
                "characters": len(text),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
            for match in _LINK.finditer(_link_text(text)):
                target = urlsplit(match.group(1).strip("<>"))
                raw = unquote(target.path)
                if target.scheme or target.netloc or not raw or raw.startswith("/"):
                    continue
                candidate = (path.parent / raw).resolve()
                if candidate.suffix.lower() == ".md" and candidate.is_relative_to(root):
                    pending.append(candidate)
    return {
        "characters": sum(map(len, contents)),
        "reachable_files": len(inventory),
        "unique_contents": len(contents),
        "files": sorted(inventory, key=lambda item: item["path"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills_root", type=Path)
    args = parser.parse_args()
    print(json.dumps(measure_markdown(args.skills_root, OLD_CHAIN), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
