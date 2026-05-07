import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from playwright.async_api import async_playwright

app = FastAPI()

# Secrets ထဲက ယူမယ်
G_EMAIL = os.getenv("G_EMAIL")
G_PASS = os.getenv("G_PASS")
SESSION_DIR = "/app/session_data"

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ATOM AI</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/vs2015.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        :root { --bg: #1a1a1a; --card: #222; --gold: #f1c40f; }
        body { margin: 0; background: var(--bg); color: white !important; font-family: sans-serif; overflow: hidden; }
        .wrapper { display: flex; flex-direction: column; height: 100vh; max-width: 600px; margin: 0 auto; background: var(--card); }
        header { padding: 15px; text-align: center; border-bottom: 1px solid #333; color: var(--gold); font-weight: bold; letter-spacing: 2px; }
        #chat-box { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; background: inset 0 0 10px #000; }
        .msg { max-width: 90%; padding: 15px; border-radius: 18px; font-size: 15px; line-height: 1.6; word-wrap: break-word; color: white !important; }
        .user { align-self: flex-end; background: linear-gradient(145deg, #d4af37, #f1c40f); color: black !important; font-weight: bold; }
        .bot { align-self: flex-start; background: #2a2a2a; border: 1px solid #333; box-shadow: 5px 5px 15px #0d0d0d; }
        pre { background: #1e1e1e !important; border-radius: 10px; padding: 15px; margin: 10px 0; overflow-x: auto; }
        .input-area { padding: 15px; display: flex; gap: 10px; border-top: 1px solid #333; }
        input { flex: 1; padding: 15px; border-radius: 30px; border: none; background: #1a1a1a; color: white; outline: none; }
        button { padding: 10px 25px; border-radius: 30px; border: 1px solid #d4af37; background: transparent; color: #f1c40f; cursor: pointer; font-weight: bold; }
    </style>
</head>
<body>
    <div class="wrapper">
        <header>ATOM AI CONTENT WRITER</header>
        <div id="chat-box"></div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Ask anything..." autocomplete="off">
            <button id="sendBtn">Send</button>
        </div>
    </div>
    <script>
        const box = document.getElementById('chat-box');
        const input = document.getElementById('userInput');
        const btn = document.getElementById('sendBtn');
        function format(t) {
            t = t.replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>');
            t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
            return t.replace(/\\n/g, '<br>');
        }
        async function ask() {
            const q = input.value.trim();
            if(!q || btn.disabled) return;
            input.value = ''; btn.disabled = true;
            box.innerHTML += `<div class="msg user">${q}</div>`;
            const tid = 't-' + Date.now();
            box.innerHTML += `<div class="msg bot" id="${tid}">Thinking...</div>`;
            box.scrollTop = box.scrollHeight;
            try {
                const r = await fetch("/ask?q=" + encodeURIComponent(q));
                const d = await r.json();
                const target = document.getElementById(tid);
                if(d.answer) {
                    target.innerHTML = format(d.answer);
                    target.querySelectorAll('pre code').forEach(el => hljs.highlightElement(el));
                    target.innerHTML += `<br><button style="color:#f1c40f; background:none; border:none; cursor:pointer;" onclick="navigator.clipboard.writeText(\`${d.answer.replace(/`/g, '\\\\`')}\`)">Copy Text</button>`;
                } else if(d.error) { target.innerText = "Error: " + d.error; }
            } catch (e) { document.getElementById(tid).innerText = "Connection Error."; }
            btn.disabled = false; box.scrollTop = box.scrollHeight;
        }
        btn.onclick = ask;
        input.onkeydown = (e) => { if(e.key === "Enter") ask(); };
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home(): return HTML_CONTENT

@app.get("/ask")
async def ask_gemini(q: str):
    async with async_playwright() as p:
        # Persistent context သုံးပြီး login ကို folder ထဲမှာ မှတ်ထားခိုင်းမယ်
        context = await p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        page = context.pages[0] if context.pages else await context.new_page()
        try:
            await page.goto("https://gemini.google.com/app", timeout=60000)
            
            # Login မဝင်ရသေးရင် ဝင်ပေးမယ်
            if await page.query_selector("text=Sign in"):
                await page.click("text=Sign in")
                await page.wait_for_selector('input[type="email"]')
                await page.fill('input[type="email"]', G_EMAIL)
                await page.click('#identifierNext')
                await page.wait_for_selector('input[type="password"]', timeout=10000)
                await page.fill('input[type="password"]', G_PASS)
                await page.click('#passwordNext')
                await asyncio.sleep(15) # 2FA စောင့်ချိန်

            # စာရိုက်ခြင်း
            await page.wait_for_selector('div[role="textbox"]', timeout=30000)
            await page.fill('div[role="textbox"]', q)
            await page.keyboard.press("Enter")
            
            # အဖြေယူခြင်း
            ans_text = ""
            for _ in range(20):
                await asyncio.sleep(1.5)
                res = await page.query_selector_all(".message-content")
                if res:
                    last = res[-1]
                    text_el = await last.query_selector(".model-response-text, div.markdown")
                    if text_el:
                        ans_text = await text_el.inner_text()
                        if ans_text.strip(): break
            
            await context.close()
            return {"answer": ans_text}
        except Exception as e:
            if 'context' in locals(): await context.close()
            return {"error": str(e)}
