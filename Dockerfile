FROM python:3.11

# System အခြေခံလိုအပ်ချက်အချို့ကိုပဲ အရင်သွင်းမယ်
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements သွင်းခြင်း
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- ဒီအပိုင်းက အရေးကြီးဆုံးပါ ---
# Playwright ရော၊ သူ့အတွက်လိုအပ်တဲ့ Linux dependencies တွေရော အကုန် သူ့ဘာသာသူ ရှာသွင်းခိုင်းလိုက်တာပါ
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

# Port သတ်မှတ်ချက်
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
