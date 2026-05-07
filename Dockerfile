# 3.10-bullseye က Playwright နဲ့ အကိုက်ညီဆုံးပါ
FROM python:3.10-bullseye

# အခြေခံ အလိုအပ်ဆုံးတွေပဲ သွင်းမယ်
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright ကို သူ့ဘာသာသူ အကုန်သွင်းခိုင်းမယ် (Bullseye မှာ error မတက်ပါ)
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
