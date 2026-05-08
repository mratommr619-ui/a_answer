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

# --- ၂။ Groq Setup (4 Keys Rotation) ---
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_KEYS", "").split(",") if k.strip()]
current_key_index = 0

def get_rotated_groq_client():
    global current_key_index
    if not GROQ_KEYS: return None
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
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['my', 'en'])
        return " ".join([t['text'] for t in transcript_list])
    except: return None

# --- ၄။ UI Design (The Complete Frontend) ---
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
        .container { width: 100%; max-width: 500px; background: var(--card); display: flex; flex-direction: column; box-shadow: 10px 10px 30px #000; }
        .screen { display: none; flex-direction: column; height: 100%; padding: 25px; box-sizing: border-box; }
        .active { display: flex; }
        input { width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 50px; background: var(--bg); color: #fff; outline: none; box-sizing: border-box; box-shadow: inset 5px 5px 10px var(--ds); }
        button { padding: 15px; border-radius: 50px; border: none; background: var(--card); color: var(--gold); font-weight: bold; cursor: pointer; box-shadow: 5px 5px 10px var(--ds), -5px -5px 10px var(--ls); }
        #chat-box { flex: 1; overflow-y: auto; padding: 15px; background: var(--bg); border-radius: 20px; display: flex; flex-direction: column; margin-bottom: 10px; }
        .msg { position: relative; margin-bottom: 25px; padding: 15px; border-radius: 20px; font-size: 14px; max-width: 85%; line-height:1.6; word-wrap: break-word; }
        .user { align-self: flex-end; background: var(--gold); color: #000; font-weight: bold; }
        .bot { align-self: flex-start; background: var(--card); border: 1px solid #333; }
        pre { background: #000 !important; border-radius: 10px; padding: 10px; overflow-x: auto; border: 1px solid #444; }
        .copy-btn { position: absolute; top: -10px; right: 10px; background: var(--card); color: var(--gold); padding: 4px 10px; border-radius: 10px; cursor: pointer; font-size: 10px; border: 1px solid #444; }
        #lb { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.9); z-index:99; justify-content:center; align-items:center; }
    </style>
</head>
<body>
    <div class="container">
        <div id="auth-screen" class="screen active" style="justify-content:center; text-align:center;">
            <h1 style="color:var(--gold);">ATOM AI</h1>
            <div id="l-f">
                <input type="text" id="u" placeholder="Username">
                <input type="password" id="p" placeholder="Password">
                <button onclick="auth('login')" style="width:100%">SIGN IN</button>
                <p onclick="tgl()" style="color:var(--gold); cursor:pointer; font-size:12px; margin-top:20px;">Register Account</p>
            </div>
            <div id="r-f" style="display:none">
                <input type="text" id="ru" placeholder="Username">
                <input type="password" id="rp" placeholder="Password">
                <button onclick="auth('register')" style="width:100%">CREATE ACCOUNT</button>
                <p onclick="tgl()" style="color:var(--gold); cursor:pointer; font-size:12px; margin-top:20px;">Back to Login</p>
            </div>
        </div>
        <div id="chat-screen" class="screen">
            <div style="display:flex; justify-content:space-between; color:var(--gold); margin-bottom:10px; border-bottom:1px solid #333; padding-bottom:5px;">
                <b id="du"></b><span id="dt" style="border:1px solid; padding:2px 8px; border-radius:20px;"></span>
            </div>
            <div id="chat-box"></div>
            <div style="display:flex; gap:10px;">
                <input type="text" id="query" placeholder="Ask or Draw..." onkeypress="if(event.key==='Enter') ask()">
                <button onclick="ask()" style="width:50px; border-radius:50%;"><i class="fas fa-paper-plane"></i></button>
            </div>
        </div>
    </div>
    <div id="lb" onclick="this.style.display='none'"><img id="lb-i" style="max-width:90%; border:2px solid var(--gold);"></div>
    <script>
        let curU="", curP="", cache={};
        function tgl(){ document.getElementById('l-f').style.display=document.getElementById('l-f').style.display==='none'?'block':'none'; document.getElementById('r-f').style.display=document.getElementById('r-f').style.display==='none'?'block':'none'; }
        async function auth(t){
            const u=t==='login'?document.getElementById('u').value:document.getElementById('ru').value;
            const p=t==='login'?document.getElementById('p').value:document.getElementById('rp').value;
            const res=await fetch("/"+t,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:u,password:p})});
            const d=await res.json();
            if(d.status==='success'){
                if(t==='register'){ alert("Success!"); tgl(); }
                else { curU=u; curP=p; document.getElementById('auth-screen').classList.remove('active'); document.getElementById('chat-screen').classList.add('active'); document.getElementById('du').innerText=u.toUpperCase(); document.getElementById('dt').innerText=d.tier.toUpperCase(); }
            } else alert(d.message);
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
            const target=document.getElementById(tid);
            if(d.answer){
                cache[tid] = d.answer;
                target.innerHTML = formatAI(d.answer);
                target.innerHTML += `<div class="copy-btn" onclick="copy('${tid}', this)">COPY</div>`;
                if(d.img) {
                    target.innerHTML += `<div style="margin-top:10px"><img src="${d.img}" style="width:100%; border-radius:10px;" onclick="openI('${d.img}')">
                    <a href="${d.img}" download target="_blank"><button style="width:100%; margin-top:5px; padding:5px; font-size:10px;">DOWNLOAD</button></a></div>`;
                }
                target.querySelectorAll('pre code').forEach(el => hljs.highlightElement(el));
            } else target.innerHTML=`<span style="color:red">${d.error}</span>`;
            box.scrollTop=box.scrollHeight;
        }
        function copy(id, b){ navigator.clipboard.writeText(cache[id]); b.innerText="COPIED!"; setTimeout(()=>b.innerText="COPY", 2000); }
        function openI(s){ document.getElementById('lb-i').src=s; document.getElementById('lb').style.display='flex'; }
    </script>
</body>
</html>
"""

# --- ၅။ FastAPI & Logic ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/", response_class=HTMLResponse)
async def home(): return USER_UI

@app.post("/register")
async def register(data: dict):
    u, p = data.get("username"), data.get("password")
    user_ref = db.collection("users").document(u)
    if user_ref.get().exists: return {"status": "fail", "message": "Username taken"}
    user_ref.set({"password": p, "type": "free", "usage": {"date": str(date.today()), "count": 0}})
    return {"status": "success"}

@app.post("/login")
async def login(data: dict):
    u, p = data.get("username"), data.get("password")
    user_ref = db.collection("users").document(u)
    doc = user_ref.get()
    if doc.exists and doc.to_dict()["password"] == p:
        return {"status": "success", "tier": doc.to_dict().get("type", "free")}
    return {"status": "fail", "message": "Login Failed"}

@app.post("/ask")
async def ask(data: dict):
    u, p, q = data.get("username"), data.get("password"), data.get("query")
    user_ref = db.collection("users").document(u)
    ud = user_ref.get().to_dict()
    tier = ud.get("type", "free")
    
    # YouTube Transcript Logic
    yt_context = ""
    vid = extract_video_id(q)
    if vid:
        ts = get_yt_transcript(vid)
        if ts: yt_context = f"\n\nVideo Transcript: {ts[:4000]}"

    # Image Logic (Premium Only)
    if any(w in q.lower() for w in ["draw", "image", "ပုံဆွဲ"]):
        if tier == "free": return {"error": "Premium Feature Only!"}
        prompt = q.replace("draw", "").replace("ပုံဆွဲ", "").strip() or "cool artwork"
        img_url = f"https://pollinations.ai/p/{prompt.replace(' ', '%20')}?width=1024&height=1024&model=flux"
        return {"answer": f"ဆွဲပေးလိုက်ပါပြီ- **{prompt}**", "img": img_url}

    # System Prompt (The Professor Role)
    sys_prompt = (
        "သင်သည် ဗဟုသုတအလွန်ကြွယ်ဝသော မြန်မာစာ ပါမောက္ခတစ်ဦးဖြစ်သည်။ "
        "မြန်မာစကားကို အနက်အဓိပ္ပာယ်ပြည့်စုံစွာ၊ ယဉ်ကျေးစွာနှင့် တကယ့်လူတစ်ယောက်ကဲ့သို့ သဘာဝကျကျသာ ဖြေကြားပါ။ "
        "ဘာသာပြန်စတိုင် (Translation style) လုံးဝမဖြစ်စေရ။ "
        "YouTube Transcript ပါလာပါက ၎င်းကို အနှစ်ချုပ်ရှင်းပြပါ။"
    )

    try:
        client = get_rotated_groq_client()
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"{q} {yt_context}"}],
            temperature=0.6
        )
        return {"answer": resp.choices[0].message.content}
    except: return {"error": "AI Error. Try again."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
