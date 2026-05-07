FROM python:3.10-bullseye

# အခြေခံ လိုအပ်ချက်များ
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright ကို manual သွင်းမယ်
RUN playwright install chromium
RUN playwright install-deps chromium

# session_data folder မရှိရင် ဆောက်ထားမယ်
RUN mkdir -p /app/session_data

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
