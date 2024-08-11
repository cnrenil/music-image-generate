FROM python:3.12

COPY . /app

WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install firefox

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

