"""Regression tests for accent/typo-tolerant building search."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from routes.buildings import search_buildings, _norm


def _names(q):
    res = asyncio.run(search_buildings(q))
    return [b["name"] for b in res]


def test_norm_strips_accents_and_punctuation():
    assert _norm("Sacré-Cœur") == "sacre coeur"
    assert _norm("Château de Chambord") == "chateau de chambord"
    assert _norm("St. Basil's Cathedral") == "st basil s cathedral"


def test_accent_and_punctuation_tolerant():
    assert "Sacre-Coeur" in _names("sacre coeur")
    assert "Mont-Saint-Michel" in _names("mont saint michel")
    assert "Stephansdom" in _names("stephansdom")


def test_typo_tolerant():
    assert "Colosseum" in _names("colliseum")
    assert "Eiffel Tower" in _names("eifel")
    assert "Machu Picchu" in _names("machu pichu")
    assert "Burj Khalifa" in _names("burj kalifa")
    assert "Leaning Tower of Pisa" in _names("piza")


def test_alias_match():
    # alias "Namsan Tower" should find N Seoul Tower
    assert "N Seoul Tower" in _names("namsan")


def test_prefix_still_works():
    assert "Eiffel Tower" in _names("eif")
    assert {"Tokyo Tower", "Tokyo Skytree"}.issubset(set(_names("tokyo")))


def test_short_query_guarded():
    # 1-char query returns nothing
    assert _names("e") == []


def test_no_garbage_for_nonsense():
    assert _names("zzzzqwxv") == []
