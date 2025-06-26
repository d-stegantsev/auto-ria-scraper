FROM python:3.11

WORKDIR /app

COPY parse.py .
COPY requirements.txt .
COPY docker-wait-for-db.sh .

RUN apt-get update && \
    apt-get install -y wget unzip postgresql-client \
    && wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb

RUN pip install --no-cache-dir -r requirements.txt

RUN chmod +x docker-wait-for-db.sh

ENTRYPOINT ["/app/docker-wait-for-db.sh"]
CMD ["python", "parse.py"]
