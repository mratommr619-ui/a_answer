FROM python:3.11

# လိုအပ်တဲ့ Linux dependencies တွေကို Debian Trixie နဲ့ ကိုက်အောင် လက်နဲ့ သွင်းပေးခြင်း
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    librandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    fonts-liberation \
    libv4l-0 \
    libu2f-udev \
    libxml2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements သွင်းခြင်း
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Browser သွင်းခြင်း (install-deps ကို မသုံးတော့ဘဲ install ပဲ သုံးမည်)
RUN playwright install chromium

COPY . .

# Port သတ်မှတ်ချက်
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
