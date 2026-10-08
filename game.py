"""Game rules, categories, validation and scoring for Basta."""
import random
import re
import string
import time
import unicodedata
from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.live import Live

CATEGORIES: List[str] = [
    "Nombre",
    "Apellido",
    "País o Ciudad",
    "Animal",
    "Fruta o Flor",
    "Objeto",
    "Color",
]

DEFAULT_EXCLUDED_LETTERS: List[str] = ["Ñ", "W", "X"]


def get_available_letters(excluded: Optional[List[str]] = None) -> List[str]:
    """Return alphabet letters excluding difficult letters."""
    ex = set(excluded or DEFAULT_EXCLUDED_LETTERS)
    return [c for c in string.ascii_uppercase if c not in ex]


def normalize_char(ch: str) -> str:
    """Strip accents and convert single character to uppercase ASCII."""
    if not ch:
        return ""
    decomposed = unicodedata.normalize("NFD", ch)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return stripped.upper()


def validate_word(word: str, expected_letter: str) -> bool:
    """
    Check if word starts with expected letter (case/accent insensitive).
    Returns False if word is empty or missing.
    """
    if not word or not word.strip():
        return False
    # Remove leading quotes, hyphens, bullets or numbering
    cleaned = re.sub(r"^[\s\"'‘“`\*\-\d\.\)]+", "", word).strip()
    if not cleaned:
        return False
    return normalize_char(cleaned[0]) == normalize_char(expected_letter)


def score_entry(word: str, expected_letter: str) -> Tuple[bool, int]:
    """Calculate validity and points (10 if valid, 0 if invalid/empty)."""
    is_valid = validate_word(word, expected_letter)
    points = 10 if is_valid else 0
    return is_valid, points


def animate_letter_selection(console: Console, target_letter: Optional[str] = None) -> str:
    """
    Animate the alphabet counting cycle and shout ¡BASTA!
    """
    letters = get_available_letters()
    chosen = (target_letter.upper() if target_letter else random.choice(letters))

    console.print("\n[bold yellow]🎲 Recitando el abecedario mentalmente...[/bold yellow]")
    with Live(console=console, refresh_per_second=20, transient=True) as live:
        # Cycle through letters with variable rhythm
        total_ticks = random.randint(12, 18)
        for i in range(total_ticks):
            idx = i % len(letters)
            curr = letters[idx]
            live.update(f"[dim]Contando:[/dim] [bold cyan]{curr}[/bold cyan]...")
            time.sleep(0.05 + (i * 0.005))

    console.print(f"[bold red]¡BASTA![/bold red] ✋  Letra seleccionada: [bold yellow on blue]  {chosen}  [/bold yellow on blue]\n")
    return chosen


FINISHING_CHANT: str = (
    "¡Basta para mí, basta para todos, basta 1, basta 2, basta 3... ¡BASTA!"
)
