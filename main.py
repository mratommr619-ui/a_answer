import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import playwright_stealth  # import ပုံစံကို ပြောင်းလိုက်ပါပြီ
from playwright.async_api import async_playwright

app = FastAPI()

SESSION_DATA = os.getenv("SESSION_DATA")

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Atom Auto Content Writer</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root {
            --bg-color: #1a1a1a;
            --container-bg: #222222;
            --gold-light: #f1c40f;
            --gold-dark: #d4af37;
            --shadow-out: 6px 6px 12px #0d0d0d, -6px -6px 12px #272727;
            --shadow-in: inset 4px 4px 8px #0d0d0d, inset -4px -4px 8px #272727;
            --text-color: #e0e0e0;
        }
        body { font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; align-items: center; background: var(--bg-color); margin: 0; padding: 20px; color: var(--text-color); }
        .chat-container { width: 100%; max-width: 550px; background: var(--container-bg); padding: 30px; border-radius: 30px; box-shadow: var(--shadow-out); border: 1px solid #333; }
        h2 { color: var(--gold-light); text-align: center; text-transform: uppercase; letter-spacing: 2px; }
        #chat-box { height: 400px; overflow-y: auto; margin-bottom: 25px; padding: 20px; border-radius: 20px; background: var(--container-bg); box-shadow: var(--shadow-in); display: flex; flex-direction: column; }
        .msg { margin: 10px 0; padding: 12px 18px; border-radius: 15px; max-width: 85%; line-height: 1.6; }
        .user { align-self: flex-end; background: linear-gradient(145deg, #d4af37, #f1c40f); color: #000; font-weight: 600; }
        .bot { align-self: flex-start; background: #2a2a2a; border: 1px solid #333; }
        .input-area { display: flex; gap: 15px; }
        input { flex: 1; padding: 15px; border: none; border-radius: 25px; background: var(--container-bg); color: var(--text-color); box-shadow: var(--shadow-in); outline: none; }
        button { padding: 10px 25px; background: var(--container-bg); color: var(--gold-light); border: 1px solid var(--gold-dark); border-radius: 25px; cursor: pointer; font-weight: 700; box-shadow: var(--shadow-out); }
        button:hover { background: var(--gold-light); color: #000; }
        button:disabled { opacity: 0.5; }
        .blink { animation: blinker 1.5s linear infinite; }
        @keyframes blinker { 50% { opacity: 0.5; } }
    </style>
</head>
<body>
    <div class="chat-container">
        <h2>Atom Auto Content Writer</h2>
        <div id="chat-box"></div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="မေးခွန်းရိုက်ပါ..." onkeypress="if(event.key==='Enter') ask()">
            <button onclick="ask()" id="sendBtn">Send</button>
        </div>
    </div>
    <script>
        async function ask() {
            const input = document.getElementById('userInput');
            const btn = document.getElementById('sendBtn');
            const box = document.getElementById('chat-box');
            if(!input.value.trim()) return;
            const q = input.value;
            box.innerHTML += `<div class="msg user">${q}</div>`;
            input.value = ''; btn.disabled = true;
            box.innerHTML += `<div class="msg bot"><i>Message received.</i></div>`;
            const tid = 't-' + Date.now();
            box.innerHTML += `<div class="msg bot blink" id="${tid}">Thinking....</div>`;
            box.scrollTop = box.scrollHeight;
            try {
                const r = await fetch(`/ask?q=${encodeURIComponent(q)}`);
                const d = await r.json();
                document.getElementById(tid).innerText = d.answer || "Error: " + d.error;
                document.getElementById(tid).classList.remove('blink');
            } catch (e) { document.getElementById(tid).innerText = "Error: Connection failed."; }
            btn.disabled = false; box.scrollTop = box.scrollHeight;
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_CONTENT

@app.get("/ask")
async def ask_gemini(q: str):
    if not SESSION_DATA:
        return {"error": "SESSION_DATA variable is missing!"}

    with open("auth.json", "w") as f:
        f.write(SESSION_DATA)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(storage_state="auth.json")
        page = await context.new_page()
        
        # Stealth mode ကို Dynamic check လုပ်ပြီး သုံးခြင်း (Error ကင်းစေရန်)
        if hasattr(playwright_stealth, 'stealth_async'):
            await playwright_stealth.stealth_async(page)
        elif hasattr(playwright_stealth, 'stealth_page_async'):
            await playwright_stealth.stealth_page_async(page)
        
        try:
            await page.goto("https://gemini.google.com/app", timeout=60000)
            await page.fill('div[role="textbox"]', q)
            await page.keyboard.press("Enter")
            await asyncio.sleep(12)
            
            responses = await page.query_selector_all(".message-content")
            answer = await responses[-1].inner_text() if responses else "No response from Gemini."
            await browser.close()
            return {"answer": answer}
        except Exception as e:
            await browser.close()
            return {"error": str(e)}
