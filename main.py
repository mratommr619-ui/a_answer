import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

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

        body { 
            font-family: 'Segoe UI', Roboto, sans-serif; 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            background-color: var(--bg-color); 
            margin: 0; 
            padding: 20px; 
            color: var(--text-color);
        }

        .chat-container { 
            width: 100%; 
            max-width: 550px; 
            background: var(--container-bg); 
            padding: 30px; 
            border-radius: 30px; 
            box-shadow: var(--shadow-out);
            border: 1px solid #333;
        }

        h2 { 
            color: var(--gold-light); 
            text-align: center; 
            margin-top: 0; 
            font-weight: 700; 
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 0 0 10px rgba(241, 196, 15, 0.5);
        }

        #chat-box { 
            height: 400px; 
            overflow-y: auto; 
            margin-bottom: 25px; 
            padding: 20px;
            border-radius: 20px; 
            display: flex; 
            flex-direction: column; 
            background: var(--container-bg);
            box-shadow: var(--shadow-in);
        }

        /* Scrollbar styling */
        #chat-box::-webkit-scrollbar { width: 8px; }
        #chat-box::-webkit-scrollbar-track { background: transparent; }
        #chat-box::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
        #chat-box::-webkit-scrollbar-thumb:hover { background: var(--gold-dark); }

        .msg { 
            margin: 10px 0; 
            padding: 12px 18px; 
            border-radius: 15px; 
            max-width: 80%; 
            line-height: 1.6; 
            font-size: 15px;
            position: relative;
        }

        .user { 
            align-self: flex-end; 
            background: linear-gradient(145deg, #d4af37, #f1c40f);
            color: #000; 
            font-weight: 600;
            border-bottom-right-radius: 2px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
        }

        .bot { 
            align-self: flex-start; 
            background: #2a2a2a; 
            color: var(--text-color); 
            border: 1px solid #333;
            border-bottom-left-radius: 2px;
            box-shadow: var(--shadow-out);
        }

        .input-area { 
            display: flex; 
            gap: 15px; 
        }

        input { 
            flex: 1; 
            padding: 15px 20px; 
            border: none; 
            border-radius: 25px; 
            outline: none; 
            font-size: 15px; 
            background: var(--container-bg);
            color: var(--text-color);
            box-shadow: var(--shadow-in);
            transition: box-shadow 0.3s, border 0.3s;
        }

        input:focus { 
            box-shadow: inset 2px 2px 5px #0d0d0d, inset -2px -2px 5px #272727, 0 0 5px rgba(241, 196, 15, 0.3);
            border: 1px solid rgba(241, 196, 15, 0.3);
        }

        button { 
            padding: 10px 28px; 
            background: var(--container-bg);
            color: var(--gold-light); 
            border: 1px solid var(--gold-dark); 
            border-radius: 25px; 
            cursor: pointer; 
            font-weight: 700; 
            text-transform: uppercase;
            letter-spacing: 1px;
            box-shadow: var(--shadow-out);
            transition: all 0.3s ease;
        }

        button:hover { 
            background: linear-gradient(145deg, #f1c40f, #d4af37);
            color: #000;
            box-shadow: 0 0 15px rgba(241, 196, 15, 0.5);
        }

        button:active {
            box-shadow: var(--shadow-in);
            transform: scale(0.98);
        }

        button:disabled { 
            background: #333; 
            color: #666; 
            border-color: #444;
            box-shadow: none;
            cursor: not-allowed; 
        }

        .blink { animation: blinker 1.5s linear infinite; }
        @keyframes blinker { 50% { opacity: 0.5; } }
    </style>
</head>
<body>
    <div class="chat-container">
        <h2>Atom Auto Content Writer</h2>
        <div id="chat-box"></div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="ရွှေရောင်ဉာဏ်ရည်ကို မေးမြန်းပါ..." onkeypress="if(event.key==='Enter') ask()">
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
            // 1. User မေးခွန်း (ရွှေရောင်နောက်ခံ)
            box.innerHTML += `<div class="msg user">${q}</div>`;
            input.value = '';
            btn.disabled = true;

            // 2. လက်ခံရရှိကြောင်း ပြခြင်း
            box.innerHTML += `<div class="msg bot"><i>Message received.</i></div>`;
            
            // 3. Thinking status (မှိတ်တုတ်မှိတ်တုတ်ပုံစံ)
            const thinkingId = 'think-' + Date.now();
            box.innerHTML += `<div class="msg bot blink" id="${thinkingId}">Thinking....</div>`;
            box.scrollTop = box.scrollHeight;

            try {
                const response = await fetch(`/ask?q=${encodeURIComponent(q)}`);
                const data = await response.json();
                
                const thinkMsg = document.getElementById(thinkingId);
                thinkMsg.classList.remove('blink'); // Blink ကို ရပ်လိုက်မယ်
                
                if (data.answer) {
                    thinkMsg.innerText = data.answer;
                } else {
                    thinkMsg.style.color = '#ff6b6b'; // Error ဆိုရင် အနီရောင်ပြမယ်
                    thinkMsg.innerText = "Error: " + (data.error || "Something went wrong");
                }
            } catch (e) {
                const thinkMsg = document.getElementById(thinkingId);
                thinkMsg.classList.remove('blink');
                thinkMsg.style.color = '#ff6b6b';
                thinkMsg.innerText = "Error: Connection failed.";
            }

            btn.disabled = false;
            box.scrollTop = box.scrollHeight;
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

    with open("auth.json", "w") as f:
        f.write(SESSION_DATA)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = await browser.new_context(storage_state="auth.json")
        page = await context.new_page()
        await stealth_async(page)
        
        try:
            await page.goto("https://gemini.google.com/app", timeout=60000)
            await page.fill('div[role="textbox"]', q)
            await page.keyboard.press("Enter")
            
            await asyncio.sleep(12) # Gemini အဖြေပေးချိန်စောင့်ရန်
            
            responses = await page.query_selector_all(".message-content")
            if responses:
                answer = await responses[-1].inner_text()
            else:
                answer = "Gemini is currently unavailable."
            
            await browser.close()
            return {"answer": answer}
        except Exception as e:
            await browser.close()
            return {"error": str(e)}
