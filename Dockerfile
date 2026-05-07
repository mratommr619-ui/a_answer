FROM python:3.11

# Playwright browser အတွက် လိုအပ်တဲ့ Linux dependencies အကုန်သွင်းတာပါ
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxext6 libxfixes3 \
    librandr2 libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# လိုအပ်တဲ့ libraries တွေ သွင်းမယ်
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chromium browser ကို သွင်းမယ်
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

# Hugging Face က port 7860 ကို သုံးတာဖြစ်လို့ အတိအကျပေးရပါမယ်
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
