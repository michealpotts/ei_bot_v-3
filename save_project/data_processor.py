"""Process scraped project data before saving - filter stages to awarded builder only."""
import re
from typing import Any, Dict, Optional


def _extract_awarded_builder_name(project_activity_logs: list) -> Optional[str]:
    """
    Extract the awarded builder name from projectActivityLogs.
    Looks for messageType 'stage.tender.won' and parses the builder name from the message.
    Example message: "Tender marked as Awarded to Black Sheep Construct."
    """
    if not project_activity_logs or not isinstance(project_activity_logs, list):
        return None
    for log in project_activity_logs:
        if not isinstance(log, dict):
            continue
        if log.get("messageType") != "stage.tender.won":
            continue
        message = log.get("message") or ""
        match = re.search(r"Tender marked as Awarded to (.+?)\.?\s*$", message, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _is_awarded_builder_stage(stage: dict, awarded_builder_name: str) -> bool:
    """Check if the stage's builderDetails matches the awarded builder."""
    builder_details = stage.get("builderDetails")
    if not builder_details or not isinstance(builder_details, dict):
        return False
    builder_name = builder_details.get("name")
    if not builder_name or not isinstance(builder_name, str):
        return False
    return builder_name.strip() == awarded_builder_name.strip()


def filter_stages_to_awarded_builder_only(detail: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter project stages to keep only those with the awarded builder.
    Uses projectActivityLogs to find the awarded builder (messageType: stage.tender.won),
    then filters stages to retain only stages where builderDetails.name matches.
    Returns a copy of detail with updated stages (does not mutate the input).
    """
    if not detail or not isinstance(detail, dict):
        return detail or {}

    detail = dict(detail)
    project = detail.get("project")
    if not project or not isinstance(project, dict):
        return detail

    project = dict(project)
    stages = project.get("stages")
    if not stages or not isinstance(stages, list):
        return detail

    awarded_builder_name = _extract_awarded_builder_name(detail.get("projectActivityLogs"))
    if not awarded_builder_name:
        return detail

    filtered_stages = [s for s in stages if isinstance(s, dict) and _is_awarded_builder_stage(s, awarded_builder_name)]
    project["stages"] = filtered_stages
    detail["project"] = project

    # Remove fields not needed for saved data__typename
    detail.pop("projectActivityLogs", None)
    detail.pop("__typename", None)
    detail.pop("notes", None)

    return_detail = detail['project'];
    return_detail.pop("__typename", None)
    return_detail.pop("trades", None)
    
    return return_detail
