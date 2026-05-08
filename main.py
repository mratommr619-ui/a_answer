import os
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# သင်ပေးထားတဲ့ API Keys ၄ ခုကို Rotation လုပ်ဖို့ List ထဲထည့်ထားပါတယ်
API_KEYS = [
    "AIzaSyDtRhod768k7HX6gVufgmXGUxvb3veAx5k",
    "AIzaSyBcuyznz4DU0nDigC4kCnuX8oh44WkyEC8",
    "AIzaSyAJJjMJGNKitoYgUrvy9jVwCctVr5WLDik",
    "AIzaSyD6ZPN-cXY7xIJXMdHYAJYkVSXdkU0rDFE"
]

current_index = 0

def get_rotated_model():
    global current_index
    # အလှည့်ကျ Key ကို ယူသုံးခြင်း
    key = API_KEYS[current_index]
    genai.configure(api_key=key)
    # Gemini 1.5 Flash က ပေါ့ပါးမြန်ဆန်လို့ ဒါကိုပဲ သုံးထားပါတယ်
    model = genai.GenerativeModel('gemini-1.5-flash')
    current_index = (current_index + 1) % len(API_KEYS)
    return model

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATOM AI - RENDER EDITION</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/vs2015.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        :root {
            --bg: #0d0d0d;
            --card-bg: #1a1a1a;
            --gold: #f1c40f;
            --gold-dark: #d4af37;
            --text: #ffffff;
        }

        html, body {
            margin: 0; padding: 0; height: 100%;
            background: var(--bg); color: var(--text) !important;
            font-family: 'Segoe UI', Roboto, sans-serif;
            overflow: hidden;
        }

        .wrapper {
            display: flex; flex-direction: column;
            width: 100%; height: 100vh; max-width: 650px;
            margin: 0 auto; background: var(--card-bg);
            border-left: 1px solid #333; border-right: 1px solid #333;
        }

        header {
            padding: 20px; text-align: center;
            border-bottom: 1px solid #333;
            color: var(--gold); font-weight: bold;
            text-transform: uppercase; letter-spacing: 3px;
            font-size: 1.2rem;
        }

        #chat-box {
            flex: 1; overflow-y: auto; padding: 25px;
            display: flex; flex-direction: column; gap: 20px;
            background: #0d0d0d;
        }

        /* Scrollbar Design */
        #chat-box::-webkit-scrollbar { width: 5px; }
        #chat-box::-webkit-scrollbar-thumb { background: var(--gold-dark); border-radius: 10px; }

        .msg {
            max-width: 85%; padding: 15px 20px;
            border-radius: 20px; font-size: 15px;
            line-height: 1.6; word-wrap: break-word;
            color: #ffffff !important;
        }

        .user {
            align-self: flex-end;
            background: linear-gradient(135deg, var(--gold-dark), var(--gold-light));
            color: #000 !important; font-weight: bold;
            box-shadow: 0 4px 15px rgba(241, 196, 15, 0.2);
        }

        .bot {
            align-self: flex-start;
            background: #262626; border: 1px solid #333;
            box-shadow: 5px 5px 20px rgba(0,0,0,0.5);
        }

        /* VS Code Style Code Blocks */
        pre {
            background: #1e1e1e !important;
            border-radius: 12px; padding: 15px;
            margin: 15px 0; overflow-x: auto;
            border: 1px solid #444;
        }
        code { font-family: 'Fira Code', 'Consolas', monospace; }

        .copy-btn {
            margin-top: 10px; background: none;
            border: 1px solid #444; color: var(--gold);
            padding: 5px 12px; border-radius: 6px;
            cursor: pointer; font-size: 12px; transition: 0.3s;
        }
        .copy-btn:hover { background: rgba(241, 196, 15, 0.1); border-color: var(--gold); }

        .input-area {
            padding: 20px; display: flex; gap: 12px;
            background: var(--card-bg); border-top: 1px solid #333;
        }

        input {
            flex: 1; padding: 15px 25px; border-radius: 35px;
            border: 1px solid #333; background: #0d0d0d;
            color: #fff; outline: none; font-size: 16px;
            transition: 0.3s;
        }
        input:focus { border-color: var(--gold-dark); }

        button#sendBtn {
            padding: 10px 28px; border-radius: 35px;
            border: 1px solid var(--gold); background: transparent;
            color: var(--gold); cursor: pointer; font-weight: bold;
            transition: 0.3s;
        }
        button#sendBtn:hover { background: var(--gold); color: #000; }
    </style>
</head>
<body>
    <div class="wrapper">
        <header>ATOM AI CONTENT WRITER</header>
        <div id="chat-box"></div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Ask anything (API Rotator)..." autocomplete="off">
            <button id="sendBtn">SEND</button>
        </div>
    </div>

    <script>
        const box = document.getElementById('chat-box');
        const input = document.getElementById('userInput');
        const btn = document.getElementById('sendBtn');

        function formatMsg(text) {
            // HTML Escape
            let formatted = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            // Markdown Code Blocks
            formatted = formatted.replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>');
            // Inline Code
            formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
            // Line Breaks
            return formatted.replace(/\\n/g, '<br>');
        }

        async function ask() {
            const q = input.value.trim();
            if(!q || btn.disabled) return;

            input.value = '';
            btn.disabled = true;

            // User Message
            box.innerHTML += `<div class="msg user">${q}</div>`;
            const tid = 'bot-' + Date.now();
            box.innerHTML += `<div class="msg bot" id="${tid}">Processing...</div>`;
            box.scrollTop = box.scrollHeight;

            try {
                const response = await fetch("/ask?q=" + encodeURIComponent(q));
                const data = await response.json();
                const target = document.getElementById(tid);

                if (data.answer) {
                    target.innerHTML = formatMsg(data.answer);
                    // Code Highlight Apply
                    target.querySelectorAll('pre code').forEach(el => hljs.highlightElement(el));
                    // Copy Button
                    const cleanText = data.answer.replace(/\\\\/g, '\\\\\\\\').replace(/\\\`/g, '\\\\\\\\\`');
                    target.innerHTML += \`<br><button class="copy-btn" onclick="copyText(this, \\\`\${cleanText}\\\`)">Copy Text</button>\`;
                } else {
                    target.innerText = "Error: " + (data.error || "No response");
                }
            } catch (e) {
                document.getElementById(tid).innerText = "Server error. Please check Render logs.";
            }

            btn.disabled = false;
            box.scrollTop = box.scrollHeight;
            input.focus();
        }

        function copyText(button, text) {
            navigator.clipboard.writeText(text);
            button.innerText = '✅ Copied!';
            setTimeout(() => button.innerText = 'Copy Text', 2000);
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
    try:
        # API Key တစ်ခုစီကို အလှည့်ကျ သုံးသွားမှာပါ
        model = get_rotated_model()
        response = model.generate_content(q)
        return {"answer": response.text}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Render အတွက် port ကို manual သတ်မှတ်ပေးဖို့ လိုနိုင်ပါတယ်
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
