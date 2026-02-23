import asyncio
import math
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright
from dotenv import load_dotenv

from login import login
from get_total_count import get_total_count
from get_project import get_project
from get_project_detail import get_project_detail
from save_project.save_detail_only import save_project_detail_result_only
from graphql_client import GraphQLClient
from checkpoint import CheckpointManager

from save_project.db_handler import get_db_handler, close_db_handler

# load .env with utf-8-sig to strip BOM if present
load_dotenv(encoding='utf-8-sig')

if getattr(sys, 'frozen', False):
    base_path = Path(sys._MEIPASS)
else:
    base_path = Path(__file__).parent
chromium_path = base_path / "chromium" / "chrome.exe"

FIXED_DELAY = 1.0


async def run_scraper(email, password, headless=False):
    checkpoint_manager = CheckpointManager()
    
    try:
        await get_db_handler()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                executable_path=str(chromium_path)
            )
            context = await browser.new_context()
            page = await context.new_page()
            
            client = GraphQLClient(
                page,
                timeout=120000,
                max_retries=5,
                base_backoff=1.0,
                max_backoff=60.0,
                min_pacing=0.5,
                max_pacing=3.0
            )
            
            await login(page, email, password)
            
            total_count = await get_total_count(client)
            if total_count == 0:
                await browser.close()
                return
            
            scraped_ids = checkpoint_manager.get_scraped_project_ids()
            start_page = checkpoint_manager.get_resume_page(1)
            
            total_pages = max(1, math.ceil(total_count))
            for page_num in range(start_page, total_pages + 1):
                projects = await get_project(client, page_num)
                
                if projects is None:
                    await process_retry_queue(client)
                    continue
                
                if isinstance(projects, dict):
                    projects = [projects]
                
                page_processed = await process_projects(
                    projects,
                    client,
                    checkpoint_manager,
                    page_num
                )
                
                await process_retry_queue(client)
                
                # Delay between pages
                await asyncio.sleep(FIXED_DELAY)
            
            if client.get_retry_queue_size() > 0:
                await client.process_retry_queue()
            
            await browser.close()
    
    except Exception as e:
        print(f"[ERROR] Scraper failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            await close_db_handler()
        except:
            pass


async def process_projects(projects, client, checkpoint_manager, page_num):
    page_processed = False
    
    for item in projects:
        project = item.get("project") if isinstance(item, dict) and "project" in item else item

        if not project:
            continue
        
        project_id = project.get("id")
        if not project_id:
            continue
        
        if checkpoint_manager.is_project_scraped(project_id):
            continue
        
        # if project.get("requireAdditionalLicense", False) or project.get("requiredProductForRoadblock"):
        #     continue
        # print("---------4-----------")
        
        detail = None
        http_status = 200
        
        try:
            detail_result = await get_project_detail(client, project_id, page_number=page_num)
            if isinstance(detail_result, tuple):
                detail, http_status = detail_result
            else:
                detail = detail_result
                http_status = None
        except Exception as e:
            print(f"[ERROR] Failed to get detail for {project_id}: {e}")
        
        try:
            if detail is not None:
                await save_project_detail_result_only(project_id, detail, http_status)
            checkpoint_manager.save_checkpoint(page_num, project_id)
            page_processed = True
        except Exception as e:
            print(f"[ERROR] Failed to save project {project_id}: {e}")
            continue
        
        await asyncio.sleep(FIXED_DELAY)
    
    return page_processed


async def process_retry_queue(client):
    if client.get_retry_queue_size() > 0:
        await client.process_retry_queue()


def main():
    print('--------------------------bot working -----------------------------')
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    
    if not email or not password:
        print("Credentials not found in .env file")
        email = input("Enter email: ").strip()
        password = input("Enter password: ").strip()
    
    if not email or not password:
        print("ERROR: Email and password are required")
        sys.exit(1)
   
    try:
        asyncio.run(run_scraper(email, password, headless=True))
    except KeyboardInterrupt:
        print("\n\nWARNING: Scraping interrupted by user")
        print("Progress has been saved in checkpoint file")
        sys.exit(0)


if __name__ == "__main__":
    main()
