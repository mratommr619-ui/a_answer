import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from playwright.async_api import async_playwright

app = FastAPI()

SESSION_DATA = os.getenv("SESSION_DATA")

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ATOM AI CONTENT WRITER</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/vs2015.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        :root { --bg: #1a1a1a; --gold: #f1c40f; --card: #222; }
        body { margin: 0; background: var(--bg); color: white !important; font-family: sans-serif; overflow: hidden; }
        .wrapper { display: flex; flex-direction: column; height: 100vh; max-width: 600px; margin: 0 auto; background: var(--card); }
        header { padding: 15px; text-align: center; border-bottom: 1px solid #333; color: var(--gold); font-weight: bold; }
        #chat-box { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
        .msg { max-width: 85%; padding: 12px; border-radius: 15px; font-size: 15px; line-height: 1.5; word-wrap: break-word; }
        .user { align-self: flex-end; background: var(--gold); color: black; font-weight: bold; }
        .bot { align-self: flex-start; background: #333; border: 1px solid #444; color: white !important; }
        .img-card { margin-top: 10px; border-radius: 10px; overflow: hidden; border: 1px solid var(--gold); }
        .img-card img { width: 100%; display: block; }
        .input-area { padding: 15px; display: flex; gap: 10px; border-top: 1px solid #333; }
        input { flex: 1; padding: 12px; border-radius: 20px; border: none; background: #333; color: white; outline: none; }
        button { padding: 10px 20px; border-radius: 20px; border: 1px solid var(--gold); background: transparent; color: var(--gold); cursor: pointer; }
        pre { background: #1e1e1e !important; border-radius: 8px; padding: 10px; overflow-x: auto; }
        .copy-btn { margin-top: 5px; color: var(--gold); background: none; border: none; cursor: pointer; font-size: 12px; }
    </style>
</head>
<body>
    <div class="wrapper">
        <header>ATOM AI CONTENT WRITER</header>
        <div id="chat-box"></div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Ask anything (Unlimited)..." autocomplete="off">
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
                    target.innerHTML += `<br><button class="copy-btn" onclick="navigator.clipboard.writeText(\`${d.answer.replace(/`/g, '\\\\`')}\`)">Copy Text</button>`;
                }
                if(d.images && d.images.length > 0) {
                    d.images.forEach(src => {
                        target.innerHTML += `<div class="img-card"><img src="${src}" onclick="window.open('${src}', '_blank')"></div>`;
                    });
                }
                if(d.error) target.innerHTML = `<span style="color:red">Error: ${d.error}</span>`;
            } catch (e) { document.getElementById(tid).innerText = "Server Error."; }
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
    if not SESSION_DATA: return {"error": "SESSION_DATA missing!"}
    with open("auth.json", "w") as f: f.write(SESSION_DATA)
    
    async with async_playwright() as p:
        # Browser ကို ပိုပြီး Stealth ဖြစ်အောင် Argument တွေ ထပ်တိုးထားပါတယ်
        browser = await p.chromium.launch(headless=True, args=[
            '--no-sandbox', 
            '--disable-setuid-sandbox', 
            '--disable-blink-features=AutomationControlled',
            '--use-gl=desktop'
        ])
        try:
            context = await browser.new_context(
                storage_state="auth.json",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Error တက်နေတဲ့ stealth_async ကို ဖြုတ်ပြီး Manual Injection သုံးထားပါတယ်
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            await page.goto("https://gemini.google.com/app", timeout=60000)
            
            # စာရိုက်တဲ့ အပိုင်း
            await page.wait_for_selector('div[role="textbox"]', timeout=30000)
            await page.fill('div[role="textbox"]', q)
            await page.keyboard.press("Enter")
            
            # အဖြေစောင့်တဲ့ Logic ကို ပိုမြန်အောင် ပြင်ထားပါတယ်
            ans_text = ""
            imgs = []
            for _ in range(20):
                await asyncio.sleep(2)
                responses = await page.query_selector_all(".message-content")
                if responses:
                    last = responses[-1]
                    text_el = await last.query_selector(".model-response-text, div.markdown")
                    if text_el:
                        ans_text = await text_el.inner_text()
                        if ans_text.strip():
                            # ပုံရှိမရှိ စစ်မယ်
                            img_els = await last.query_selector_all("img")
                            imgs = [await i.get_attribute("src") for i in img_els if await i.get_attribute("src") and "https" in (await i.get_attribute("src"))]
                            break
            
            await browser.close()
            return {"answer": ans_text, "images": imgs}
        except Exception as e:
            if 'browser' in locals(): await browser.close()
            return {"error": str(e)}
