import os
import asyncio
import httpx
import json
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from datetime import datetime, date
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(lifespan=lifespan)

# CORS ကို အကုန်ဖွင့်ပေးလိုက်ခြင်း (ဒါမှ Firebase ကနေ ခေါ်လို့ရမှာပါ)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- Firebase Setup ---
def init_firebase():
    fb_config_str = os.getenv("FIREBASE_CONFIG_JSON")
    if not fb_config_str: return None
    cred = credentials.Certificate(json.loads(fb_config_str))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# --- Gemini API Setup ---
API_KEYS = [k.strip() for k in os.getenv("GEMINI_KEYS", "").split(",") if k.strip()]
current_index = 0

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
if os.path.exists("public"):
    app.mount("/public", StaticFiles(directory="public"), name="public")

def get_rotated_model():
    global current_index
    if not API_KEYS: return None
    genai.configure(api_key=API_KEYS[current_index])
    current_index = (current_index + 1) % len(API_KEYS)
    return genai.GenerativeModel('gemini-1.5-flash')

# --- Helper: Check Expiry ---
def check_expiry(udata):
    if udata.get("type") == "premium" and udata.get("expiry_date"):
        try:
            exp = datetime.strptime(udata["expiry_date"], "%Y-%m-%d").date()
            if exp < date.today(): return True
        except: pass
    return False

# --- UI Designs (ဖောင်းကြွ + Code Color Highlighting) ---
USER_UI = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATOM AI - NEUMORPHIC PRO</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        :root { --bg: #121212; --card: #1e1e1e; --gold: #f1c40f; --dark-shadow: #0a0a0a; --light-shadow: #2a2a2a; }
        body { margin: 0; background: var(--bg); color: #fff; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; height: 100vh; overflow: hidden; }
        
        .container { 
            width: 100%; max-width: 500px; background: var(--card); 
            display: flex; flex-direction: column; 
            box-shadow: 20px 20px 60px var(--dark-shadow), -20px -20px 60px var(--light-shadow);
        }

        .screen { display: none; flex-direction: column; height: 100%; padding: 20px; box-sizing: border-box; }
        .active { display: flex; }

        /* Neumorphic Input & Button */
        input {
            width: 90%; padding: 15px; margin: 15px 0; border: none; border-radius: 50px;
            background: var(--bg); color: #fff; outline: none;
            box-shadow: inset 6px 6px 12px var(--dark-shadow), inset -6px -6px 12px var(--light-shadow);
        }

        button {
            padding: 15px 30px; border-radius: 50px; border: none;
            background: var(--card); color: var(--gold); font-weight: bold; cursor: pointer;
            box-shadow: 6px 6px 12px var(--dark-shadow), -6px -6px 12px var(--light-shadow);
            transition: 0.2s;
        }
        button:active { box-shadow: inset 4px 4px 8px var(--dark-shadow), inset -4px -4px 8px var(--light-shadow); transform: scale(0.98); }

        /* Chat Area */
        #chat-box { 
            flex: 1; overflow-y: auto; padding: 15px; margin: 15px 0;
            background: var(--bg); border-radius: 20px;
            box-shadow: inset 8px 8px 16px var(--dark-shadow), inset -8px -8px 16px var(--light-shadow);
        }
        .msg { position: relative; margin-bottom: 25px; padding: 15px; border-radius: 20px; font-size: 14px; line-height: 1.6; max-width: 85%; word-wrap: break-word; }
        .user { align-self: flex-end; background: var(--gold); color: #000; box-shadow: 4px 4px 10px rgba(0,0,0,0.3); }
        .bot { align-self: flex-start; background: var(--card); border: 1px solid #333; box-shadow: 6px 6px 12px var(--dark-shadow); }
        
        /* Code Box styling */
        pre { background: #000 !important; border-radius: 10px; padding: 10px; overflow-x: auto; margin: 10px 0; border: 1px solid #444; }
        code { font-family: 'Consolas', monospace; }

        .copy-btn { position: absolute; top: -10px; right: 10px; background: var(--card); border: 1px solid #444; color: var(--gold); padding: 5px 10px; border-radius: 10px; cursor: pointer; font-size: 10px; box-shadow: 3px 3px 6px #000; }

        .input-area { display: flex; gap: 10px; align-items: center; }
        .input-area input { flex: 1; margin: 0; }
        .input-area button { width: 50px; height: 50px; padding: 0; border-radius: 50%; }

        /* Lightbox for images */
        #lb { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.9); z-index:99; justify-content:center; align-items:center; flex-direction:column; }
        #lb img { max-width:90%; max-height:80%; border-radius:15px; box-shadow: 0 0 20px var(--gold); }
    </style>
</head>
<body>
    <div class="container">
        <div id="auth-screen" class="screen active" style="justify-content:center; text-align:center;">
            <h1 style="color:var(--gold); letter-spacing:5px; text-shadow: 2px 2px 4px #000;">ATOM AI</h1>
            <div id="l-f">
                <input type="text" id="u" placeholder="Username">
                <input type="password" id="p" placeholder="Password">
                <button onclick="auth('login')">SIGN IN</button>
                <p onclick="tgl()" style="color:var(--gold); cursor:pointer; font-size:12px; margin-top:25px;">No account? Register</p>
            </div>
            <div id="r-f" style="display:none">
                <input type="text" id="ru" placeholder="Username">
                <input type="password" id="rp" placeholder="Password">
                <button onclick="auth('register')">CREATE ACCOUNT</button>
                <p onclick="tgl()" style="color:var(--gold); cursor:pointer; font-size:12px; margin-top:25px;">Back to Login</p>
            </div>
        </div>

        <div id="chat-screen" class="screen">
            <div style="display:flex; justify-content:space-between; align-items:center; padding-bottom:10px; border-bottom:1px solid #333;">
                <b id="du" style="color:var(--gold)"></b>
                <span id="dt" style="font-size:10px; color:var(--gold); border:1px solid; padding:2px 8px; border-radius:20px;"></span>
            </div>
            <div id="chat-box" style="display:flex; flex-direction:column;"></div>
            <div class="input-area">
                <input type="text" id="query" placeholder="Type a message...">
                <button onclick="ask()"><i class="fas fa-paper-plane"></i></button>
            </div>
        </div>
    </div>

    <div id="lb" onclick="this.style.display='none'"><img id="lb-i"><p style="color:#666; margin-top:10px;">Tap to close</p></div>

    <script>
        let curU="", curP="", cache={};
        function tgl(){ const l=document.getElementById('l-f'),r=document.getElementById('r-f'); l.style.display=l.style.display==='none'?'block':'none'; r.style.display=r.style.display==='none'?'block':'none'; }
        
        async function auth(t){
            const u=t==='login'?document.getElementById('u').value:document.getElementById('ru').value;
            const p=t==='login'?document.getElementById('p').value:document.getElementById('rp').value;
            const r=await fetch("/"+t,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:u,password:p})});
            const d=await r.json();
            if(d.status==='success'){
                if(t==='register'){alert("Registered!");tgl();}
                else { curU=u;curP=p; document.getElementById('auth-screen').classList.remove('active'); document.getElementById('chat-screen').classList.add('active'); document.getElementById('du').innerText=u.toUpperCase(); document.getElementById('dt').innerText=d.tier.toUpperCase(); }
            } else { alert(d.message || "Login Failed"); }
        }

        function formatAI(t) {
            // Code Blocks formatting with Highlighting
            let res = t.replace(/```(\w+)?\n([\s\S]*?)```/g, (m, lang, code) => {
                return `<pre><code class="language-${lang || 'plaintext'}">${code.trim()}</code></pre>`;
            });
            return res.replace(/\n/g, '<br>');
        }

        async function ask(){
            const box=document.getElementById('chat-box'), input=document.getElementById('query');
            const q=input.value; if(!q) return; input.value='';
            box.innerHTML+=`<div class="msg user">${q}</div>`;
            const tid='t'+Date.now();
            box.innerHTML+=`<div class="msg bot" id="${tid}"><i class="fas fa-circle-notch fa-spin"></i> ATOM is thinking...</div>`;
            box.scrollTop=box.scrollHeight;

            const res=await fetch("/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:curU,password:curP,query:q})});
            const d=await res.json();
            const target=document.getElementById(tid);
            
            if(d.answer){
                cache[tid] = d.answer;
                target.innerHTML = formatAI(d.answer);
                target.innerHTML += `<div class="copy-btn" onclick="copy('${tid}', this)">COPY</div>`;
                
                // Highlight Code
                target.querySelectorAll('pre code').forEach(el => hljs.highlightElement(el));

                if(d.img) {
                    target.innerHTML += `<div style="margin-top:10px" onclick="openI('${d.img}')"><img src="${d.img}" style="width:100%; border-radius:10px;"></div>`;
                }
            } else { target.innerHTML = d.error; }
            box.scrollTop=box.scrollHeight;
        }

        function copy(id, b){
            navigator.clipboard.writeText(cache[id]);
            b.innerText = "COPIED!";
            setTimeout(()=> b.innerText="COPY", 2000);
        }
        function openI(src){ document.getElementById('lb-i').src=src; document.getElementById('lb').style.display='flex'; }
    </script>
</body>
</html>
"""

# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def user_home(): return USER_UI

@app.post("/register")
async def register(data: dict):
    u, p = data.get("username"), data.get("password")
    user_ref = db.collection("users").document(u)
    if user_ref.get().exists: return {"status": "fail", "message": "Username exists"}
    user_ref.set({"password": p, "type": "free", "usage": {"date": str(date.today()), "count": 0}})
    return {"status": "success"}

@app.post("/login")
async def login(data: dict):
    u, p = data.get("username"), data.get("password")
    user_ref = db.collection("users").document(u)
    doc = user_ref.get()
    if doc.exists:
        udata = doc.to_dict()
        if udata["password"] == p:
            if check_expiry(udata):
                user_ref.update({"type": "free", "expiry_date": None})
                return {"status": "success", "tier": "free"}
            return {"status": "success", "tier": udata["type"]}
    return {"status": "fail"}

@app.post("/ask")
async def ask_ai(data: dict):
    u, p, q = data.get("username"), data.get("password"), data.get("query")
    user_ref = db.collection("users").document(u)
    user_data = user_ref.get().to_dict()
    if not user_data or user_data["password"] != p: return {"error": "Unauthorized"}
    
    tier, today = user_data["type"], str(date.today())
    usage = user_data.get("usage", {"date": today, "count": 0})
    if usage["date"] != today: usage = {"date": today, "count": 0}

    if tier == "free":
        if usage["count"] >= 5: return {"error": "Free Limit Reached (5/5). Contact @mratom_619"}
        usage["count"] += 1
        user_ref.update({"usage": usage})

    try:
        model = get_rotated_model()
        response = model.generate_content(q)
        return {"answer": response.text}
    except Exception as e: return {"error": str(e)}

# --- Admin Section ---

@app.get("/admin", response_class=FileResponse)
async def admin_page(): return "public/admin.html"

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
