"""Terminal UI components using Rich for Basta game."""
import time
from typing import Any, Dict, List, Optional
from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from game import CATEGORIES, FINISHING_CHANT


def get_column_headers(width: int) -> List[str]:
    """Return compact or full category headers based on terminal width."""
    if width < 95:
        # Shorter headers to fit narrow terminals cleanly
        mapping = {
            "País o Ciudad": "País/Cd.",
            "Fruta o Flor": "Fruta/Flor",
        }
        return [mapping.get(c, c) for c in CATEGORIES]
    return CATEGORIES


def display_header(console: Console, model_name: str, judge_model: str) -> None:
    """Print the welcome banner and game configuration."""
    title_text = Text()
    title_text.append("🎮 BASTA / TUTTI FRUTTI AUTÓNOMO 🎮\n", style="bold yellow")
    title_text.append("El LLM juega de forma autónoma en español | Registrado en DuckDB\n", style="italic cyan")
    title_text.append(
        f"🤖 Jugador: {model_name}  |  ⚖️ Árbitro: {judge_model}  |  💾 BD: basta_history.duckdb",
        style="dim white",
    )
    console.print(Panel(Align.center(title_text), border_style="bright_blue"))


def build_sheet_table(
    console: Console,
    history_rounds: List[Dict[str, Any]],
    current_letter: Optional[str] = None,
    current_data: Optional[Dict[str, str]] = None,
    current_total: str = "---",
) -> Table:
    """
    Construct the Rich Table sheet displaying past rounds and the live active round.
    """
    headers = get_column_headers(console.width)
    table = Table(
        title="📝 HOJA DE JUEGO 'BASTA'",
        header_style="bold magenta on grey15",
        border_style="bright_blue",
        show_lines=True,
    )
    table.add_column("Letra", justify="center", style="bold cyan", width=6)
    for h in headers:
        table.add_column(h, justify="center")
    table.add_column("Total", justify="center", style="bold yellow", width=9)

    # Render previous finished rounds
    for past in history_rounds:
        row = [past["letter"]]
        for cat in CATEGORIES:
            w_info = past["words"].get(cat, {})
            word = w_info.get("word", "")
            pts = w_info.get("points", 0)
            if pts > 0:
                row.append(f"[green]{word}[/green] [dim](+{pts})[/dim]")
            else:
                row.append(f"[red]{word or '-'}[/red] [dim](0)[/dim]")
        row.append(f"[bold green]{past['total_points']} pts[/bold green]")
        table.add_row(*row)

    # Render active round if present
    if current_letter is not None:
        curr_row = [f"[bold yellow]{current_letter}[/bold yellow]"]
        curr_dict = current_data or {}
        for cat in CATEGORIES:
            cell_content = curr_dict.get(cat, "[dim]⏳ pendiente[/dim]")
            curr_row.append(cell_content)
        curr_row.append(current_total)
        table.add_row(*curr_row)

    return table
def display_chant(console: Console) -> None:
    """Dramatically chant the classic finishing phrase spaced by 1 second."""
    console.print()
    parts = [
        "¡Basta para mí!",
        "¡basta para todos!",
        "¡basta 1,",
        "basta 2,",
        "basta 3...",
        "¡BASTA! 🛑",
    ]
    chant_accum: List[str] = []
    with Live(console=console, refresh_per_second=10) as live:
        for i, part in enumerate(parts):
            chant_accum.append(part)
            text = Text(" ".join(chant_accum), style="bold red")
            live.update(Panel(Align.center(text), border_style="red"))
            if i < len(parts) - 1:
                time.sleep(1.0)
        time.sleep(0.5)


def display_round_summary(
    console: Console,
    letter: str,
    total_points: int,
    words: List[Dict[str, Any]],
    round_id: str,
    judge_model: Optional[str] = None,
) -> None:
    """Print the final validation scoreboard, LLM judge dictamen and DuckDB confirmation."""
    valid_count = sum(1 for w in words if w["is_valid"])
    judge_label = f" | ⚖️ Árbitro: {judge_model}" if judge_model else ""
    summary_text = (
        f"🏁 [bold green]Ronda completada[/bold green] (ID: {round_id[:8]}...) | Letra: [bold yellow]{letter}[/bold yellow]{judge_label}\n"
        f"Aciertos válidos: [bold cyan]{valid_count}/{len(words)}[/bold cyan] | "
        f"Puntaje total: [bold green]{total_points} pts[/bold green]"
    )
    console.print(Panel(summary_text, border_style="green"))

    # Dictamen table
    detail_table = Table(
        title="⚖️ DICTAMEN DEL ÁRBITRO LLM",
        border_style="dim cyan",
        show_lines=True,
    )
    detail_table.add_column("Categoría", style="bold white", width=14)
    detail_table.add_column("Palabra", style="cyan")
    detail_table.add_column("Dictamen", justify="center", width=11)
    detail_table.add_column("Puntos", justify="center", width=8)
    detail_table.add_column("Motivo del Árbitro", style="dim italic")

    for item in words:
        is_valid = item["is_valid"]
        pts = item["points"]
        reason = item.get("reason", "")
        status = "[bold green]✔ VÁLIDO[/bold green]" if is_valid else "[bold red]✘ INVÁLIDO[/bold red]"
        detail_table.add_row(
            item["category"],
            item["word"] or "-",
            status,
            f"+{pts}" if pts > 0 else "0",
            reason or ("Cumple con los requisitos" if is_valid else "No válido"),
        )

    console.print(detail_table)
    console.print("[dim green]✔ Datos guardados exitosamente en DuckDB (basta_history.duckdb)[/dim green]\n")


def display_stats(console: Console, stats: Dict[str, Any]) -> None:
    """Display historical stats from DuckDB."""
    table = Table(title="📊 HISTORIAL GENERAL DE BASTA", border_style="cyan")
    table.add_column("Métrica", style="bold cyan")
    table.add_column("Valor", style="bold yellow", justify="right")

    table.add_row("Rondas Jugadas", str(stats.get("rounds", 0)))
    table.add_row("Puntos Promedio por Ronda", f"{stats.get('avg_points', 0.0)} pts")
    table.add_row("Mejor Puntaje en una Ronda", f"{stats.get('best_score', 0)} pts")
    table.add_row("Palabras Válidas Totales", str(stats.get("valid_words", 0)))

    console.print(table)
