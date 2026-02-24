FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y wget tar && \
    mkdir -p /app/data && \
    wget -O /tmp/GeoLite2-City.tar.gz "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb.tar.gz" && \
    tar -xzf /tmp/GeoLite2-City.tar.gz -C /tmp && \
    find /tmp -name "*.mmdb" -exec mv {} /app/data/GeoLite2-City.mmdb \; && \
    rm -rf /tmp/GeoLite2-City.tar.gz /tmp/GeoLite2-City_* && \
    apt-get remove -y wget tar && apt-get autoremove -y && apt-get clean

COPY . .
EXPOSE 8000
CMD ["gunicorn", "chatPsych:app", "-w", "4", "-b", "0.0.0.0:8000"]