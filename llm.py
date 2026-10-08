"""Ollama LLM integration for Basta game."""
import re
from typing import Callable, Optional
import ollama

# Configurable model name constant (can also be passed via CLI --model)
# Default model: llama3.2 (3B for high reasoning/judging quality)
MODEL_NAME: str = "llama3.2"

def check_ollama(model: str = MODEL_NAME) -> None:
    """Verify Ollama is reachable and model is available."""
    try:
        models_info = ollama.list()
        raw_models = getattr(models_info, "models", None) or (
            models_info.get("models") if isinstance(models_info, dict) else []
        )
        available_models = []
        for m in raw_models:
            name = (
                getattr(m, "model", None)
                or getattr(m, "name", None)
                or (m.get("model") if isinstance(m, dict) else None)
            )
            if name:
                available_models.append(name)
    except Exception as e:
        raise ConnectionError(
            f"No se pudo conectar con el servidor Ollama ({e}).\n"
            "Asegúrate de que Ollama esté ejecutándose (`ollama serve`)."
        ) from e

    found = any(
        model == m or m.startswith(f"{model}:") or model.startswith(f"{m}:")
        for m in available_models
    )
    if not found and available_models:
        models_str = ", ".join(available_models)
        raise ValueError(
            f"El modelo '{model}' no está descargado.\n"
            f"Modelos disponibles en tu máquina: {models_str}\n"
            f"Para descargarlo, ejecuta: `ollama pull {model}`"
        )
    elif not found and not available_models:
        raise ValueError(
            f"No hay ningún modelo instalado en Ollama.\n"
            f"Para descargar el modelo '{model}', ejecuta: `ollama pull {model}`"
        )


def clean_word(raw: str) -> str:
    """Clean model response to isolate the pure Spanish word/phrase."""
    text = raw.strip()
    # Remove markdown emphasis, asterisks, backticks, quotes
    text = re.sub(r'[*_`"\'«»]', '', text).strip()
    # If model prefixed "Categoría: Palabra" or "Respuesta: Palabra"
    if ":" in text:
        text = text.split(":")[-1].strip()
    # If multiple lines, take first non-empty line
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        text = lines[0]
    # Remove trailing period, comma, semicolon
    text = text.rstrip(".,;")
    return text


def stream_category_word(
    letter: str,
    category: str,
    model: str = MODEL_NAME,
    on_token: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Stream generation of a single Spanish word for the category and letter.
    Calls `on_token(accumulated_text)` as each token arrives.
    """
    system_prompt = (
        "Eres un jugador autónomo en el juego tradicional de mesa 'Basta' (Tutti Frutti / Stop).\n"
        "Tu tarea es dar una sola palabra o nombre propio en idioma ESPAÑOL que corresponda a la categoría.\n"
        "REGLA CRÍTICA: La respuesta DEBE comenzar obligatoriamente con la letra indicada.\n"
        "Responde ÚNICAMENTE con la palabra o respuesta breve, sin oraciones, explicaciones, ni puntuación adicional."
    )

    user_prompt = (
        f"Ronda de Basta.\n"
        f"Letra obligatoria: '{letter.upper()}'.\n"
        f"Categoría: '{category}'.\n"
        f"Escribe una sola palabra en ESPAÑOL para '{category}' que comience con la letra '{letter.upper()}':"
    )

    accumulated = ""
    try:
        response_stream = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            options={"temperature": 0.2, "top_p": 0.9},
        )
        for chunk in response_stream:
            token = chunk.get("message", {}).get("content", "")
            if token:
                accumulated += token
                if on_token:
                    on_token(accumulated)
    except ollama.ResponseError as err:
        if err.status_code == 404:
            raise ValueError(
                f"Modelo '{model}' no encontrado. Ejecuta `ollama pull {model}`."
            ) from err
        raise RuntimeError(f"Error en respuesta de Ollama: {err}") from err
    except Exception as err:
        raise ConnectionError(
            f"Error de comunicación con Ollama ({err}).\n"
            "Verifica que el servicio de Ollama esté activo."
        ) from err

    return clean_word(accumulated)

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "evaluaciones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "categoria": {"type": "string"},
                    "valido": {"type": "boolean"},
                    "motivo": {"type": "string"},
                },
                "required": ["categoria", "valido", "motivo"],
            },
        }
    },
    "required": ["evaluaciones"],
}


def judge_categories(
    letter: str,
    answers: dict,
    judge_model: str = MODEL_NAME,
) -> dict:
    """
    Evaluate round answers using a second LLM as the referee/judge.
    Validates category fit, word existence in Spanish, and letter match.
    """
    import json
    from game import validate_word

    results = {}
    to_judge = {}

    # Step 1: Deterministic letter check
    for cat, word in answers.items():
        if not word or not word.strip():
            results[cat] = {"valido": False, "motivo": "Respuesta vacía"}
        elif not validate_word(word, letter):
            results[cat] = {
                "valido": False,
                "motivo": f"No comienza con la letra obligatoria '{letter.upper()}'",
            }
        else:
            to_judge[cat] = word

    if not to_judge:
        return results

    # Step 2: Query Judge LLM for category semantics
    case_lines = "\n".join(
        [f"- Categoría: {cat} | Respuesta: {w}" for cat, w in to_judge.items()]
    )
    prompt = (
        f"Eres el Árbitro Oficial del juego tradicional de mesa 'Basta' (Tutti Frutti / Stop) en español.\n"
        f"Letra de la ronda: '{letter.upper()}'.\n\n"
        "Evalúa si cada respuesta es VÁLIDA según las reglas del juego:\n"
        "- 'Nombre': Nombre de pila de persona en español (ej. Mónica, Manuel, María). SÍ es válido.\n"
        "- 'Apellido': Apellido de persona (ej. Mendoza, Morales, García). SÍ es válido.\n"
        "- 'País o Ciudad': Cualquier país, ciudad o capital real existente (ej. Málaga, Madrid, México). SÍ es válido.\n"
        "- 'Animal': Cualquier animal o ser vivo zoológico (ej. Mono, Murciélago). SÍ es válido. Si es un objeto, planta o palabra inventada, es FALSO.\n"
        "- 'Fruta o Flor': Cualquier fruta O flor (ej. Mango, Manzana, Margarita, Magnolia). SÍ es válido.\n"
        "- 'Objeto': Cosa u objeto físico inanimado (ej. Máscara, Mesa, Martillo). SÍ es válido.\n"
        "- 'Color': Cualquier color (ej. Marrón, Morado, Magenta). SÍ es válido.\n\n"
        f"Respuestas a dictaminar:\n{case_lines}\n\n"
        "Para cada categoría, indica 'valido' (true o false) y el 'motivo' breve de tu decisión."
    )

    try:
        response = ollama.chat(
            model=judge_model,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un árbitro estricto del juego Basta en español. Evalúas la pertenencia semántica de palabras a sus categorías.",
                },
                {"role": "user", "content": prompt},
            ],
            format=JUDGE_SCHEMA,
            options={"temperature": 0.1},
        )
        payload = json.loads(response["message"]["content"])
        for item in payload.get("evaluaciones", []):
            c = item.get("categoria")
            if c in to_judge:
                results[c] = {
                    "valido": bool(item.get("valido", False)),
                    "motivo": str(item.get("motivo", "")),
                }
    except Exception:
        # Fallback to letter validation if judge call fails
        for cat, word in to_judge.items():
            if cat not in results:
                results[cat] = {
                    "valido": True,
                    "motivo": f"Letra '{letter.upper()}' válida (arbitraje fallback)",
                }

    # Guarantee all categories have an entry
    for cat in answers:
        if cat not in results:
            results[cat] = {"valido": True, "motivo": "Aceptado"}

    return results
