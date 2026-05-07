import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import playwright_stealth
from playwright.async_api import async_playwright

app = FastAPI()

SESSION_DATA = os.getenv("SESSION_DATA")

# HTML UI (သင်နှစ်သက်သော Black & Gold ဒီဇိုင်းကို အစအဆုံး ပြန်ထည့်ပေးထားပါသည်)
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ATOM AI CONTENT WRITER</title>
    <style>
        :root {
            --bg-color: #0f0f0f;
            --container-bg: #1a1a1a;
            --gold-light: #f1c40f;
            --gold-dark: #d4af37;
            --text-color: #e0e0e0;
        }

        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

        body, html { 
            margin: 0; padding: 0; height: 100%; width: 100%; 
            background: var(--bg-color); color: var(--text-color);
            font-family: 'Segoe UI', Roboto, sans-serif;
            overflow: hidden; /* Screen တစ်ခုလုံးကို Fix ဖြစ်စေရန် */
        }

        .app-wrapper {
            display: flex; flex-direction: column;
            height: 100vh; /* Viewport height အပြည့်ယူမည် */
            width: 100%; max-width: 600px; /* Mobile size width */
            margin: 0 auto;
            background: var(--container-bg);
            box-shadow: 0 0 50px rgba(0,0,0,0.5);
            position: relative;
        }

        header {
            padding: 15px; text-align: center;
            border-bottom: 1px solid #333;
            background: rgba(26,26,26,0.95);
            z-index: 10;
        }

        h2 { 
            margin: 0; font-size: 18px; color: var(--gold-light); 
            letter-spacing: 2px; text-transform: uppercase;
        }

        #chat-box {
            flex: 1; /* ကျန်တဲ့ space အကုန်ယူမည် */
            overflow-y: auto; /* စာများရင် chat box ထဲမှာတင် scroll လုပ်မည် */
            padding: 20px;
            display: flex; flex-direction: column;
            gap: 15px;
            background: radial-gradient(circle at top, #222 0%, #1a1a1a 100%);
            scroll-behavior: smooth;
        }

        /* Scrollbar အလှဆင်ခြင်း */
        #chat-box::-webkit-scrollbar { width: 4px; }
        #chat-box::-webkit-scrollbar-thumb { background: #444; border-radius: 10px; }

        .msg {
            max-width: 85%; padding: 12px 16px;
            border-radius: 18px; font-size: 15px; line-height: 1.5;
            word-wrap: break-word; position: relative;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        .user {
            align-self: flex-end;
            background: linear-gradient(135deg, var(--gold-dark), var(--gold-light));
            color: #000; font-weight: 600;
            border-bottom-right-radius: 2px;
        }

        .bot {
            align-self: flex-start;
            background: #2a2a2a;
            border: 1px solid #383838;
            border-bottom-left-radius: 2px;
        }

        .input-area {
            padding: 15px; background: #1a1a1a;
            border-top: 1px solid #333;
            display: flex; gap: 10px; align-items: center;
        }

        input {
            flex: 1; background: #252525; border: 1px solid #333;
            border-radius: 25px; padding: 12px 20px; color: white;
            outline: none; font-size: 15px; transition: 0.3s;
        }

        input:focus { border-color: var(--gold-dark); background: #2a2a2a; }

        button {
            background: var(--gold-dark); border: none; color: black;
            width: 45px; height: 45px; border-radius: 50%;
            cursor: pointer; display: flex; align-items: center; justify-content: center;
            font-weight: bold; transition: 0.2s; flex-shrink: 0;
        }

        button:active { transform: scale(0.9); }
        button:disabled { opacity: 0.5; filter: grayscale(1); }

        .blink { animation: blinker 1.5s linear infinite; font-style: italic; color: var(--gold-light); }
        @keyframes blinker { 50% { opacity: 0.3; } }
    </style>
</head>
<body>
    <div class="app-wrapper">
        <header>
            <h2>ATOM AI WRITER</h2>
        </header>

        <div id="chat-box">
            <div class="msg bot">မင်္ဂလာပါ။ ဘာကူညီပေးရမလဲဗျာ။</div>
        </div>

        <div class="input-area">
            <input type="text" id="userInput" placeholder="Type a message..." autocomplete="off">
            <button onclick="ask()" id="sendBtn">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
            </button>
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

            // User message
            box.innerHTML += `<div class="msg user">${q}</div>`;
            box.scrollTop = box.scrollHeight;

            // Thinking message
            const tid = 't-' + Date.now();
            box.innerHTML += `<div class="msg bot blink" id="${tid}">Thinking...</div>`;
            box.scrollTop = box.scrollHeight;

            try {
                const r = await fetch(`/ask?q=${encodeURIComponent(q)}`);
                const d = await r.json();
                const target = document.getElementById(tid);
                target.innerText = d.answer || "Error: " + d.error;
                target.classList.remove('blink');
            } catch (e) {
                document.getElementById(tid).innerText = "Error: Connection failed.";
                document.getElementById(tid).classList.remove('blink');
            }

            btn.disabled = false;
            box.scrollTop = box.scrollHeight;
            input.focus();
        }

        input.addEventListener("keypress", (e) => { if(e.key === "Enter") ask(); });
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

    # Session အသစ်ပြန်ရေးခြင်း
    with open("auth.json", "w") as f:
        f.write(SESSION_DATA)

    async with async_playwright() as p:
        # Browser settings (Hugging Face RAM 16GB ကို အပြည့်သုံးမည်)
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        try:
            context = await browser.new_context(
                storage_state="auth.json",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Stealth mode
            if hasattr(playwright_stealth, 'stealth_async'):
                await playwright_stealth.stealth_async(page)

            # Gemini ဆီသို့ သွားမည်
            await page.goto("https://gemini.google.com/app", timeout=60000)
            
            # Textbox အသင့်ဖြစ်ချိန်ထိ စောင့်မည်
            textbox = await page.wait_for_selector('div[role="textbox"]', timeout=30000)
            await textbox.fill(q)
            await page.keyboard.press("Enter")
            
            # အဖြေစထွက်လာသည်အထိ စောင့်မည့် Loop (ပိုသေချာအောင် လုပ်ထားခြင်း)
            await asyncio.sleep(15) 
            
            # အဖြေထုတ်ပေးမည့် Selector များကို အစုံလိုက်စစ်မည်
            selectors = [".message-content", ".model-response-text", "div.markdown"]
            answer = "No response from Gemini. Please check SESSION_DATA."
            
            for s in selectors:
                elements = await page.query_selector_all(s)
                if elements:
                    raw_text = await elements[-1].inner_text()
                    if raw_text.strip():
                        answer = raw_text.strip()
                        break
            
            await browser.close()
            return {"answer": answer}
        except Exception as e:
            await browser.close()
            return {"error": str(e)}
