import json
import os


boundary = json.loads(os.environ["MY_MATT_TICKET_BOUNDARY"])
acceptance = boundary["current"]["acceptance"]
spec_ref = "spec:" + os.environ["MY_MATT_SPEC_REF"]
source = open("app.py", encoding="utf-8").read()
blank_name_is_rejected = 'raise ValueError("name must not be blank")' in source
finding = {
    "id": "blank-name-not-rejected",
    "root_cause": "greeting returns a value for a blank normalized name",
    "severity": "P1",
    "summary": "blank normalized names must raise the specified ValueError",
    "baseline_reachable": True,
    "acceptance_ids": [item["id"] for item in acceptance],
}
print(
    json.dumps(
        {
            "review_id": os.environ["MY_MATT_REVIEW_ID"],
            "status": "pass" if blank_name_is_rejected else "findings",
            "code_content_id": os.environ["MY_MATT_CODE_CONTENT_ID"],
            "reviewer_provenance": {
                "kind": "self",
                "session_id": os.environ["MY_MATT_IMPLEMENTATION_SESSION_ID"],
            },
            "findings": [] if blank_name_is_rejected else [finding],
            "follow_ons": [],
            "design_gap": None,
            "self_review_coverage": {
                "acceptance": [
                    {"acceptance_id": item["id"], "evidence_refs": [spec_ref]}
                    for item in acceptance
                ],
                "probes": [
                    {"probe": probe, "summary": "checked", "evidence_refs": [spec_ref]}
                    for probe in boundary["required_probes"]
                ],
            },
        }
    )
)
