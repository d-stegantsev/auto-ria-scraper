FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y postgresql-client

COPY docker-wait-for-db.sh /app/docker-wait-for-db.sh
RUN chmod +x /app/docker-wait-for-db.sh

ENTRYPOINT ["/app/docker-wait-for-db.sh"]
CMD ["scrapy", "crawl", "autoriaspider"]
