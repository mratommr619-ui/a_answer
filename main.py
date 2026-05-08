import os
import asyncio
import httpx
import json
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, date

# --- 1. Firebase Configuration ---
def init_firebase():
    fb_config_str = os.getenv("FIREBASE_CONFIG_JSON")
    if not fb_config_str: return None
    cred = credentials.Certificate(json.loads(fb_config_str))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# --- 2. Gemini API Key Rotation ---
API_KEYS = [k.strip() for k in os.getenv("GEMINI_KEYS", "").split(",") if k.strip()]
current_index = 0

def get_api_key():
    global current_index
    if not API_KEYS: return None
    key = API_KEYS[current_index]
    current_index = (current_index + 1) % len(API_KEYS)
    return key

# --- 3. Keep Alive ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(keep_alive())
    yield

async def keep_alive():
    url = os.getenv("RENDER_EXTERNAL_URL")
    if not url: return
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(600)
            try: await client.get(url)
            except: pass

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def check_expiry(udata):
    if udata.get("type") == "premium" and udata.get("expiry_date"):
        try:
            exp = datetime.strptime(udata["expiry_date"], "%Y-%m-%d").date()
            if exp < date.today(): return True
        except: pass
    return False

# --- 4. UI Design (Enter to Send & All Logic Included) ---
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
        #chat-box { flex: 1; overflow-y: auto; padding: 15px; background: var(--bg); border-radius: 20px; display: flex; flex-direction: column; margin-bottom: 10px; }
        .msg { position: relative; margin-bottom: 25px; padding: 15px; border-radius: 20px; font-size: 14px; max-width: 85%; line-height:1.6; word-wrap: break-word; }
        .user { align-self: flex-end; background: var(--gold); color: #000; font-weight: bold; }
        .bot { align-self: flex-start; background: var(--card); border: 1px solid #333; }
        pre { background: #000 !important; border-radius: 10px; padding: 10px; overflow-x: auto; border: 1px solid #444; }
        .copy-btn { position: absolute; top: -10px; right: 10px; background: var(--card); color: var(--gold); padding: 4px 10px; border-radius: 10px; cursor: pointer; font-size: 10px; border: 1px solid #444; }
        .input-area { display: flex; gap: 10px; }
        .input-area input { flex: 1; margin: 0; }
        .input-area button { width: 50px; height: 50px; padding: 0; border-radius: 50%; }
    </style>
</head>
<body>
    <div class="container">
        <div id="auth-screen" class="screen active" style="justify-content:center; text-align:center;">
            <h1 style="color:var(--gold); letter-spacing:5px;">ATOM AI</h1>
            <div id="l-f">
                <input type="text" id="u" placeholder="Username" onkeypress="if(event.key==='Enter') auth('login')">
                <input type="password" id="p" placeholder="Password" onkeypress="if(event.key==='Enter') auth('login')">
                <button onclick="auth('login')" style="width:100%">SIGN IN</button>
                <p onclick="tgl()" style="color:var(--gold); cursor:pointer; font-size:12px; margin-top:20px;">Register Account</p>
            </div>
            <div id="r-f" style="display:none">
                <input type="text" id="ru" placeholder="Username" onkeypress="if(event.key==='Enter') auth('register')">
                <input type="password" id="rp" placeholder="Password" onkeypress="if(event.key==='Enter') auth('register')">
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
                <input type="text" id="query" placeholder="Ask ATOM AI..." onkeypress="if(event.key==='Enter') ask()">
                <button onclick="ask()"><i class="fas fa-paper-plane"></i></button>
            </div>
        </div>
    </div>
    <script>
        let curU="", curP="", cache={};
        function tgl(){ document.getElementById('l-f').style.display=document.getElementById('l-f').style.display==='none'?'block':'none'; document.getElementById('r-f').style.display=document.getElementById('r-f').style.display==='none'?'block':'none'; }
        async function auth(t){
            const u=t==='login'?document.getElementById('u').value:document.getElementById('ru').value;
            const p=t==='login'?document.getElementById('p').value:document.getElementById('rp').value;
            if(!u || !p) return;
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
            try {
                const res=await fetch("/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:curU,password:curP,query:q})});
                const d=await res.json();
                const target=document.getElementById(tid);
                if(d.answer){
                    cache[tid] = d.answer;
                    target.innerHTML = formatAI(d.answer);
                    target.innerHTML += `<div class="copy-btn" onclick="copy('${tid}', this)">COPY</div>`;
                    target.querySelectorAll('pre code').forEach(el => hljs.highlightElement(el));
                } else target.innerHTML=`<span style="color:red">${d.error}</span>`;
            } catch(e) { document.getElementById(tid).innerText = "Error."; }
            box.scrollTop=box.scrollHeight;
        }
        function copy(id, b){ navigator.clipboard.writeText(cache[id]); b.innerText="COPIED!"; setTimeout(()=>b.innerText="COPY", 2000); }
    </script>
</body>
</html>
"""

# --- 5. Backend Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def home(): return USER_UI

@app.post("/register")
async def register(data: dict):
    u, p = data.get("username"), data.get("password")
    user_ref = db.collection("users").document(u)
    if user_ref.get().exists: return {"status": "fail", "message": "Username exists"}
    user_ref.set({"password": p, "type": "free", "usage": {"date": str(date.today()), "count": 0, "content_count": 0}})
    return {"status": "success"}

@app.post("/login")
async def login(data: dict):
    u, p = data.get("username"), data.get("password")
    user_ref = db.collection("users").document(u)
    doc = user_ref.get()
    if doc.exists and doc.to_dict()["password"] == p:
        ud = doc.to_dict()
        if check_expiry(ud): user_ref.update({"type": "free", "expiry_date": None})
        return {"status": "success", "tier": ud.get("type", "free")}
    return {"status": "fail", "message": "Login Failed"}

@app.post("/ask")
async def ask(data: dict):
    u, p, q = data.get("username"), data.get("password"), data.get("query")
    user_ref = db.collection("users").document(u)
    ud = user_ref.get().to_dict()
    
    tier, today = ud["type"], str(date.today())
    usage = ud.get("usage", {"date": today, "count": 0, "content_count": 0})
    if usage["date"] != today: usage = {"date": today, "count": 0, "content_count": 0}

    if tier == "free":
        if usage["count"] >= 5: return {"error": "Limit reached."}
        if any(w in q.lower() for w in ["write", "essay", "article", "ရေးပေး"]):
            if usage["content_count"] >= 2: return {"error": "Writing limit reached."}
            usage["content_count"] += 1
        if any(w in q.lower() for w in ["draw", "image", "ပုံဆွဲ"]): return {"error": "Premium Feature."}
        usage["count"] += 1
        user_ref.update({"usage": usage})

    try:
        # API Key ကို ယူပြီး model ကို အောက်ကအတိုင်း Direct ဆောက်ပါမယ်
        key = get_api_key()
        genai.configure(api_key=key)
        # အောက်က model နာမည်က standard အကျဆုံးပါပဲ
        model = genai.GenerativeModel('gemini-1.5-flash')
        resp = model.generate_content(q)
        return {"answer": resp.text}
    except Exception as e: return {"error": f"AI Error. Please try again."}

@app.post("/admin/list")
async def admin_list(data: dict):
    if data.get("pass") != os.getenv("ADMIN_PASSWORD"): return {"error": "Unauthorized"}
    users = [dict(doc.to_dict(), id=doc.id) for doc in db.collection("users").stream()]
    return {"users": users}

@app.post("/admin/update")
async def admin_upd(data: dict):
    if data.get("pass") != os.getenv("ADMIN_PASSWORD"): return {"error": "Unauthorized"}
    db.collection("users").document(data["target"]).update({"type": data["type"], "expiry_date": data["expiry"]})
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
