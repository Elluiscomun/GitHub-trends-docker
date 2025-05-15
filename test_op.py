import requests

# 🔐 Tu API Key de OpenRouter
OPENROUTER_API_KEY = "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"  # <-- reemplaza esto con tu clave

# 📘 Repositorio de GitHub
owner = "microsoft"
repo = "BitNet"
url = f"https://api.github.com/repos/{owner}/{repo}/readme"
headers = {"Accept": "application/vnd.github.v3.raw"}

response = requests.get(url, headers=headers)
if response.status_code != 200:
    print("Error al obtener README:", response.status_code)
    exit()

readme = response.text

# 🧠 Pregunta para el modelo
pregunta = "devuelme un json con resumen de habilidades detectadas"

# ✉️ Construcción del mensaje para el LLM
mensajes = [
    {"role": "system", "content": "Eres un experto en análisis de proyectos de software."},
    {"role": "user", "content": f"Aquí está el README de un proyecto:\n\n{readme}"},
    {"role": "user", "content": pregunta}
]

# 📡 Llamada a la API de OpenRouter
respuesta = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "nousresearch/deephermes-3-mistral-24b-preview:free",  # Puedes usar otros modelos como openchat, llama3, etc.
        "messages": mensajes
    }
)

if respuesta.status_code == 200:
    contenido = respuesta.json()
    print("\n📌 Respuesta de la IA:\n")
    print(contenido["choices"][0]["message"]["content"])
else:
    print("Error al llamar a OpenRouter:", respuesta.status_code)
    print(respuesta.text)
