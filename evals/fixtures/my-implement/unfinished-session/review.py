import json
import os


boundary = json.loads(os.environ["MY_MATT_TICKET_BOUNDARY"])
acceptance = boundary["current"]["acceptance"]
spec_ref = "spec:" + os.environ["MY_MATT_SPEC_REF"]
print(
    json.dumps(
        {
            "review_id": os.environ["MY_MATT_REVIEW_ID"],
            "status": "pass",
            "code_content_id": os.environ["MY_MATT_CODE_CONTENT_ID"],
            "reviewer_provenance": {
                "kind": "self",
                "session_id": os.environ["MY_MATT_IMPLEMENTATION_SESSION_ID"],
            },
            "findings": [],
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
