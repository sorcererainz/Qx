FROM python:3.11

# Install Chrome directly
RUN apt-get update && apt-get install -y wget gnupg \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && apt-get clean

# Install ChromeDriver
RUN apt-get install -y chromium-chromedriver \
    && ln -s /usr/lib/chromium-browser/chromedriver /usr/local/bin/chromedriver

# Setup app
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
