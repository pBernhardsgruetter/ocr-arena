from arena.metrics.accuracy import cer, wer, region_match
from arena.metrics.hallucination import analyze
from arena.metrics.structure import table_f1, reading_order
from arena.metrics.text import tokens


def test_cer_wer_basic():
    assert cer("Rechnung", "Rechnung") == 0
    assert abs(cer("abcd", "abcx") - 0.25) < 1e-9
    assert wer("a b c d", "a b c") == 0.25
    assert cer("", "x") == 1.0


def test_markdown_is_not_penalised():
    assert tokens("# Titel\n\n| a | b |\n|---|---|\n| 1 | 2 |") == ["Titel", "a", "b", "1", "2"]


def test_insertion_is_hallucination_deletion_is_omission():
    h = analyze("Der Betrag ist fällig", "Der Betrag ist fällig sofort laut Vertrag")
    assert h.hallucinated == 3 and h.omitted == 0
    h = analyze("Der Betrag ist fällig", "Der fällig")
    assert h.omitted == 2 and h.hallucinated == 0


def test_misread_vs_fabricated():
    h = analyze("Rechnungsnummer 4711", "Rechnungsnurnmer 4711")
    assert h.misread == 1 and h.hallucinated == 0
    h = analyze("Rechnungsnummer 4711", "Quittung 4711")
    assert h.hallucinated == 1


def test_digit_swap_flagged_as_near_miss():
    h = analyze("Total 1.234,56 CHF", "Total 1.243,56 CHF")
    assert h.numeric_wrong == 1 and h.numeric_near_miss == 1


def test_fabricated_page():
    assert analyze("", "Lorem ipsum dolor sit amet").fabricated_page == 1
    assert analyze("", "").fabricated_page == 0


def test_region_match():
    assert region_match("Müller Hans", "Name: Müller Hans, Zürich") == 1.0
    assert region_match("Müller Hans", "") == 0.0


def test_table_f1_and_order():
    truth = [["Pos", "Betrag"], ["1", "10,00"], ["2", "20,00"]]
    md = "| Pos | Betrag |\n|---|---|\n| 1 | 10,00 |\n| 2 | 20,00 |"
    assert table_f1(truth, md) == 1.0
    assert table_f1(truth, "Pos   Betrag\n1   10,00\n2   99,00") < 1.0
    assert table_f1(truth, "") == 0.0
    a = "Erster Absatz mit genug Text hier."
    b = "Zweiter Absatz mit anderem Inhalt."
    assert reading_order([a, b], a + "\n" + b) == 1.0
    assert reading_order([a, b], b + "\n" + a) == 0.0


def test_markdown_escapes_not_penalised():
    assert cer("Pos Bezeichnung", "Pos \\| Bezeichnung") == 0


def test_table_precision_ignores_prose():
    truth = [["Pos", "Betrag"], ["1", "10,00"]]
    md = "Ein langer Absatz davor.\n\n| Pos | Betrag |\n|---|---|\n| 1 | 10,00 |\n\nUnd danach."
    assert table_f1(truth, md) == 1.0
