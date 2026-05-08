import os
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# Environment Variable ထဲကနေ API Keys တွေကို ဖတ်မယ်
# Render Settings ထဲမှာ GEMINI_KEYS ဆိုတဲ့ နာမည်နဲ့ ကော်မာခံပြီး ထည့်ထားပေးပါ
raw_keys = os.getenv("GEMINI_KEYS", "")
API_KEYS = [k.strip() for k in raw_keys.split(",") if k.strip()]

# အကယ်၍ Environment Variable ထဲမှာ မရှိရင် အရန်အနေနဲ့ အရင် Key တွေကို သုံးမယ်
if not API_KEYS:
    API_KEYS = [
        "AIzaSyDtRhod768k7HX6gVufgmXGUxvb3veAx5k",
        "AIzaSyBcuyznz4DU0nDigC4kCnuX8oh44WkyEC8",
        "AIzaSyAJJjMJGNKitoYgUrvy9jVwCctVr5WLDik",
        "AIzaSyD6ZPN-cXY7xIJXMdHYAJYkVSXdkU0rDFE"
    ]

current_index = 0

def get_rotated_model():
    global current_index
    key = API_KEYS[current_index]
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    current_index = (current_index + 1) % len(API_KEYS)
    return model

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATOM AI - PRO</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/vs2015.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        :root { --bg: #0a0a0a; --card: #161616; --gold: #f1c40f; }
        body { margin: 0; background: var(--bg); color: #fff !important; font-family: sans-serif; overflow: hidden; }
        .wrapper { display: flex; flex-direction: column; height: 100vh; max-width: 600px; margin: 0 auto; background: var(--card); border: 1px solid #333; }
        header { padding: 15px; text-align: center; border-bottom: 1px solid #333; color: var(--gold); font-weight: bold; letter-spacing: 2px; }
        #chat-box { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; background: #000; }
        .msg { max-width: 85%; padding: 15px; border-radius: 18px; font-size: 15px; line-height: 1.6; color: #fff !important; }
        .user { align-self: flex-end; background: linear-gradient(135deg, #d4af37, #f1c40f); color: #000 !important; font-weight: bold; }
        .bot { align-self: flex-start; background: #222; border: 1px solid #333; }
        pre { background: #1e1e1e !important; border-radius: 10px; padding: 15px; margin: 10px 0; overflow-x: auto; }
        .input-area { padding: 20px; display: flex; gap: 10px; border-top: 1px solid #333; }
        input { flex: 1; padding: 12px 20px; border-radius: 30px; border: none; background: #111; color: #fff; outline: none; }
        button { padding: 10px 25px; border-radius: 30px; border: 1px solid var(--gold); background: transparent; color: var(--gold); cursor: pointer; font-weight: bold; }
        .copy-btn { margin-top: 8px; color: var(--gold); background: none; border: 1px solid #444; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 11px; }
    </style>
</head>
<body>
    <div class="wrapper">
        <header>ATOM AI (ENV ROTATOR)</header>
        <div id="chat-box"></div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Ask anything..." autocomplete="off">
            <button id="sendBtn">SEND</button>
        </div>
    </div>
    <script>
        const box = document.getElementById('chat-box');
        const input = document.getElementById('userInput');
        const btn = document.getElementById('sendBtn');
        function format(t) {
            let res = t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            res = res.replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>');
            res = res.replace(/`([^`]+)`/g, '<code>$1</code>');
            return res.replace(/\\n/g, '<br>');
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
                    target.innerHTML += \`<br><button class="copy-btn" onclick="navigator.clipboard.writeText(\\\`\${d.answer.replace(/\\\`/g, '\\\\\\\\\`').replace(/\\\\$/g, '\\\\\\\\$')}\\\'); this.innerText='✅ Copied!'">Copy Text</button>\`;
                } else { target.innerText = "Error: " + d.error; }
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
    try:
        model = get_rotated_model()
        response = model.generate_content(q)
        return {"answer": response.text}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
