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
            --text-main: #e0e0e0; /* စာလုံးအရောင် - အဖြူရောင်အကြည် */
            --text-bot: #f0f0f0;  /* Bot စာလုံးအရောင် - ပိုလင်းသော အဖြူ */
        }

        html, body {
            margin: 0; padding: 0; width: 100%; height: 100%;
            overflow: hidden; background: var(--bg-color);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: var(--text-main);
        }

        .main-wrapper {
            display: flex; flex-direction: column;
            width: 100%; height: 100vh; max-width: 600px;
            margin: 0 auto; background: var(--container-bg);
            position: relative; box-shadow: 0 0 30px rgba(0,0,0,0.5);
        }

        header { padding: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3); z-index: 5; border-bottom: 1px solid #333; }
        h2 { color: var(--gold-light); margin: 0; font-size: 18px; letter-spacing: 2px; text-transform: uppercase; }

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

        .user { align-self: flex-end; background: linear-gradient(145deg, var(--gold-dark), var(--gold-light)); color: #000; font-weight: 700; box-shadow: 4px 4px 10px rgba(0,0,0,0.2); }
        
        /* Bot Message - စာလုံးအရောင်ကို အဖြူပြင်ထားသည် */
        .bot { align-self: flex-start; background: #2a2a2a; border: 1px solid #333; box-shadow: var(--shadow-out); color: var(--text-bot); }

        /* Code Block Styles (VS Code Style) */
        pre { margin: 10px 0; padding: 0; border-radius: 10px; overflow: hidden; box-shadow: var(--shadow-in); }
        code { font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 14px; }
        .hljs { padding: 15px; background: #1e1e1e !important; } /* VS Code background */

        /* Tools & Icons */
        .tools { display: flex; gap: 10px; margin-top: 10px; border-top: 1px solid #444; padding-top: 8px; }
        .icon-btn { 
            background: none; border: none; color: var(--gold-light); 
            cursor: pointer; font-size: 12px; display: flex; align-items: center; gap: 5px; 
            padding: 5px 10px; border-radius: 20px; transition: 0.2s;
        }
        .icon-btn:hover { background: rgba(241, 196, 15, 0.1); }

        /* Image Gallery */
        .image-gallery { display: flex; flex-direction: column; gap: 15px; margin-top: 10px; }
        .img-card { position: relative; width: 100%; border-radius: 12px; overflow: hidden; border: 1px solid var(--gold-dark); box-shadow: var(--shadow-out); }
        .gemini-img { width: 100%; display: block; }
        
        .dl-btn {
            position: absolute; top: 10px; right: 10px;
            background: rgba(0,0,0,0.7); color: white; border: none;
            padding: 10px; border-radius: 50%; cursor: pointer; opacity: 0.8; transition: 0.2s;
        }
        .dl-btn:hover { opacity: 1; background: #000; }

        /* Input Area */
        .input-container { padding: 15px; display: flex; gap: 10px; background: var(--container-bg); border-top: 1px solid #333; z-index: 5; }
        input { flex: 1; padding: 15px 20px; border: none; border-radius: 30px; background: var(--container-bg); color: var(--text-main); box-shadow: var(--shadow-in); outline: none; font-size: 16px; }
        input::placeholder { color: #666; }
        
        #sendBtn { 
            padding: 10px 25px; background: var(--container-bg); 
            color: var(--gold-light); border: 1px solid var(--gold-dark); 
            border-radius: 30px; cursor: pointer; font-weight: 700; 
            box-shadow: var(--shadow-out); transition: 0.2s;
        }
        #sendBtn:active { box-shadow: var(--shadow-in); transform: scale(0.95); }
        #sendBtn:disabled { opacity: 0.5; cursor: not-allowed; }

        .blink { animation: blinker 1.5s linear infinite; font-style: italic; color: var(--gold-light); }
        @keyframes blinker { 50% { opacity: 0.4; } }
    </style>
</head>
<body>
    <div class="main-wrapper">
        <header><h2>ATOM AI CONTENT WRITER</h2></header>
        <div id="chat-box">
            <div class="msg bot">မင်္ဂလာပါ။ ATOM AI မှ ကြိုဆိုပါတယ်။ ဘာကူညီပေးရမလဲဗျာ။<br>(YouTube link များ၊ ပုံထုတ်ခိုင်းခြင်းများ စမ်းသပ်နိုင်ပါတယ်)</div>
        </div>
        <div class="input-container">
            <input type="text" id="userInput" placeholder="Type a message or ask for code..." autocomplete="off">
            <button id="sendBtn">Send</button>
        </div>
    </div>

    <script>
        const box = document.getElementById('chat-box');
        const input = document.getElementById('userInput');
        const btn = document.getElementById('sendBtn');

        // Markdown အတွက် ရိုးရှင်းသော Parser (Code block များကို pre/code ပြောင်းရန်)
        function parseMarkdown(text) {
            // Escape HTML to prevent XSS
            let escapedText = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            
            // Code blocks (```code```) -> <pre><code>code</code></pre>
            escapedText = escapedText.replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>');
            
            // Inline code (`code`) -> <code>code</code>
            escapedText = escapedText.replace(/`([^`]+)`/g, '<code>$1</code>');
            
            // New lines -> <br>
            return escapedText.replace(/\\n/g, '<br>');
        }

        async function ask() {
            const q = input.value.trim();
            if(!q) return;

            input.value = '';
            btn.disabled = true;

            // User Message
            box.innerHTML += `<div class="msg user">${q}</div>`;
            box.scrollTop = box.scrollHeight;

            // Thinking Message
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
                    //Markdown parser သုံးပြီး code blocks များကို ခွဲထုတ်မည်
                    textDiv.innerHTML = parseMarkdown(d.answer);
                    target.appendChild(textDiv);
                    
                    // Code blocks များကို highlight.js ဖြင့် ကာလာချယ်မည်
                    target.querySelectorAll('pre code').forEach((el) => {
                        hljs.highlightElement(el);
                    });
                    
                    // Copy Button
                    const toolDiv = document.createElement('div');
                    toolDiv.className = 'tools';
                    const copyBtn = document.createElement('button');
                    copyBtn.className = 'icon-btn';
                    copyBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> Copy Text';
                    copyBtn.onclick = () => {
                        navigator.clipboard.writeText(d.answer);
                        copyBtn.innerHTML = '✅ Copied!';
                        setTimeout(() => copyBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> Copy Text', 2000);
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
                        card.innerHTML = `<img src="${src}" class="gemini-img">
                                         <button class="dl-btn" title="Open in new tab">
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 22 3 22 10"></polyline><line x1="10" y1="14" x2="22" y2="2"></line></svg>
                                         </button>`;
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
            input.focus(); // Input ကိုပြန် focus ထားမည်
        }

        btn.onclick = ask;
        // Enter Key Function (Fix)
        input.addEventListener("keydown", (e) => { 
            if(e.key === "Enter" && !btn.disabled) { 
                e.preventDefault(); // Prevents default behave (like new line)
                ask(); 
            } 
        });
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
            await page.goto("https://gemini.google.com/app", timeout=60000, wait_until="domcontentloaded")
            textbox = await page.wait_for_selector('div[role="textbox"]', timeout=30000)
            await textbox.fill(q); await page.keyboard.press("Enter")
            await asyncio.sleep(20) # Gemini စဉ်းစားချိန် တိုးပေးထားသည်
            responses = await page.query_selector_all(".message-content")
            if responses:
                last_res = responses[-1]
                # စာသားနှင့် ပုံSelectors များကို ပိုစုံအောင် စစ်မည်
                text_el = await last_res.query_selector(".model-response-text, div.markdown, .message-content-text")
                ans_text = await text_el.inner_text() if text_el else ""
                
                imgs = []
                img_els = await last_res.query_selector_all("img")
                for i in img_els:
                    src = await i.get_attribute("src")
                    if src and (src.startswith("https://") or src.startswith("data:image")): imgs.append(src)
                
                await browser.close()
                return {"answer": ans_text, "images": imgs}
            await browser.close()
            return {"answer": "No response from Gemini. Website might be slow.", "images": []}
        except Exception as e:
            if 'browser' in locals(): await browser.close()
            return {"error": str(e), "images": []}
