from .db_handler import get_db_handler
from .data_processor import filter_stages_to_awarded_builder_only


async def save_project_detail_result_only(project_id: str, detail: dict, http_status=None):
    """Save only the raw project detail result (projectForSlider) to the database.
    Before saving, filters stages to keep only awarded builder info (from projectActivityLogs)."""
    if not detail or not isinstance(detail, dict):
        return False
    detail = filter_stages_to_awarded_builder_only(detail)
    db = await get_db_handler()
    await db.save_project_detail_result(project_id, detail, http_status)
    return True
