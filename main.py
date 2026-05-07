import os
import json
import asyncio
from fastapi import FastAPI
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

app = FastAPI()

# Render က ပေးတဲ့ Environment Variable ကနေ Session ကို ဖတ်မယ်
SESSION_DATA = os.getenv("SESSION_DATA")

@app.get("/")
async def home():
    return {"status": "Online", "message": "Gemini Bridge is ready!"}

@app.get("/ask")
async def ask_gemini(q: str):
    if not SESSION_DATA:
        return {"error": "SESSION_DATA variable is missing!"}

    # Session data ကို ယာယီဖိုင်အဖြစ် သိမ်းဆည်းခြင်း
    with open("auth.json", "w") as f:
        f.write(SESSION_DATA)

    async with async_playwright() as p:
        # Render RAM သက်သာစေရန် Setting များ
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        
        context = await browser.new_context(storage_state="auth.json")
        page = await context.new_page()
        await stealth_async(page)
        
        try:
            await page.goto("https://gemini.google.com/app", timeout=60000)
            
            # မေးခွန်းရိုက်ခြင်း
            await page.fill('div[role="textbox"]', q)
            await page.keyboard.press("Enter")
            
            # AI အဖြေပေးသည်အထိ စောင့်ခြင်း
            await asyncio.sleep(10)
            
            # နောက်ဆုံးအဖြေကို ယူခြင်း
            responses = await page.query_selector_all(".message-content")
            answer = await responses[-1].inner_text() if responses else "Error: No response"
            
            await browser.close()
            return {"question": q, "answer": answer}
            
        except Exception as e:
            await browser.close()
            return {"error": str(e)}
