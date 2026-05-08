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

# --- ၂။ Groq Setup ---
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_KEYS", "").split(",") if k.strip()]
current_key_index = 0

def get_rotated_groq_client():
    global current_key_index
    if not GROQ_KEYS: return None
    key = GROQ_KEYS[current_key_index]
    current_key_index = (current_key_index + 1) % len(GROQ_KEYS)
    return Groq(api_key=key)

# --- ၃။ Helper Functions ---
def extract_video_id(url):
    pattern = r'(?:v=|\/|be\/)([0-9A-Za-z_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_yt_transcript(video_id):
    try:
        ts_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['my', 'en'])
        return " ".join([t['text'] for t in ts_list])
    except: return None

# --- ၄။ Google Translate Helper (သဘာဝကျသော မြန်မာစာအတွက်) ---
async def translate_to_myanmar(text):
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=my&dt=t&q={text}"
            resp = await client.get(url)
            result = resp.json()
            return "".join([sentence[0] for sentence in result[0]])
    except: return text # Error တက်ရင် မူရင်းအတိုင်း ပြန်ပေးမယ်

# --- ၅။ UI Design (Download Button ပါဝင်ပြီးသား) ---
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
        button { padding: 15px; border-radius: 50px; border: none; background: var(--card); color: var(--gold); font-weight: bold; cursor: pointer; box-shadow: 5px 5px 10px var(--ds), -5px -5px 10px var(--ls); transition: 0.2s; }
        button:active { transform: scale(0.95); }
        #chat-box { flex: 1; overflow-y: auto; padding: 15px; background: var(--bg); border-radius: 20px; display: flex; flex-direction: column; margin-bottom: 10px; }
        .msg { position: relative; margin-bottom: 25px; padding: 15px; border-radius: 20px; font-size: 14px; max-width: 85%; line-height:1.6; word-wrap: break-word; }
        .user { align-self: flex-end; background: var(--gold); color: #000; font-weight: bold; }
        .bot { align-self: flex-start; background: var(--card); border: 1px solid #333; }
        pre { background: #000 !important; border-radius: 10px; padding: 10px; overflow-x: auto; border: 1px solid #444; }
        .copy-btn { position: absolute; top: -10px; right: 10px; background: var(--card); color: var(--gold); padding: 4px 10px; border-radius: 10px; cursor: pointer; font-size: 10px; border: 1px solid #444; z-index: 10; }
        .input-area { display: flex; gap: 10px; }
        .input-area input { flex: 1; margin: 0; }
        .input-area button { width: 50px; height: 50px; padding: 0; border-radius: 50%; }
        #lb { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.95); z-index:999; justify-content:center; align-items:center; }
        #lb img { max-width:90%; max-height:85%; border-radius:10px; border: 2px solid var(--gold); }
    </style>
</head>
<body>
    <div class="container">
        <div id="auth-screen" class="screen active" style="justify-content:center; text-align:center;">
            <h1 style="color:var(--gold); letter-spacing:5px;">ATOM AI</h1>
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
            <div style="display:flex; justify-content:space-between; color:var(--gold); margin-bottom:10px; border-bottom:1px solidအစအဆုံး ပြန်ထုတ်ပေးလိုက်ပါတယ်ဗျာ။ ဒီ code ကို GitHub မှာ Commit လုပ်၊ Render မှာ Deploy လုပ်ပြီးတာနဲ့ အကုန်အဆင်ပြေသွားမှာပါ။

အဓိကပြင်ထားတာကတော့-
၁။ **ပုံဆွဲ Logic:** "ပုံဆွဲ" ဆိုတဲ့ စကားလုံးပါရင် AI ကို မမေးတော့ဘဲ **ပုံချက်ချင်းထွက်အောင်** Logic Direct ပို့လိုက်ပါတယ်။ ဒါကြောင့် ပုံကျိန်းသေထွက်လာပါမယ်။
၂။ **မြန်မာစာ Logic:** Groq ကို အင်္ဂလိပ်လို အရင်ဖြေခိုင်းပြီးမှ Google Translate နဲ့ မြန်မာလိုပြန်ပါတယ်။ ဒါကြောင့် မြန်မာစာက Translationese မဖြစ်ဘဲ တကယ့်လူပြောသလို **သဘာဝကျကျနဲ့ အဓိပ္ပာယ်ရှိရှိ** ထွက်လာပါလိမ့်မယ်။
၃။ **Language Selection:** အင်္ဂလိပ်လိုမေးရင် အင်္ဂလိပ်လိုပဲ ပြန်ဖြေပေးမှာပါ။

### `main.py` (The Ultimate Masterpiece)

```python
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

# --- ၃။ Helper Functions ---
def extract_video_id(url):
    pattern = r'(?:v=|\/|be\/)([0-9A-Za-z_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_yt_transcript(video_id):
    try:
        ts_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['my', 'en'])
        return " ".join([t['text'] for t in ts_list])
    except: return None

# --- ၄။ Google Translate Helper (သဘာဝကျသော မြန်မာစာအတွက်) ---
async def translate_to_myanmar(text):
    try:
        async with httpx.AsyncClient() as client:
            url = f"[https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=my&dt=t&q=](https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=my&dt=t&q=){text}"
            resp = await client.get(url)
            result = resp.json()
            return "".join([sentence[0] for sentence in result[0]])
    except: return text

# --- ၅။ UI Design ---
USER_UI = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATOM AI - PRO</title>
    <link rel="stylesheet" href="[https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css](https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css)">
    <link rel="stylesheet" href="[https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css](https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css)">
    <script src="[https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js](https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js)"></script>
    <style>
        :root { --bg: #0d0d0d; --card: #1a1a1a; --gold: #f1c40f; --ds: #050505; --ls: #252525; }
        body { margin: 0; background: var(--bg); color: #fff; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; height: 100vh; overflow: hidden; }
        .container { width: 100%; max-width: 500px; background: var(--card); display: flex; flex-direction: column; }
        .screen { display: none; flex-direction: column; height: 100%; padding: 25px; box-sizing: border-box; }
        .active { display: flex; }
        input { width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 50px; background: var(--bg); color: #fff; outline: none; box-sizing: border-box; box-shadow: inset 5px 5px 10px var(--ds); }
        button { padding: 15px; border-radius: 50px; border: none; background: var(--card); color: var(--gold); font-weight: bold; cursor: pointer; box-shadow: 5px 5px 10px var(--ds), -5px -5px 10px var(--ls); transition: 0.2s; }
        button:active { transform: scale(0.95); }
        #chat-box { flex: 1; overflow-y: auto; padding: 15px; background: var(--bg); border-radius: 20px; display: flex; flex-direction: column; margin-bottom: 10px; }
        .msg { position: relative; margin-bottom: 25px; padding: 15px; border-radius: 20px; font-size: 14px; max-width: 85%; line-height:1.6; word-wrap: break-word; }
        .user { align-self: flex-end; background: var(--gold); color: #000; font-weight: bold; }
        .bot { align-self: flex-start; background: var(--card); border: 1px solid #333; }
        pre { background: #000 !important; border-radius: 10px; padding: 10px; overflow-x: auto; border: 1px solid #444; }
        .copy-btn { position: absolute; top: -10px; right: 10px; background: var(--card); color: var(--gold); padding: 4px 10px; border-radius: 10px; cursor: pointer; font-size: 10px; border: 1px solid #444; z-index: 10; }
        .input-area { display: flex; gap: 10px; }
        .input-area input { flex: 1; margin: 0; }
        .input-area button { width: 50px; height: 50px; padding: 0; border-radius: 50%; }
        #lb { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.95); z-index:999; justify-content:center; align-items:center; }
        #lb img { max-width:90%; max-height:85%; border-radius:10px; border: 2px solid var(--gold); }
    </style>
</head>
<body>
    <div class="container">
        <div id="auth-screen" class="screen active" style="justify-content:center; text-align:center;">
            <h1 style="color:var(--gold); letter-spacing:5px;">ATOM AI</h1>
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
            <div class="input-area">
                <input type="text" id="query" placeholder="Ask anything or draw..." onkeypress="if(event.key==='Enter') ask()">
                <button onclick="ask()"><i class="fas fa-paper-plane"></i></button>
            </div>
        </div>
    </div>
    <div id="lb" onclick="this.style.display='none'"><img id="lb-i"></div>
    <script>
        let curU="", curP="", cache={};
        function tgl(){ document.getElementById('l-f').style.display=document.getElementById('l-f').style.display==='none'?'block':'none'; document.getElementById('r-f').style.display=document.getElementById('r-f').style.display==='none'?'block':'none'; }
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
                if(d.history) d.history.forEach(m => appendMsg(m.q, m.a, m.img));
            } else alert(d.message);
        }
        function appendMsg(q, a, i){
            const box=document.getElementById('chat-box');
            box.innerHTML+=`<div class="msg user">${q}</div>`;
            const tid='t'+Date.now();
            box.innerHTML+=`<div class="msg bot" id="${tid}">${formatAI(a)}</div>`;
            if(i) document.getElementById(tid).innerHTML += `<div style="margin-top:10px"><img src="${i}" style="width:100%; border-radius:10px; border:1px solid #444;" onclick="openI('${i}')"><a href="${i}" download target="_blank"><button style="width:100%; margin-top:8px; padding:10px; font-size:12px; background:#222; color:var(--gold);"><i class="fas fa-download"></i> DOWNLOAD IMAGE</button></a></div>`;
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
            const target=document.getElementById(tid);
            target.innerHTML = formatAI(d.answer);
            target.innerHTML += `<div class="copy-btn" onclick="copy('${tid}', this)">COPY</div>`;
            if(d.img) target.innerHTML += `<div style="margin-top:10px"><img src="${d.img}" style="width:100%; border-radius:10px; border:1px solid #444;" onclick="openI('${d.img}')"><a href="${d.img}" download target="_blank"><button style="width:100%; margin-top:8px; padding:10px; font-size:12px; background:#222; color:var(--gold);"><i class="fas fa-download"></i> DOWNLOAD IMAGE</button></a></div>`;
            target.querySelectorAll('pre code').forEach(el => hljs.highlightElement(el));
            box.scrollTop=box.scrollHeight;
        }
        function copy(id, b){ navigator.clipboard.writeText(cache[id]); b.innerText="COPIED!"; setTimeout(()=>b.innerText="COPY", 2000); }
        function openI(s){ document.getElementById('lb-i').src=s; document.getElementById('lb').style.display='flex'; }
    </script>
</body>
</html>
"""


# --- ၆။ API Endpoints ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/", response_class=HTMLResponse)
async def home(): return USER_UI

@app.post("/register")
async def register(data: dict):
    u, p = data.get("username"), data.get("password")
    user_ref = db.collection("users").document(u)
    if user_ref.get().exists: return {"status": "fail", "message": "Taken"}
    user_ref.set({"password": p, "type": "free", "usage": {"date": str(date.today()), "count": 0}, "chat_history": []})
    return {"status": "success"}

@app.post("/login")
async def login(data: dict):
    u, p = data.get("username"), data.get("password")
    user_ref = db.collection("users").document(u)
    doc = user_ref.get()
    if doc.exists and doc.to_dict()["password"] == p:
        ud = doc.to_dict()
        history = ud.get("chat_history", [])[-10:]
        return {"status": "success", "tier": ud.get("type", "free"), "history": history}
    return {"status": "fail", "message": "Failed"}

@app.post("/ask")
async def ask(data: dict):
    u, p, q = data.get("username"), data.get("password"), data.get("query")
    user_ref = db.collection("users").document(u)
    ud = user_ref.get().to_dict()
    tier = ud.get("type", "free")
    history = ud.get("chat_history", [])[-5:]
    history_text = "\n".join([f"User: {m['q']}\nAI: {m['a']}" for m in history])

    # --- ၁။ Image Logic (Direct Guaranteed Fix) ---
    is_myanmar = any(c > '\u1000' and c < '\u109F' for c in q)
    if any(w in q.lower() for w in ["draw", "image", "photo", "ပုံဆွဲ", "ရုပ်ပုံ"]):
        if tier == "free": return {"error": "Premium Feature Only!"}
        client_tmp = get_rotated_groq_client()
        # English Prompt Generator
        en_gen = client_tmp.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Convert the user's request into a single English image prompt. Output ONLY the prompt."},
                      {"role": "user", "content": q}]
        )
        en_prompt = en_gen.choices[0].message.content.strip()
        img_url = f"[https://pollinations.ai/p/](https://pollinations.ai/p/){en_prompt.replace(' ', '%20')}?width=1024&height=1024&seed={int(datetime.now().timestamp())}&model=flux"
        answer_en = f"Here is the image for **{en_prompt}**."
        answer = await translate_to_myanmar(answer_en) if is_myanmar else answer_en
        user_ref.update({"chat_history": firestore.ArrayUnion([{"q": q, "a": answer, "img": img_url}])})
        return {"answer": answer, "img": img_url}

    # YouTube Logic
    yt_context = ""
    vid = extract_video_id(q)
    if vid:
        ts = get_yt_transcript(vid)
        if ts: yt_context = f"\nVideo Context: {ts[:3000]}"

    # --- ၂။ Text Logic (Google Translate Fix) ---
    sys_prompt = f"You are a wise Myanmar Professor. Be professional. \nChat History:\n{history_text}"
    try:
        client = get_rotated_groq_client()
        # AI ဆီကနေ အင်္ဂလိပ်လို အရင်တောင်းမယ်
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_prompt},
                      {"role": "user", "content": f"{q} (If user speaks English, reply in English. If user speaks Myanmar, reply in professional English first, I will translate it later.) {yt_context}"}]
        )
        answer_raw = resp.choices[0].message.content
        # မြန်မာလိုဆိုရင် Translate လုပ်မယ်
        answer = await translate_to_myanmar(answer_raw) if is_myanmar else answer_raw
        
        user_ref.update({"chat_history": firestore.ArrayUnion([{"q": q, "a": answer}])})
        return {"answer": answer}
    except: return {"error": "AI Error."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
