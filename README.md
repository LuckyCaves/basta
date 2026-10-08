# 🎮 Basta (Tutti Frutti / Stop) Autónomo con LLM y DuckDB

Aplicación CLI en Python 3.10+ donde un modelo LLM local (vía Ollama) juega de forma completamente autónoma al tradicional juego de mesa en español **Basta** (Tutti Frutti / Stop), visualizando las respuestas en tiempo real mediante `rich` y guardando cada ronda en `duckdb`.

---

## 🚀 Requisitos e Instalación

### 1. Prerrequisitos
- Python 3.10 o superior.
- [Ollama](https://ollama.com/) instalado y en ejecución en tu equipo (`ollama serve`).

### 2. Entorno virtual e instalación de dependencias
```bash
# Crear entorno virtual
python -m venv .venv

# Activar en Windows
.venv\Scripts\activate
# O en Linux/macOS
# source .venv/bin/activate

# Instalar dependencias requeridas
pip install -r requirements.txt
# o directamente:
pip install ollama rich duckdb
```

### 3. Modelo de Ollama
Descarga el modelo predeterminado (`llama3.2:1b` o `llama3.2`):
```bash
ollama pull llama3.2:1b
```

---

## 🕹️ Uso y Ejecución

### Ejecutar una ronda estándar
```bash
python main.py
```

### Cambiar de modelo (`--model`)
Puedes configurar la constante `MODEL_NAME` en la parte superior de `main.py` y `llm.py`, o especificarlo dinámicamente:
```bash
python main.py --model llama3.2
python main.py --model mistral
```

### Jugar múltiples rondas consecutivas (`--rounds`)
```bash
python main.py --rounds 3
```

### Forzar una letra específica (`--letter`)
```bash
python main.py --letter M
```

### Consultar estadísticas globales de DuckDB (`--stats`)
```bash
python main.py --stats
```

---

## 📦 Estructura del Proyecto

- `main.py`: Punto de entrada CLI, ciclo principal del juego y orquestación.
- `game.py`: Categorías, exclusión de letras (Ñ, W, X), normalización de acentos (Á->A), validación y puntuación (10 / 0 pts).
- `llm.py`: Cliente de Ollama, prompts en español, streaming token por token y manejo robusto de errores de conexión.
- `ui.py`: Interfaz de terminal con `rich` (`Live`, `Table`, `Panel`), animación de selección de letra y canto de finalización.
- `db.py`: Persistencia en `basta_history.duckdb` (`rounds` y `round_words`) y consultas de estadísticas.
- `test_basta.py`: Suite de auto-verificación (validación de acentos, reglas de letras y operaciones DuckDB).

---

## 💾 Esquema de Base de Datos (DuckDB)

Persistido localmente en `basta_history.duckdb`:

- **`rounds`**: `(round_id VARCHAR, letter VARCHAR, model_name VARCHAR, timestamp TIMESTAMP, total_points INT)`
- **`round_words`**: `(round_id VARCHAR, category VARCHAR, word VARCHAR, is_valid BOOLEAN, points INT)`
