import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import playwright_stealth
from playwright.async_api import async_playwright

app = FastAPI()

# Render သို့မဟုတ် Hugging Face ရဲ့ Environment Variable ထဲမှာ SESSION_DATA ထည့်ထားဖို့ လိုပါတယ်
SESSION_DATA = os.getenv("SESSION_DATA")

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>ATOM AI CONTENT WRITER</title>
    <style>
        :root {
            --bg-color: #1a1a1a;
            --container-bg: #222222;
            --gold-light: #f1c40f;
            --gold-dark: #d4af37;
            --shadow-out: 8px 8px 16px #0d0d0d, -8px -8px 16px #272727;
            --shadow-in: inset 6px 6px 12px #0d0d0d, inset -6px -6px 12px #272727;
            --text-color: #e0e0e0;
        }

        html, body {
            margin: 0; padding: 0; width: 100%; height: 100%;
            overflow: hidden; background: var(--bg-color);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        .main-wrapper {
            display: flex; flex-direction: column;
            width: 100%; height: 100vh; max-width: 600px;
            margin: 0 auto; background: var(--container-bg);
            position: relative;
        }

        header { padding: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3); z-index: 5; }
        h2 { color: var(--gold-light); margin: 0; font-size: 18px; letter-spacing: 2px; }

        #chat-box {
            flex: 1; overflow-y: auto; padding: 20px;
            display: flex; flex-direction: column; gap: 15px;
            background: var(--container-bg); box-shadow: var(--shadow-in);
            margin: 10px; border-radius: 20px;
        }

        #chat-box::-webkit-scrollbar { width: 4px; }
        #chat-box::-webkit-scrollbar-thumb { background: var(--gold-dark); border-radius: 10px; }

        .msg {
            max-width: 90%; padding: 15px; border-radius: 18px;
            font-size: 15px; line-height: 1.6; position: relative;
            animation: slideUp 0.3s ease; word-wrap: break-word;
        }

        @keyframes slideUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        .user { align-self: flex-end; background: linear-gradient(145deg, var(--gold-dark), var(--gold-light)); color: #000; font-weight: 700; }
        .bot { align-self: flex-start; background: #2a2a2a; border: 1px solid #333; box-shadow: var(--shadow-out); }

        .tools { display: flex; gap: 10px; margin-top: 10px; border-top: 1px solid #444; padding-top: 8px; }
        .icon-btn { 
            background: none; border: none; color: var(--gold-light); 
            cursor: pointer; font-size: 12px; display: flex; align-items: center; gap: 5px; 
            padding: 5px; border-radius: 5px;
        }

        .image-gallery { display: flex; flex-direction: column; gap: 15px; margin-top: 10px; }
        .img-card { position: relative; width: 100%; }
        .gemini-img { width: 100%; border-radius: 12px; border: 1px solid var(--gold-dark); display: block; }
        
        .dl-btn {
            position: absolute; top: 10px; right: 10px;
            background: rgba(0,0,0,0.7); color: white; border: none;
            padding: 8px; border-radius: 50%; cursor: pointer;
        }

        .input-container { padding: 15px; display: flex; gap: 10px; background: var(--container-bg); border-top: 1px solid #333; }
        input { flex: 1; padding: 15px 20px; border: none; border-radius: 30px; background: var(--container-bg); color: var(--text-color); box-shadow: var(--shadow-in); outline: none; font-size: 16px; }
        
        #sendBtn { 
            padding: 10px 20px; background: var(--container-bg); 
            color: var(--gold-light); border: 1px solid var(--gold-dark); 
            border-radius: 30px; cursor: pointer; font-weight: 700; 
            box-shadow: var(--shadow-out); 
        }

        .blink { animation: blinker 1.5s linear infinite; font-style: italic; }
        @keyframes blinker { 50% { opacity: 0.4; } }
    </style>
</head>
<body>
    <div class="main-wrapper">
        <header><h2>ATOM AUTO CONTENT WRITER</h2></header>
        <div id="chat-box"></div>
        <div class="input-container">
            <input type="text" id="userInput" placeholder="Type here..." autocomplete="off">
            <button id="sendBtn">Send</button>
        </div>
    </div>

    <script>
        const box = document.getElementById('chat-box');
        const input = document.getElementById('userInput');
        const btn = document.getElementById('sendBtn');

        async function ask() {
            const q = input.value.trim();
            if(!q) return;

            input.value = '';
            btn.disabled = true;

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
                    const textDiv = document.createElement('div');
                    textDiv.innerText = d.answer;
                    target.appendChild(textDiv);
                    
                    const toolDiv = document.createElement('div');
                    toolDiv.className = 'tools';
                    const copyBtn = document.createElement('button');
                    copyBtn.className = 'icon-btn';
                    copyBtn.innerHTML = 'Copy Text';
                    copyBtn.onclick = () => {
                        navigator.clipboard.writeText(d.answer);
                        copyBtn.innerText = '✅ Copied!';
                        setTimeout(() => copyBtn.innerText = 'Copy Text', 2000);
                    };
                    toolDiv.appendChild(copyBtn);
                    target.appendChild(toolDiv);
                }

                if (d.images && d.images.length > 0) {
                    const gall = document.createElement('div');
                    gall.className = 'image-gallery';
                    d.images.forEach(src => {
                        const card = document.createElement('div');
                        card.className = 'img-card';
                        card.innerHTML = '<img src="'+src+'" class="gemini-img"><button class="dl-btn">DL</button>';
                        card.querySelector('.dl-btn').onclick = () => window.open(src, '_blank');
                        gall.appendChild(card);
                    });
                    target.appendChild(gall);
                }
                if (d.error) target.innerText = "Error: " + d.error;

            } catch (e) {
                document.getElementById(tid).innerText = "Error: Connection failed.";
            }

            btn.disabled = false;
            box.scrollTop = box.scrollHeight;
        }

        btn.onclick = ask;
        input.onkeydown = (e) => { if(e.key === "Enter") ask(); };
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
        return {"error": "SESSION_DATA missing!"}
    
    # auth.json ဖန်တီးခြင်း
    with open("auth.json", "w") as f:
        f.write(SESSION_DATA)
        
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        try:
            context = await browser.new_context(
                storage_state="auth.json", 
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Stealth mode စစ်ဆေးခြင်း
            if hasattr(playwright_stealth, 'stealth_async'):
                await playwright_stealth.stealth_async(page)
                
            await page.goto("https://gemini.google.com/app", timeout=60000)
            
            # Textbox ကို ရှာပြီး ရိုက်ထည့်ခြင်း
            textbox = await page.wait_for_selector('div[role="textbox"]', timeout=30000)
            await textbox.fill(q)
            await page.keyboard.press("Enter")
            
            # Gemini စဉ်းစားပြီး အဖြေပြန်ပေးချိန်ကို စောင့်ခြင်း
            await asyncio.sleep(18)
            
            responses = await page.query_selector_all(".message-content")
            if responses:
                last_res = responses[-1]
                
                # စာသားယူခြင်း
                text_el = await last_res.query_selector(".model-response-text, div.markdown")
                ans_text = await text_el.inner_text() if text_el else ""
                
                # ပုံယူခြင်း
                imgs = []
                img_els = await last_res.query_selector_all("img")
                for i in img_els:
                    src = await i.get_attribute("src")
                    if src and src.startswith("https://"):
                        imgs.append(src)
                
                await browser.close()
                return {"answer": ans_text, "images": imgs}
            
            await browser.close()
            return {"answer": "No response from Gemini.", "images": []}
            
        except Exception as e:
            if 'browser' in locals():
                await browser.close()
            return {"error": str(e), "images": []}
