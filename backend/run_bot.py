"""Entrypoint do bot em modo desenvolvimento (long-polling, sem webhook público).

Uso:
    cd backend && PYTHONPATH=. python3 run_bot.py

Em produção, prefira o modo webhook via FastAPI (app/api/main.py) atrás de HTTPS.
"""
from app.bot.handlers import run_polling

if __name__ == "__main__":
    print("♠️ Poker Hand Analyzer — bot iniciando em modo polling…")
    run_polling()
