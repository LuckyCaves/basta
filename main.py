#!/usr/bin/env python3
"""
Basta (Tutti Frutti / Stop) - Autonomous LLM Game in Spanish with DuckDB Logging.
"""
import argparse
from datetime import datetime
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel

import db
from game import CATEGORIES, animate_letter_selection, score_entry
import llm
import ui

# Configurable default model (can also be passed via --model CLI flag)
# Default is llama3.2 (3B); to use a lightweight model: python main.py --model llama3.2:1b
MODEL_NAME: str = "llama3.2"

def play_round(
    console: Console,
    conn: Any,
    model_name: str,
    judge_model: str,
    history_rounds: List[Dict[str, Any]],
    forced_letter: Optional[str] = None,
    delay: float = 0.02,
) -> Dict[str, Any]:
    """Execute a single autonomous round of Basta with dual LLM (Player + Judge)."""
    round_id = str(uuid.uuid4())

    # 1. Letter selection with alphabet counting animation
    letter = animate_letter_selection(console, target_letter=forced_letter)

    # 2. Live table initialization
    current_data: Dict[str, str] = {cat: "[dim]⏳ pendiente[/dim]" for cat in CATEGORIES}
    current_total: str = "[dim]---[/dim]"
    raw_words: Dict[str, str] = {}

    table = ui.build_sheet_table(console, history_rounds, letter, current_data, current_total)

    # 3. Category-by-category streaming live update
    with Live(table, console=console, refresh_per_second=15) as live:
        for cat in CATEGORIES:
            current_data[cat] = "[bold yellow]🤔 pensando...[/bold yellow]"
            live.update(
                ui.build_sheet_table(console, history_rounds, letter, current_data, current_total)
            )
            time.sleep(0.15)

            def on_token(accumulated: str) -> None:
                # Live typing effect
                cleaned_preview = accumulated.strip().replace("\n", " ")[:20]
                current_data[cat] = f"[bold white]{cleaned_preview}▌[/bold white]"
                live.update(
                    ui.build_sheet_table(console, history_rounds, letter, current_data, current_total)
                )

            # Query Ollama for this category
            word = llm.stream_category_word(letter, cat, model=model_name, on_token=on_token)
            raw_words[cat] = word
            current_data[cat] = f"[bold cyan]{word}[/bold cyan]"
            live.update(
                ui.build_sheet_table(console, history_rounds, letter, current_data, current_total)
            )
            time.sleep(max(0.1, delay))

    # 4. Finishing phrase
    ui.display_chant(console)

    # 5. Autonomous validation & scoring via Judge LLM
    console.print(f"[bold cyan]⚖️  Árbitro LLM ({judge_model}) deliberando...[/bold cyan]")
    evaluations = llm.judge_categories(letter, raw_words, judge_model=judge_model)

    round_words_data: List[Dict[str, Any]] = []
    total_points = 0
    words_summary: Dict[str, Dict[str, Any]] = {}

    for cat in CATEGORIES:
        word = raw_words.get(cat, "")
        eval_entry = evaluations.get(cat, {"valido": False, "motivo": "Sin evaluar"})
        is_valid = bool(eval_entry.get("valido", False))
        points = 10 if is_valid else 0
        reason = str(eval_entry.get("motivo", ""))
        total_points += points
        round_words_data.append({
            "category": cat,
            "word": word,
            "is_valid": is_valid,
            "points": points,
            "reason": reason,
        })
        words_summary[cat] = {"word": word, "is_valid": is_valid, "points": points, "reason": reason}
        if is_valid:
            current_data[cat] = f"[green]{word}[/green] [dim](+10)[/dim]"
        else:
            current_data[cat] = f"[red]{word or '-'}[/red] [dim](0)[/dim]"
    current_total = f"[bold green]{total_points} pts[/bold green]"

    # Re-render finalized table with points
    final_table = ui.build_sheet_table(
        console, history_rounds, letter, current_data, current_total
    )
    console.print(final_table)

    # 6. Commit to DuckDB
    timestamp = datetime.now()
    db.save_round(
        conn=conn,
        round_id=round_id,
        letter=letter,
        model_name=model_name,
        timestamp=timestamp,
        total_points=total_points,
        words=round_words_data,
    )

    # 7. Summary panel with Judge Dictamen
    ui.display_round_summary(console, letter, total_points, round_words_data, round_id, judge_model=judge_model)
    return {
        "round_id": round_id,
        "letter": letter,
        "total_points": total_points,
        "words": words_summary,
    }


def main() -> None:
    """CLI Entrypoint for autonomous Basta game."""
    parser = argparse.ArgumentParser(
        description="🎮 Basta (Tutti Frutti / Stop) - Juego autónomo con LLM local y DuckDB",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--model",
        type=str,
        default=MODEL_NAME,
        help=f"Nombre del modelo jugador en Ollama (por defecto: {MODEL_NAME}).\nEjemplo: --model llama3.2 o --model mistral",
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        default=None,
        help="Nombre del modelo árbitro en Ollama (por defecto: el mismo que --model)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="Número de rondas consecutivas a jugar (por defecto: 1)",
    )
    parser.add_argument(
        "--letter",
        type=str,
        default=None,
        help="Forzar una letra específica para la ronda (ejemplo: --letter M)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Mostrar estadísticas globales almacenadas en DuckDB y salir",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.02,
        help="Retardo visual adicional entre categorías (en segundos)",
    )

    args = parser.parse_args()
    console = Console()

    # Initialize DuckDB connection
    try:
        conn = db.get_connection()
    except Exception as e:
        console.print(Panel(f"[bold red]Error al inicializar DuckDB:[/bold red] {e}", border_style="red"))
        sys.exit(1)

    # Handle --stats flag
    if args.stats:
        stats = db.fetch_stats(conn)
        ui.display_stats(console, stats)
        conn.close()
        return

    judge_model = args.judge_model or args.model

    # Check Ollama and models availability
    try:
        llm.check_ollama(args.model)
        if judge_model != args.model:
            llm.check_ollama(judge_model)
    except (ConnectionError, ValueError) as err:
        console.print(Panel(f"[bold red]Error de configuración de LLM:[/bold red]\n{err}", border_style="red"))
        conn.close()
        sys.exit(1)

    # Display welcome header with both models
    ui.display_header(console, args.model, judge_model)

    history_rounds: List[Dict[str, Any]] = []

    try:
        for r in range(1, args.rounds + 1):
            if args.rounds > 1:
                console.rule(f"[bold cyan]Ronda {r} de {args.rounds}[/bold cyan]")
            completed_info = play_round(
                console=console,
                conn=conn,
                model_name=args.model,
                judge_model=judge_model,
                history_rounds=history_rounds,
                forced_letter=args.letter,
                delay=args.delay,
            )
            history_rounds.append(completed_info)
            if r < args.rounds:
                time.sleep(1.0)

        # Final game overview if multiple rounds played
        if args.rounds > 1:
            total_game_pts = sum(rnd["total_points"] for rnd in history_rounds)
            console.print(
                Panel(
                    f"🏆 [bold yellow]JUEGO TERMINADO[/bold yellow] 🏆\n"
                    f"Rondas jugadas: {len(history_rounds)} | Puntos acumulados: [bold green]{total_game_pts} pts[/bold green]",
                    border_style="gold1",
                )
            )

    except KeyboardInterrupt:
        console.print("\n[yellow]Partida interrumpida por el usuario. ¡Hasta la próxima![/yellow]")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
