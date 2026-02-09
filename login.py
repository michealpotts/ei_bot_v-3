async def login(page, email, password):
    await page.goto("https://app.estimateone.com/", wait_until="domcontentloaded")
    await page.wait_for_selector('input[type="email"]', timeout=60000)
    await page.fill('input[type="email"]', email)
    await page.fill('input[type="password"]', password)
    await page.click('button[type="submit"]')
    await page.wait_for_selector("#company-profile-menu", timeout=60000)
    print("[OK]-----------Login successful")
    return True