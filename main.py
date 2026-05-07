import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import playwright_stealth
from playwright.async_api import async_playwright

app = FastAPI()

SESSION_DATA = os.getenv("SESSION_DATA")

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>ATOM AI CONTENT WRITER</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/vs2015.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        :root {
            --bg-color: #1a1a1a;
            --container-bg: #222222;
            --gold-light: #f1c40f;
            --gold-dark: #d4af37;
            --shadow-out: 8px 8px 16px #0d0d0d, -8px -8px 16px #272727;
            --shadow-in: inset 6px 6px 12px #0d0d0d, inset -6px -6px 12px #272727;
            --text-white: #ffffff; /* အဖြူရောင်စစ်စစ် */
        }

        html, body {
            margin: 0; padding: 0; width: 100%; height: 100%;
            overflow: hidden; background: var(--bg-color);
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: var(--text-white);
        }

        .main-wrapper {
            display: flex; flex-direction: column;
            width: 100%; height: 100vh; max-width: 600px;
            margin: 0 auto; background: var(--container-bg);
            position: relative;
        }

        header { padding: 15px; text-align: center; border-bottom: 1px solid #333; }
        h2 { color: var(--gold-light); margin: 0; font-size: 18px; letter-spacing: 2px; text-transform: uppercase; }

        #chat-box {
            flex: 1; overflow-y: auto; padding: 20px;
            display: flex; flex-direction: column; gap: 15px;
            background: var(--container-bg); box-shadow: var(--shadow-in);
            margin: 10px; border-radius: 20px;
        }

        .msg {
            max-width: 90%; padding: 15px; border-radius: 18px;
            font-size: 15px; line-height: 1.6; word-wrap: break-word;
            animation: slideUp 0.3s ease;
        }

        @keyframes slideUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; } }

        .user { align-self: flex-end; background: linear-gradient(145deg, var(--gold-dark), var(--gold-light)); color: #000; font-weight: 700; }
        
        /* Bot Message - စာလုံးကို အဖြူရောင်သတ်မှတ်သည် */
        .bot { align-self: flex-start; background: #2a2a2a; border: 1px solid #333; color: var(--text-white); box-shadow: var(--shadow-out); }

        pre { margin: 10px 0; border-radius: 10px; overflow: hidden; background: #1e1e1e; }
        .hljs { padding: 15px; background: #1e1e1e !important; }

        .tools { display: flex; gap: 12px; margin-top: 12px; border-top: 1px solid #444; padding-top: 10px; }
        .icon-btn { 
            background: none; border: none; color: var(--gold-light); 
            cursor: pointer; font-size: 13px; display: flex; align-items: center; gap: 6px;
        }

        .image-gallery { display: flex; flex-direction: column; gap: 15px; margin-top: 15px; }
        .img-card { position: relative; border-radius: 12px; overflow: hidden; border: 1px solid var(--gold-dark); }
        .gemini-img { width: 100%; display: block; }
        
        .dl-btn {
            position: absolute; top: 10px; right: 10px;
            background: rgba(0,0,0,0.8); color: #fff; border: none;
            padding: 8px; border-radius: 50%; cursor: pointer;
        }

        .input-container { padding: 15px; display: flex; gap: 10px; background: var(--container-bg); border-top: 1px solid #333; }
        input { 
            flex: 1; padding: 15px 20px; border: none; border-radius: 30px; 
            background: var(--container-bg); color: #fff; box-shadow: var(--shadow-in); 
            outline: none; font-size: 16px; 
        }
        
        #sendBtn { 
            padding: 10px 25px; background: var(--container-bg); color: var(--gold-light); 
            border: 1px solid var(--gold-dark); border-radius: 30px; cursor: pointer; 
            font-weight: 700; box-shadow: var(--shadow-out);
        }

        .blink { animation: blinker 1.5s linear infinite; color: var(--gold-light); }
        @keyframes blinker { 50% { opacity: 0.3; } }
    </style>
</head>
<body>
    <div class="main-wrapper">
        <header><h2>ATOM AI CONTENT WRITER</h2></header>
        <div id="chat-box"></div>
        <div class="input-container">
            <input type="text" id="userInput" placeholder="Ask anything or generate image..." autocomplete="off">
            <button id="sendBtn">Send</button>
        </div>
    </div>

    <script>
        const box = document.getElementById('chat-box');
        const input = document.getElementById('userInput');
        const btn = document.getElementById('sendBtn');

        function formatMsg(text) {
            let t = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            t = t.replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>');
            t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
            return t.replace(/\\n/g, '<br>');
        }

        async function ask() {
            const q = input.value.trim();
            if(!q || btn.disabled) return;

            input.value = ''; btn.disabled = true;
            box.innerHTML += `<div class="msg user">${q}</div>`;
            box.scrollTop = box.scrollHeight;

            const tid = 't-' + Date.now();
            box.innerHTML += `<div class="msg bot blink" id="${tid}">Thinking....</div>`;
            box.scrollTop = box.scrollHeight;

            try {
                const r = await fetch("/ask?q=" + encodeURIComponent(q));
                const d = await r.json();
                const target = document.getElementById(tid);
                target.classList.remove('blink');
                target.innerHTML = '';

                if (d.answer) {
                    const content = document.createElement('div');
                    content.innerHTML = formatMsg(d.answer);
                    target.appendChild(content);
                    target.querySelectorAll('pre code').forEach(el => hljs.highlightElement(el));
                    
                    const tools = document.createElement('div');
                    tools.className = 'tools';
                    tools.innerHTML = `<button class="icon-btn" id="copy-${tid}">Copy Text</button>`;
                    target.appendChild(tools);
                    document.getElementById(`copy-${tid}`).onclick = () => {
                        navigator.clipboard.writeText(d.answer);
                        document.getElementById(`copy-${tid}`).innerText = '✅ Copied!';
                    };
                }

                if (d.images && d.images.length > 0) {
                    const gall = document.createElement('div');
                    gall.className = 'image-gallery';
                    d.images.forEach(src => {
                        const card = document.createElement('div');
                        card.className = 'img-card';
                        card.innerHTML = `<img src="${src}" class="gemini-img"><button class="dl-btn">DL</button>`;
                        card.querySelector('.dl-btn').onclick = () => window.open(src, '_blank');
                        gall.appendChild(card);
                    });
                    target.appendChild(gall);
                }
                if (d.error) target.innerText = "Error: " + d.error;
            } catch (e) { document.getElementById(tid).innerText = "Error: Connection failed."; }
            btn.disabled = false; box.scrollTop = box.scrollHeight;
            input.focus();
        }

        btn.onclick = ask;
        input.onkeydown = (e) => { if(e.key === "Enter") { e.preventDefault(); ask(); } };
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
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        try:
            context = await browser.new_context(storage_state="auth.json", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
            page = await context.new_page()
            if hasattr(playwright_stealth, 'stealth_async'): await playwright_stealth.stealth_async(page)
            await page.goto("https://gemini.google.com/app", timeout=60000)
            
            textbox = await page.wait_for_selector('div[role="textbox"]', timeout=30000)
            await textbox.fill(q); await page.keyboard.press("Enter")
            
            # အဖြေထွက်လာသည်အထိ Loop ပတ်ပြီး စောင့်မည့်စနစ်
            ans_text = ""
            imgs = []
            for _ in range(15): # စုစုပေါင်း စက္ကန့် ၃၀ ခန့်စောင့်မည်
                await asyncio.sleep(2)
                responses = await page.query_selector_all(".message-content")
                if responses:
                    last_res = responses[-1]
                    text_el = await last_res.query_selector(".model-response-text, div.markdown, .message-content-text")
                    if text_el:
                        ans_text = await text_el.inner_text()
                        if ans_text.strip(): # စာသားအမှန်တကယ်ပါမှ ရပ်မည်
                            img_els = await last_res.query_selector_all("img")
                            for i in img_els:
                                src = await i.get_attribute("src")
                                if src and src.startswith("https://"): imgs.append(src)
                            break
            
            await browser.close()
            if not ans_text: return {"error": "Gemini is too slow or Session expired."}
            return {"answer": ans_text, "images": imgs}
        except Exception as e:
            if 'browser' in locals(): await browser.close()
            return {"error": str(e)}
