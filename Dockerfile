# Single image running FastAPI (uvicorn) + Streamlit behind nginx on one port.

FROM python:3.10.6-slim

RUN apt-get update && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN rm -f /etc/nginx/sites-enabled/default
COPY nginx.conf /etc/nginx/sites-enabled/default

EXPOSE 80

CMD bash -c "\
    uvicorn api:app --host 0.0.0.0 --port 8000 & \
    streamlit run ui.py --server.port=8501 --server.address=0.0.0.0 & \
    nginx -g 'daemon off;'"
