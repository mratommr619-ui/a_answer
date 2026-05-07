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
<html>
<head>
    <title>ATOM AI CONTENT WRITER</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
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

        body, html { 
            margin: 0; padding: 0; height: 100%; width: 100%; 
            background: var(--bg-color); color: var(--text-color);
            font-family: 'Segoe UI', sans-serif;
            overflow: hidden; /* Screen fix ဖြစ်စေရန် */
            display: flex; justify-content: center; align-items: center;
        }

        .chat-container { 
            width: 95%; max-width: 550px; 
            height: 90vh; /* Screen ရဲ့ ၉၀% အမြင့်ကိုယူမည် */
            background: var(--container-bg); 
            padding: 30px; border-radius: 40px; 
            box-shadow: var(--shadow-out); 
            border: 1px solid #333;
            display: flex; flex-direction: column;
        }

        h2 { 
            color: var(--gold-light); text-align: center; 
            text-transform: uppercase; letter-spacing: 3px; 
            margin: 0 0 20px 0; font-size: 20px; 
        }

        #chat-box { 
            flex: 1; /* ကျန်တဲ့နေရာအကုန်ယူမည် */
            overflow-y: auto; 
            margin-bottom: 20px; padding: 20px; 
            border-radius: 25px; background: var(--container-bg); 
            box-shadow: var(--shadow-in); 
            display: flex; flex-direction: column;
            scroll-behavior: smooth;
        }

        /* Scrollbar hide */
        #chat-box::-webkit-scrollbar { width: 0px; }

        .msg { margin: 10px 0; padding: 15px; border-radius: 18px; max-width: 85%; line-height: 1.6; font-size: 15px; }
        .user { align-self: flex-end; background: linear-gradient(145deg, #d4af37, #f1c40f); color: #000; font-weight: 700; }
        .bot { align-self: flex-start; background: #2a2a2a; border: 1px solid #333; }

        .input-area { 
            display: flex; gap: 10px; padding-top: 5px;
        }

        input { 
            flex: 1; padding: 15px 20px; border: none; 
            border-radius: 30px; background: var(--container-bg); 
            color: var(--text-color); box-shadow: var(--shadow-in); 
            outline: none; font-size: 15px;
        }

        button { 
            padding: 10px 25px; background: var(--container-bg); 
            color: var(--gold-light); border: 1px solid var(--gold-dark); 
            border-radius: 30px; cursor: pointer; font-weight: 700; 
            box-shadow: var(--shadow-out); transition: 0.3s;
        }

        button:active { box-shadow: var(--shadow-in); transform: scale(0.95); }
        button:disabled { opacity: 0.4; }

        .blink { animation: blinker 1.5s linear infinite; }
        @keyframes blinker { 50% { opacity: 0.5; } }
    </style>
</head>
<body>
    <div class="chat-container">
        <h2>ATOM AUTO CONTENT WRITER</h2>
        <div id="chat-box"></div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="မေးခွန်းရိုက်ပါ..." onkeypress="if(event.key==='Enter') ask()">
            <button onclick="ask()" id="sendBtn">Send</button>
        </div>
    </div>
    <script>
        const box = document.getElementById('chat-box');
        const input = document.getElementById('userInput');
        const btn = document.getElementById('sendBtn');

        async function ask() {
            const q = input.value.trim();
            if(!q) return;
            box.innerHTML += `<div class="msg user">${q}</div>`;
            input.value = ''; btn.disabled = true;
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
