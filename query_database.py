"""
Utility script to query and view data from PostgreSQL database (project_details only)
"""
import asyncio
import logging
from save_project.db_handler import get_db_handler, close_db_handler

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


async def show_statistics():
    """Show database statistics"""
    db = await get_db_handler()
    with db.conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM project_details")
        count = cur.fetchone()[0]
    logger.info("\n" + "="*60)
    logger.info("📊 DATABASE STATISTICS")
    logger.info("="*60)
    logger.info(f"Project details: {count}")


async def get_project_detail(project_id: str):
    """Get detail_result for a project"""
    db = await get_db_handler()
    with db.conn.cursor() as cur:
        cur.execute(
            "SELECT project_id, detail_result, http_status, created_at FROM project_details WHERE project_id = %s",
            (project_id,),
        )
        row = cur.fetchone()
    if not row:
        logger.info(f"❌ Project {project_id} not found")
        return
    import json
    pid, detail, status, created = row
    logger.info("\n" + "="*60)
    logger.info(f"🏗  PROJECT DETAIL: {pid}")
    logger.info("="*60)
    logger.info(f"HTTP status: {status}")
    logger.info(f"Created: {created}")
    logger.info("\nDetail (JSON):")
    logger.info(json.dumps(detail, indent=2, default=str))


async def list_latest(limit: int = 10):
    """List latest project_ids"""
    db = await get_db_handler()
    with db.conn.cursor() as cur:
        cur.execute(
            "SELECT project_id, http_status, created_at FROM project_details ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )
        rows = cur.fetchall()
    logger.info("\n" + "="*60)
    logger.info(f"📋 LATEST {limit} PROJECT DETAILS")
    logger.info("="*60)
    for r in rows:
        logger.info(f"  {r[0]}  |  status={r[1]}  |  {r[2]}")


async def export_to_csv(output_file: str):
    """Export project_details to CSV (project_id, http_status, created_at; detail_result as JSON string)"""
    import csv
    db = await get_db_handler()
    with db.conn.cursor() as cur:
        cur.execute("SELECT project_id, detail_result, http_status, created_at FROM project_details")
        rows = cur.fetchall()
    if not rows:
        logger.info("⚠️ No data in project_details")
        return
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['project_id', 'detail_result', 'http_status', 'created_at'])
        for r in rows:
            import json
            w.writerow([r[0], json.dumps(r[1], default=str), r[2], r[3]])
    logger.info(f"✅ Exported {len(rows)} rows to {output_file}")


async def main_menu():
    """Interactive menu"""
    try:
        logger.info("\n" + "="*60)
        logger.info("🗄️  DATABASE QUERY UTILITY (project_details)")
        logger.info("="*60)
        logger.info("\n1. Show statistics")
        logger.info("2. List latest project details")
        logger.info("3. Get project detail by ID")
        logger.info("4. Export project_details to CSV")
        logger.info("5. Exit")
        choice = input("\nEnter choice (1-5): ").strip()

        if choice == "1":
            await show_statistics()
        elif choice == "2":
            n = input("How many? (default 10): ").strip() or "10"
            await list_latest(int(n))
        elif choice == "3":
            pid = input("Project ID: ").strip()
            if pid:
                await get_project_detail(pid)
        elif choice == "4":
            path = input("Output CSV path: ").strip()
            if path:
                await export_to_csv(path)
        elif choice == "5":
            logger.info("\n👋 Goodbye!")
            return False
        else:
            logger.info("❌ Invalid choice")
        return True
    except KeyboardInterrupt:
        logger.info("\n\n👋 Goodbye!")
        return False


async def run():
    try:
        await get_db_handler()
        logger.info("✅ Connected to database\n")
        while True:
            if not await main_menu():
                break
            input("\nPress Enter to continue...")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        await close_db_handler()


if __name__ == "__main__":
    asyncio.run(run())
