import os
import asyncio
import httpx
import re
import json
import firebase_admin
from firebase_admin import credentials, firestore
from groq import Groq
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, date
from youtube_transcript_api import YouTubeTranscriptApi

# --- ၁။ Firebase Configuration ---
def init_firebase():
    fb_config_str = os.getenv("FIREBASE_CONFIG_JSON")
    if not fb_config_str: return None
    cred = credentials.Certificate(json.loads(fb_config_str))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# --- ၂။ Groq Rotation ---
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_KEYS", "").split(",") if k.strip()]
current_key_index = 0

def get_rotated_groq_client():
    global current_key_index
    key = GROQ_KEYS[current_key_index]
    current_key_index = (current_key_index + 1) % len(GROQ_KEYS)
    return Groq(api_key=key)

# --- ၃။ YouTube Helper ---
def extract_video_id(url):
    pattern = r'(?:v=|\/|be\/)([0-9A-Za-z_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_yt_transcript(video_id):
    try:
        ts_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['my', 'en'])
        return " ".join([t['text'] for t in ts_list])
    except: return None

# --- ၄။ UI Design (History ပြန်ဖတ်နိုင်အောင် Update လုပ်ထားသည်) ---
USER_UI = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATOM AI - PRO</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        :root { --bg: #0d0d0d; --card: #1a1a1a; --gold: #f1c40f; --ds: #050505; --ls: #252525; }
        body { margin: 0; background: var(--bg); color: #fff; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; height: 100vh; overflow: hidden; }
        .container { width: 100%; max-width: 500px; background: var(--card); display: flex; flex-direction: column; }
        .screen { display: none; flex-direction: column; height: 100%; padding: 25px; box-sizing: border-box; }
        .active { display: flex; }
        input { width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 50px; background: var(--bg); color: #fff; outline: none; box-sizing: border-box; box-shadow: inset 5px 5px 10px var(--ds); }
        button { padding: 15px; border-radius: 50px; border: none; background: var(--card); color: var(--gold); font-weight: bold; cursor: pointer; box-shadow: 5px 5px 10px var(--ds), -5px -5px 10px var(--ls); }
        #chat-box { flex: 1; overflow-y: auto; padding: 15px; background: var(--bg); border-radius: 20px; display: flex; flex-direction: column; margin-bottom: 10px; }
        .msg { position: relative; margin-bottom: 25px; padding: 15px; border-radius: 20px; font-size: 14px; max-width: 85%; line-height:1.6; word-wrap: break-word; }
        .user { align-self: flex-end; background: var(--gold); color: #000; font-weight: bold; }
        .bot { align-self: flex-start; background: var(--card); border: 1px solid #333; }
        .copy-btn { position: absolute; top: -10px; right: 10px; background: var(--card); color: var(--gold); padding: 4px 10px; border-radius: 10px; cursor: pointer; font-size: 10px; border: 1px solid #444; }
    </style>
</head>
<body>
    <div class="container">
        <div id="auth-screen" class="screen active" style="justify-content:center; text-align:center;">
            <h1 style="color:var(--gold); letter-spacing:5px;">ATOM AI</h1>
            <input type="text" id="u" placeholder="Username">
            <input type="password" id="p" placeholder="Password">
            <button onclick="auth('login')" style="width:100%">SIGN IN</button>
            <p onclick="tgl()" style="color:var(--gold); cursor:pointer; font-size:12px; margin-top:20px;">Register Account</p>
        </div>
        <div id="chat-screen" class="screen">
            <div style="display:flex; justify-content:space-between; color:var(--gold); margin-bottom:10px; border-bottom:1px solid #333; padding-bottom:5px;">
                <b id="du"></b><span id="dt" style="border:1px solid; padding:2px 8px; border-radius:20px;"></span>
            </div>
            <div id="chat-box"></div>
            <div style="display:flex; gap:10px;">
                <input type="text" id="query" placeholder="Ask anything..." onkeypress="if(event.key==='Enter') ask()">
                <button onclick="ask()" style="width:50px; border-radius:50%;"><i class="fas fa-paper-plane"></i></button>
            </div>
        </div>
    </div>
    <script>
        let curU="", curP="", cache={};
        function tgl(){ /* Login/Register Toggle Logic */ }
        
        async function auth(t){
            const u=document.getElementById('u').value, p=document.getElementById('p').value;
            const res=await fetch("/"+t,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:u,password:p})});
            const d=await res.json();
            if(d.status==='success'){
                curU=u; curP=p;
                document.getElementById('auth-screen').classList.remove('active');
                document.getElementById('chat-screen').classList.add('active');
                document.getElementById('du').innerText=u.toUpperCase();
                document.getElementById('dt').innerText=d.tier.toUpperCase();
                // History ကို ဆွဲထုတ်ပြမယ်
                if(d.history) d.history.forEach(m => appendMsg(m.q, m.a));
            } else alert(d.message);
        }

        function appendMsg(q, a){
            const box=document.getElementById('chat-box');
            box.innerHTML+=`<div class="msg user">${q}</div>`;
            const tid='t'+Date.now()+Math.random();
            box.innerHTML+=`<div class="msg bot" id="${tid}">${formatAI(a)}</div>`;
            box.scrollTop=box.scrollHeight;
        }

        function formatAI(t) {
            let res = t.replace(/```(\w+)?\n([\s\S]*?)```/g, (m, lang, code) => `<pre><code class="language-${lang || 'plaintext'}">${code.trim()}</code></pre>`);
            return res.replace(/\n/g, '<br>');
        }

        async function ask(){
            const inp=document.getElementById('query'), box=document.getElementById('chat-box');
            const q=inp.value; if(!q) return; inp.value='';
            box.innerHTML+=`<div class="msg user">${q}</div>`;
            const tid='t'+Date.now();
            box.innerHTML+=`<div class="msg bot" id="${tid}">Thinking...</div>`;
            box.scrollTop=box.scrollHeight;
            const res=await fetch("/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:curU,password:curP,query:q})});
            const d=await res.json();
            document.getElementById(tid).innerHTML = formatAI(d.answer);
            box.scrollTop=box.scrollHeight;
        }
    </script>
</body>
</html>
"""

# --- ၅။ Backend Endpoints ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/", response_class=HTMLResponse)
async def home(): return USER_UI

@app.post("/login")
async def login(data: dict):
    u, p = data.get("username"), data.get("password")
    user_ref = db.collection("users").document(u)
    doc = user_ref.get()
    if doc.exists and doc.to_dict()["password"] == p:
        ud = doc.to_dict()
        # History ပါ တစ်ခါတည်း ပို့ပေးလိုက်မယ်
        history = ud.get("chat_history", [])[-10:] # နောက်ဆုံး ၁၀ ခုပဲ ပြမယ်
        return {"status": "success", "tier": ud.get("type", "free"), "history": history}
    return {"status": "fail", "message": "Failed"}

@app.post("/ask")
async def ask(data: dict):
    u, p, q = data.get("username"), data.get("password"), data.get("query")
    user_ref = db.collection("users").document(u)
    ud = user_ref.get().to_dict()
    
    # History ဟောင်းကို AI ဆီ ပို့ဖို့ ပြင်မယ်
    history = ud.get("chat_history", [])[-5:] # Context အတွက် နောက်ဆုံး ၅ ခု ယူမယ်
    history_text = "\n".join([f"User: {m['q']}\nAI: {m['a']}" for m in history])

    sys_prompt = (
        "You are a wise Myanmar Professor. Reply in the user's language. "
        "Use natural Myanmar phrasing. \nChat History:\n" + history_text
    )

    try:
        client = get_rotated_groq_client()
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": q}]
        )
        answer = resp.choices[0].message.content
        
        # History ကို Firestore ထဲမှာ သိမ်းမယ်
        user_ref.update({
            "chat_history": firestore.ArrayUnion([{"q": q, "a": answer, "t": str(datetime.now())}])
        })
        return {"answer": answer}
    except: return {"error": "AI Error"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
