"""Self-check test suite for Basta game logic and DuckDB persistence."""
from datetime import datetime
import duckdb
from db import init_schema, save_round, fetch_stats
from game import validate_word, score_entry, get_available_letters, CATEGORIES


def test_validation():
    # Accented letters
    assert validate_word("Árbol", "A") is True
    assert validate_word("árbol", "a") is True
    assert validate_word("Éxito", "E") is True
    assert validate_word("Índigo", "I") is True
    assert validate_word("Ópalo", "O") is True
    assert validate_word("Úrsula", "U") is True
    assert validate_word("Üva", "U") is True

    # Quotes and cleanups
    assert validate_word('"Manzana"', "M") is True
    assert validate_word("- Melón", "M") is True
    assert validate_word("*Morado*", "M") is True

    # Invalid / empty
    assert validate_word("Verde", "Y") is False
    assert validate_word("", "A") is False
    assert validate_word("   ", "B") is False

    # Scoring
    assert score_entry("Madrid", "M") == (True, 10)
    assert score_entry("Verde", "Y") == (False, 0)
    assert score_entry("", "M") == (False, 0)


def test_alphabet():
    letters = get_available_letters()
    for forbidden in ["Ñ", "W", "X"]:
        assert forbidden not in letters
    assert "A" in letters
    assert "Z" in letters
    assert len(CATEGORIES) == 7


def test_db():
    conn = duckdb.connect(":memory:")
    init_schema(conn)

    words = [
        {"category": "Nombre", "word": "Manuel", "is_valid": True, "points": 10},
        {"category": "Color", "word": "Verde", "is_valid": False, "points": 0},
    ]
    save_round(
        conn=conn,
        round_id="test-123",
        letter="M",
        model_name="llama3.2:1b",
        timestamp=datetime.now(),
        total_points=10,
        words=words,
    )

    stats = fetch_stats(conn)
    assert stats["rounds"] == 1
    assert stats["avg_points"] == 10.0
    assert stats["best_score"] == 10
    assert stats["valid_words"] == 1


if __name__ == "__main__":
    test_validation()
    test_alphabet()
    test_db()
    print("All Basta unit tests passed successfully!")
