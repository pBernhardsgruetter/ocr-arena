"""Seeded German / English business-text generator. Content is plausible, not literary:
what matters is exact ground truth with realistic token types (umlauts, amounts, IBANs,
dates, reference numbers)."""
import random

DE_NOUNS = [("der", "Vertrag", "Verträge"), ("die", "Rechnung", "Rechnungen"), ("der", "Kunde", "Kunden"),
            ("die", "Lieferung", "Lieferungen"), ("das", "Angebot", "Angebote"), ("die", "Zahlung", "Zahlungen"),
            ("der", "Auftrag", "Aufträge"), ("das", "Gutachten", "Gutachten"), ("die", "Versicherung", "Versicherungen"),
            ("der", "Schaden", "Schäden"), ("die", "Frist", "Fristen"), ("das", "Konto", "Konten"),
            ("die", "Gebühr", "Gebühren"), ("der", "Bericht", "Berichte"), ("das", "Protokoll", "Protokolle"),
            ("die", "Änderung", "Änderungen"), ("der", "Antrag", "Anträge"), ("die", "Übergabe", "Übergaben"),
            ("das", "Dokument", "Dokumente"), ("die", "Wartung", "Wartungen")]
DE_ADJ = ["vollständig", "fehlerhaft", "fällig", "gültig", "unvollständig", "bestätigt", "geprüft", "offen",
          "verspätet", "angemessen", "rückwirkend", "schriftlich"]
DE_VERB = ["prüft", "bestätigt", "verlangt", "erhält", "übernimmt", "beanstandet", "genehmigt", "übermittelt"]
DE_SUBJ = ["Die Gesellschaft", "Der Auftraggeber", "Die Bauleitung", "Der Versicherer", "Die Geschäftsführung",
           "Der Vermieter", "Die Abteilung Finanzen", "Herr Müller", "Frau Schärer", "Die Kantonale Verwaltung"]
DE_PLACES = ["Zürich", "Bern", "Luzern", "St. Gallen", "Winterthur", "Düsseldorf", "München", "Köln", "Basel", "Chur"]
DE_STREETS = ["Bahnhofstrasse", "Hauptstrasse", "Gartenweg", "Schulhausstrasse", "Mühlegasse", "Kirchgasse"]
DE_FIRST = ["Hans", "Anna", "Jürgen", "Brigitte", "Thomas", "Sabine", "Rüdiger", "Mara", "Lukas", "Ursula"]
DE_LAST = ["Müller", "Meier", "Schärer", "Weber", "Küng", "Bühler", "Hässig", "Gräub", "Fröhlich", "Zürcher"]
DE_ITEMS = ["Wartungsvertrag", "Ersatzteil", "Beratung", "Montage", "Schulung", "Lizenz", "Transport", "Reinigung",
            "Gutachten", "Büromaterial", "Stundenaufwand", "Versicherungsprämie"]

EN_SUBJ = ["The company", "The client", "The site manager", "The insurer", "The board", "The landlord",
           "The finance department", "Mr. Taylor", "Ms. Brown"]
EN_VERB = ["reviews", "confirms", "requires", "receives", "assumes", "disputes", "approves", "submits"]
EN_NOUN = ["contract", "invoice", "delivery", "offer", "payment", "order", "report", "claim", "deadline", "account",
           "fee", "protocol", "amendment", "application", "handover", "document"]
EN_ADJ = ["complete", "faulty", "overdue", "valid", "incomplete", "confirmed", "checked", "open", "late", "adequate"]
EN_ITEMS = ["Maintenance contract", "Spare part", "Consulting", "Installation", "Training", "Licence", "Freight",
            "Cleaning", "Expert opinion", "Office supplies", "Hours worked", "Insurance premium"]


def date(r):
    return f"{r.randint(1, 28):02d}.{r.randint(1, 12):02d}.{r.randint(2023, 2026)}"


def amount(r, lang="de"):
    v = r.randint(50, 98000) + r.randint(0, 99) / 100
    s = f"{v:,.2f}"  # 12,345.67
    if lang == "de":
        return s.replace(",", "'") + " CHF"  # Swiss: 12'345.67 CHF
    return s + " CHF"


def iban(r):
    d = "".join(str(r.randint(0, 9)) for _ in range(19))
    s = "CH" + f"{r.randint(10, 99)}" + d
    return " ".join(s[i:i + 4] for i in range(0, len(s), 4))


def refno(r):
    return f"RE-{r.randint(2023, 2026)}-{r.randint(0, 999999):06d}"


def sentence(r, lang):
    if lang == "en":
        k = r.randint(0, 3)
        if k == 0:
            return f"{r.choice(EN_SUBJ)} {r.choice(EN_VERB)} the {r.choice(EN_ADJ)} {r.choice(EN_NOUN)} by {date(r)}."
        if k == 1:
            return f"The amount of {amount(r, 'en')} must be transferred to account {iban(r)} no later than {date(r)}."
        if k == 2:
            return f"Under reference {refno(r)} the {r.choice(EN_NOUN)} was {r.choice(EN_ADJ)} on {date(r)}."
        return f"{r.choice(EN_SUBJ)} {r.choice(EN_VERB)} {r.randint(2, 40)} {r.choice(EN_NOUN)}s in {r.choice(DE_PLACES)}."
    k = r.randint(0, 4)
    art, noun, pl = r.choice(DE_NOUNS)
    A = art.capitalize()
    if k == 0:
        return f"{A} {noun} ist {r.choice(DE_ADJ)}; {r.choice(DE_SUBJ)} {r.choice(DE_VERB)} dies bis zum {date(r)}."
    if k == 1:
        return f"Der Betrag von {amount(r)} ist bis zum {date(r)} auf das Konto {iban(r)} zu überweisen."
    if k == 2:
        return f"Unter der Referenz {refno(r)} wurde {art} {noun} am {date(r)} {r.choice(DE_ADJ)} eingereicht."
    if k == 3:
        return f"{r.choice(DE_SUBJ)} {r.choice(DE_VERB)} {r.randint(2, 40)} {pl} in {r.choice(DE_PLACES)}."
    return f"Gemäss Ziffer {r.randint(1, 19)}.{r.randint(1, 9)} gilt: {A} {noun} bleibt {r.choice(DE_ADJ)}, auch nach Übergabe."


def paragraph(r, lang, n=None):
    return " ".join(sentence(r, lang) for _ in range(n or r.randint(3, 6)))


def heading(r, lang):
    if lang == "en":
        return r.choice(["Contract terms", "Payment schedule", "Claim summary", "Site report", "Delivery note"]) + f" {r.randint(1, 30)}"
    return r.choice(["Vertragsbedingungen", "Zahlungsplan", "Schadenmeldung", "Baustellenbericht", "Lieferschein"]) + f" {r.randint(1, 30)}"


def table(r, lang, nrows=None):
    n = nrows or r.randint(3, 7)
    head = ["Pos", "Bezeichnung", "Menge", "Betrag"] if lang == "de" else ["Pos", "Description", "Qty", "Amount"]
    items = DE_ITEMS if lang == "de" else EN_ITEMS
    rows = [head]
    for i in range(n):
        rows.append([str(i + 1), r.choice(items), str(r.randint(1, 120)), amount(r, lang).replace(" CHF", "")])
    return rows


def person(r):
    return f"{r.choice(DE_FIRST)} {r.choice(DE_LAST)}"


def address(r):
    return f"{r.choice(DE_STREETS)} {r.randint(1, 99)}, {r.randint(1000, 9999)} {r.choice(DE_PLACES)}"


def hand_value(r, kind):
    if kind == "name":
        return person(r)
    if kind == "date":
        return date(r)
    if kind == "amount":
        return amount(r).replace(" CHF", "")
    if kind == "note":
        return r.choice(["bitte zurückrufen", "Unterschrift fehlt", "dringend prüfen", "erledigt am " + date(r),
                         "Rückfrage bei " + person(r), "Betrag stimmt nicht"])
    return address(r)
