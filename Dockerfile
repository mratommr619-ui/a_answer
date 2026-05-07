FROM python:3.10-bullseye

# Browser အတွက် လိုအပ်တာတွေ အကုန်သွင်းမယ်
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Browser သွင်းမယ်
RUN playwright install chromium
RUN playwright install-deps chromium

# --- ဒီအပိုင်းက အရေးကြီးဆုံးပါ ---
# GitHub ထဲမှာ သင်သိမ်းထားတဲ့ session_data folder ကို Docker image ထဲ ကူးထည့်တာ
COPY ./session_data /app/session_data

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
