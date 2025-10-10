import os, requests
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

def ollama_chat(messages, temperature: float = 0.1, model: str | None = None):
    r = requests.post(f"{OLLAMA_HOST}/api/chat", json={
        "model": model or MODEL,
        "messages": messages,
        "stream": False,  # Disable streaming for simpler JSON parsing
        "options": {"temperature": temperature, "num_ctx": 2048}
    }, timeout=120)
    r.raise_for_status()
    response_data = r.json()
    return response_data["message"]["content"]
