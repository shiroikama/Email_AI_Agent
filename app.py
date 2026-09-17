from fastapi import FastAPI
from datetime import datetime
import os
from dotenv import load_dotenv
from openai import OpenAI


# Загружаем переменные из .env
load_dotenv()

app = FastAPI(title="AI Sales Assistant", version="0.1")

@app.get("/health")
def health():
    return {
        "ok": True,
        "time": datetime.utcnow().isoformat() + "Z",
        "api_key_loaded": bool(os.getenv("OPENAI_API_KEY")),
    }


# Инициализируем клиент OpenAI с использованием API ключа из окружения
client = OpenAI()

# Тестовый эндпоинт для проверки работы модели
@app.get("/test_ai")
def test_ai():
    """
    Проверяем, что можем обратиться к модели и получить ответ.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a concise assistant."},
                {"role": "user", "content": "Назови столицу Австралии."},
            ],
        )
        answer = response.choices[0].message.content

        # если ответ неожиданно пришёл байтами — после некоторых серверов так бывает
        if isinstance(answer, bytes):
            answer = answer.decode("utf-8", errors="ignore")

        return {"ok": True, "answer": str(answer)}

    except Exception as e:
        return {"ok": False, "error": str(e)}




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")