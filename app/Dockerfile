FROM python:3.9.6

ENV PYTHONPATH "${PYTHONPATH}:/app"

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD sh -c "sleep 10 && uvicorn main:app --host 0.0.0.0 --port 3000 --reload"
