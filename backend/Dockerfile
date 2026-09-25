FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# default: bot em polling (simples p/ lançar). Para webhook:
#   CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["python", "run_bot.py"]
