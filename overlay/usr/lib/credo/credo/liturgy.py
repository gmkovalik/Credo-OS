"""Liturgical calendar of the Roman Rite as it stood in 1954 (Divino Afflatu rubrics,
before the 1955 simplification): seasons, liturgical color, the Sunday/feria title,
and the Divinum Officium file references for the temporal and sanctoral Mass.

This is a calendar of the *temporal cycle* plus the major fixed feasts. Full
precedence between temporal and sanctoral offices is not computed; the Mass of the
Day page shows both so the user can choose.

CLI:  credo-liturgy [--date YYYY-MM-DD] [--plain] [--lang la]
"""
import argparse
import datetime as dt
from dataclasses import dataclass, field

COLOR_HEX = {"green": "#2e7d32", "violet": "#6a1b9a", "white": "#efe6c8",
             "red": "#b71c1c", "rose": "#d87093", "black": "#1a1a1a"}

SEASONS = {
    "advent": ("Advent", "Tempus Adventus"),
    "christmas": ("Christmastide", "Tempus Nativitatis"),
    "epiphany": ("Time after Epiphany", "Tempus post Epiphaniam"),
    "septuagesima": ("Septuagesima", "Tempus Septuagesimae"),
    "lent": ("Lent", "Tempus Quadragesimae"),
    "passiontide": ("Passiontide", "Tempus Passionis"),
    "easter": ("Eastertide", "Tempus Paschale"),
    "pentecost": ("Time after Pentecost", "Tempus post Pentecosten"),
}

ORD_EN = ["", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth",
          "Ninth", "Tenth", "Eleventh", "Twelfth", "Thirteenth", "Fourteenth", "Fifteenth",
          "Sixteenth", "Seventeenth", "Eighteenth", "Nineteenth", "Twentieth",
          "Twenty-first", "Twenty-second", "Twenty-third", "Twenty-fourth"]
ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII",
         "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI", "XXII", "XXIII", "XXIV"]
DOW_EN = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
DOW_LA = ["Dominica", "Feria II", "Feria III", "Feria IV", "Feria V", "Feria VI", "Sabbato"]

# (offset from Easter) -> (English, Latin, color)
MOVABLE = {
    -63: ("Septuagesima Sunday", "Dominica in Septuagesima", "violet"),
    -56: ("Sexagesima Sunday", "Dominica in Sexagesima", "violet"),
    -49: ("Quinquagesima Sunday", "Dominica in Quinquagesima", "violet"),
    -46: ("Ash Wednesday", "Feria IV Cinerum", "violet"),
    -21: ("Laetare Sunday", "Dominica IV in Quadragesima (Laetare)", "rose"),
    -14: ("Passion Sunday", "Dominica de Passione", "violet"),
    -7: ("Palm Sunday", "Dominica in Palmis", "violet"),
    -3: ("Maundy Thursday", "Feria V in Cena Domini", "white"),
    -2: ("Good Friday", "Feria VI in Parasceve", "black"),
    -1: ("Holy Saturday", "Sabbato Sancto", "violet"),
    0: ("Easter Sunday", "Dominica Resurrectionis", "white"),
    7: ("Low Sunday", "Dominica in Albis", "white"),
    39: ("Ascension of Our Lord", "In Ascensione Domini", "white"),
    49: ("Pentecost Sunday", "Dominica Pentecostes", "red"),
    56: ("Most Holy Trinity", "Sanctissimae Trinitatis", "white"),
    60: ("Corpus Christi", "Corporis Christi", "white"),
    68: ("Most Sacred Heart of Jesus", "Sacratissimi Cordis Iesu", "white"),
}

# (month, day) -> (English, Latin, color)
FIXED = {
    (1, 1): ("Circumcision of Our Lord", "In Circumcisione Domini", "white"),
    (1, 6): ("Epiphany of Our Lord", "In Epiphania Domini", "white"),
    (2, 2): ("Purification of the Blessed Virgin Mary", "In Purificatione B. Mariae V.", "white"),
    (3, 19): ("St. Joseph, Spouse of the B.V.M.", "S. Ioseph Sponsi B.M.V.", "white"),
    (3, 25): ("Annunciation of the B.V.M.", "In Annuntiatione B.M.V.", "white"),
    (6, 24): ("Nativity of St. John the Baptist", "In Nativitate S. Ioannis Baptistae", "white"),
    (6, 29): ("Sts. Peter and Paul, Apostles", "Ss. Petri et Pauli Apostolorum", "red"),
    (8, 15): ("Assumption of the B.V.M.", "In Assumptione B.M.V.", "white"),
    (9, 29): ("Dedication of St. Michael the Archangel", "In Dedicatione S. Michaelis Archangeli", "white"),
    (11, 1): ("All Saints", "Omnium Sanctorum", "white"),
    (11, 2): ("All Souls", "In Commemoratione Omnium Fidelium Defunctorum", "black"),
    (12, 8): ("Immaculate Conception of the B.V.M.", "In Conceptione Immaculata B.M.V.", "white"),
    (12, 25): ("Nativity of Our Lord", "In Nativitate Domini", "white"),
    (12, 26): ("St. Stephen, Protomartyr", "S. Stephani Protomartyris", "red"),
    (12, 27): ("St. John, Apostle and Evangelist", "S. Ioannis Apostoli et Evangelistae", "white"),
    (12, 28): ("Holy Innocents", "Ss. Innocentium", "violet"),
}


@dataclass
class Day:
    date: dt.date
    season: str
    color: str
    title_en: str
    title_la: str
    temporal: str | None            # Divinum Officium ref, e.g. "Tempora/Adv1-0"
    sanctoral: str                  # e.g. "Sancti/12-08"
    feast_en: str = ""
    feast_la: str = ""
    feast_first: bool = False       # a major fixed feast outranks the temporal day
    notes: list = field(default_factory=list)

    @property
    def color_hex(self):
        return COLOR_HEX[self.color]

    def season_name(self, lang="en"):
        return SEASONS[self.season][1 if lang == "la" else 0]

    def title(self, lang="en"):
        return self.title_la if lang == "la" else self.title_en

    def feast(self, lang="en"):
        return self.feast_la if lang == "la" else self.feast_en


def easter(year):
    """Gregorian Easter (anonymous algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return dt.date(year, month, day + 1)


def first_advent(year):
    xmas = dt.date(year, 12, 25)
    back = (xmas.weekday() + 1) % 7 or 7     # last Sunday strictly before Christmas
    return xmas - dt.timedelta(days=back) - dt.timedelta(weeks=3)


def christ_the_king(year):
    """Last Sunday of October (instituted 1925)."""
    d = dt.date(year, 10, 31)
    return d - dt.timedelta(days=(d.weekday() + 1) % 7)


def _dow(d):
    return (d.weekday() + 1) % 7          # 0 = Sunday


def _sunday_on_or_before(d):
    return d - dt.timedelta(days=_dow(d))


def _names(kind_en, kind_la, week, dow):
    if dow == 0:
        return (f"{ORD_EN[week]} Sunday {kind_en}", f"Dominica {ROMAN[week]} {kind_la}")
    return (f"{DOW_EN[dow]} of the {ORD_EN[week]} Week {kind_en}",
            f"{DOW_LA[dow]} infra Hebdomadam {ROMAN[week]} {kind_la}")


def day_info(d: dt.date) -> Day:
    y = d.year
    E = easter(y)
    off = (d - E).days
    dow = _dow(d)
    sun = _sunday_on_or_before(d)
    adv = first_advent(y)
    sept = E - dt.timedelta(days=63)
    ash = E - dt.timedelta(days=46)
    lent1 = E - dt.timedelta(days=42)
    passion = E - dt.timedelta(days=14)
    trinity = E + dt.timedelta(days=56)
    temporal = None
    color = "green"

    if adv <= d <= dt.date(y, 12, 24):
        season, color = "advent", "violet"
        w = (sun - adv).days // 7 + 1
        en, la = _names("of Advent", "Adventus", w, dow)
        temporal = f"Tempora/Adv{w}-{dow}"
        if w == 3 and dow == 0:
            color = "rose"
            en, la = "Gaudete Sunday (Third Sunday of Advent)", "Dominica III Adventus (Gaudete)"
    elif d >= dt.date(y, 12, 25) or d <= dt.date(y, 1, 13):
        season, color = "christmas", "white"
        if d.month == 12:
            en, la = "Christmastide", "Tempus Nativitatis"
            if dow == 0 and d.day >= 26:
                en, la = "Sunday within the Octave of Christmas", "Dominica infra Octavam Nativitatis"
                temporal = "Tempora/Nat1-0"
        else:
            en, la = "Christmastide", "Tempus Nativitatis"
            if 2 <= d.day <= 5 and dow == 0:
                en, la = "Most Holy Name of Jesus", "Ss. Nominis Iesu"
                temporal = "Tempora/Nat2-0"
            elif 7 <= d.day <= 13:
                en, la = "Within the Octave of the Epiphany", "Infra Octavam Epiphaniae"
                if dow == 0:
                    en, la = "Holy Family (Sunday within the Octave of the Epiphany)", "S. Familiae Iesu, Mariae, Ioseph"
                    temporal = "Tempora/Epi1-0"
    elif d < sept:
        season = "epiphany"
        jan6 = dt.date(y, 1, 6)
        epi1 = jan6 + dt.timedelta(days=(7 - _dow(jan6)) or 7)
        w = max(1, (sun - epi1).days // 7 + 1)
        en, la = _names("after Epiphany", "post Epiphaniam", w, dow)
        temporal = f"Tempora/Epi{w}-{dow}"
    elif d < ash:
        season, color = "septuagesima", "violet"
        w = (sun - sept).days // 7 + 1
        en, la = (f"{DOW_EN[dow]} after {['', 'Septuagesima', 'Sexagesima', 'Quinquagesima'][w]}",
                  f"{DOW_LA[dow]} post Dominicam in {['', 'Septuagesima', 'Sexagesima', 'Quinquagesima'][w]}")
        temporal = f"Tempora/Quadp{w}-{dow}"
    elif d < passion:
        season, color = "lent", "violet"
        if d < lent1:
            en, la = f"{DOW_EN[dow]} after Ash Wednesday", f"{DOW_LA[dow]} post Cineres"
            temporal = f"Tempora/Quadp3-{dow}"
        else:
            w = (sun - lent1).days // 7 + 1
            en, la = _names("of Lent", "in Quadragesima", w, dow)
            temporal = f"Tempora/Quad{w}-{dow}"
    elif d < E:
        season, color = "passiontide", "violet"
        w = 5 if d < E - dt.timedelta(days=7) else 6
        en, la = (_names("of Passiontide", "de Passione", 1, dow) if w == 5
                  else (f"{DOW_EN[dow]} of Holy Week", f"{DOW_LA[dow]} Maioris Hebdomadae"))
        temporal = f"Tempora/Quad{w}-{dow}"
    elif off <= 55:
        season, color = "easter", ("red" if off >= 49 else "white")
        w = (sun - E).days // 7
        if w == 0:
            en, la = f"{DOW_EN[dow]} in the Octave of Easter", f"{DOW_LA[dow]} infra Octavam Paschae"
        elif w == 7:
            en, la = f"{DOW_EN[dow]} in the Octave of Pentecost", f"{DOW_LA[dow]} infra Octavam Pentecostes"
        else:
            en, la = _names("after Easter", "post Pascha", w, dow)
        temporal = f"Tempora/Pasc{w}-{dow}"
    else:
        season = "pentecost"
        w = (sun - trinity).days // 7 + 1
        if (adv - sun).days == 7:
            w = 24                      # last Sunday after Pentecost is always the 24th
        w = min(w, 24)
        en, la = _names("after Pentecost", "post Pentecosten", w, dow)
        temporal = f"Tempora/Pent{w:02d}-{dow}"

    if off in MOVABLE:
        en, la, color = MOVABLE[off]

    day = Day(d, season, color, en, la, temporal, f"Sancti/{d.month:02d}-{d.day:02d}")

    feast = FIXED.get((d.month, d.day))
    if d == christ_the_king(y) and y >= 1925:
        feast = ("Christ the King", "D.N. Iesu Christi Regis", "white")
    if feast:
        day.feast_en, day.feast_la = feast[0], feast[1]
        # Major fixed feasts take the color unless it is a privileged temporal day.
        privileged = season in ("passiontide",) or off in (0, 49) or (season == "easter" and off < 8)
        if not privileged:
            day.color = feast[2]
            day.feast_first = True
    if dow in (3, 5, 6) and _is_ember(d, E, adv):
        day.notes.append("Ember Day")
    if dow == 5 and season not in ("christmas", "easter"):
        day.notes.append("Friday abstinence")
    return day


def _is_ember(d, E, adv):
    """Ember Wednesday, Friday and Saturday of the four seasons."""
    wednesdays = [
        E - dt.timedelta(days=39),          # after the 1st Sunday of Lent
        E + dt.timedelta(days=52),          # after Pentecost
        adv + dt.timedelta(days=17),        # after the 3rd Sunday of Advent
    ]
    sept14 = dt.date(d.year, 9, 14)         # after the Exaltation of the Holy Cross
    wednesdays.append(sept14 + dt.timedelta(days=(3 - _dow(sept14)) % 7 or 7))
    return any((d - w).days in (0, 2, 3) for w in wednesdays)


def today():
    return day_info(dt.date.today())


def year_overview(year):
    """List of (date, Day) for every Sunday and major feast of the year."""
    out = []
    d = dt.date(year, 1, 1)
    while d.year == year:
        info = day_info(d)
        if _dow(d) == 0 or info.feast_en or (d - easter(year)).days in MOVABLE:
            out.append(info)
        d += dt.timedelta(days=1)
    return out


def sanctorale(d, lang="en"):
    """The feast in the Proper of the Saints for this date (shipped list, no download needed)."""
    import json
    from . import config
    try:
        table = json.loads((config.SHARE / "sanctorale.json").read_text(encoding="utf-8"))
        return table.get(f"{d.month:02d}-{d.day:02d}", {}).get(lang, "")
    except (OSError, ValueError):
        return ""


def print_json(d, lang):
    """One line of JSON for the Today / Rosary desktop widgets."""
    import json
    from . import devotions
    info = day_info(d)
    saint = ""
    try:                                     # the saint's Mass title, if the Missal is downloaded
        from . import db
        r = db.connect().execute("SELECT title FROM docs WHERE collection='missal' AND ref=? AND lang=?",
                                 (info.sanctoral, lang)).fetchone()
        saint = r["title"] if r else ""
    except Exception:
        pass
    if not saint:
        saint = sanctorale(d, lang)
    nxt, day = None, d
    for _ in range(60):
        day += dt.timedelta(days=1)
        i = day_info(day)
        if i.feast_en or (day - easter(day.year)).days in MOVABLE or (_dow(day) == 0 and i.season != info.season):
            nxt = {"date": day.isoformat(), "weekday": day.strftime("%a"), "title": i.feast(lang) or i.title(lang)}
            break
    key = devotions.mysteries_for(d)
    m = devotions.MYSTERIES[key]
    print(json.dumps({
        "date": d.isoformat(), "title": info.feast(lang) or info.title(lang), "temporal": info.title(lang),
        "saint": saint, "season": info.season_name(lang), "color": info.color, "color_hex": info.color_hex,
        "notes": info.notes, "rosary_key": key, "rosary": m[1] if lang == "la" else m[0],
        "next": nxt}, ensure_ascii=False))


def angelus_reminder(lang):
    """Show a notification; clicking "Pray" opens the prayer in the Credo app."""
    import shutil
    import subprocess
    from . import config, devotions
    key = devotions.marian_antiphon_key()
    en_t, la_t, en, la, _ = devotions.PRAYERS[key]
    title = la_t if lang == "la" else en_t
    first = (la if lang == "la" else en).split("|")[0]
    if not shutil.which("notify-send"):
        print(f"{title}\n{first}")
        return
    icon = str(config.SHARE / "logos" / "chirho.svg")
    label = "Ora" if lang == "la" else "Pray"
    try:
        r = subprocess.run(["notify-send", "-a", "Credo", "-i", icon, "--expire-time=600000",
                            f"--action=pray={label}", "--wait", title, first],
                           capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        return
    if r.stdout.strip() == "pray" and shutil.which("credo-library"):
        subprocess.Popen(["credo-library", "open", f"/prayers#{key}"], start_new_session=True)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="credo-liturgy", description="1954 Roman liturgical calendar")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--lang", choices=["en", "la"])
    ap.add_argument("--plain", action="store_true", help="machine-readable: season, color hex, title")
    ap.add_argument("--json", action="store_true", help="today for desktop widgets, as JSON")
    ap.add_argument("--angelus", action="store_true",
                    help="desktop reminder to pray the Angelus (Regina Caeli in Eastertide)")
    a = ap.parse_args(argv)
    from . import config
    lang = a.lang or config.language()
    if a.angelus:
        return angelus_reminder(lang)
    if a.json:
        return print_json(dt.date.fromisoformat(a.date) if a.date else dt.date.today(), lang)
    d = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    info = day_info(d)
    title = info.feast(lang) or info.title(lang)
    if a.plain:
        print(info.season_name(lang))
        print(info.color_hex)
        print(title)
        print(info.color)
        return
    print(f"{d.isoformat()}  {title}")
    if info.feast_en:
        print(f"  Temporal: {info.title(lang)}")
    print(f"  Season:   {info.season_name(lang)}")
    print(f"  Color:    {info.color}")
    if info.notes:
        print(f"  Notes:    {', '.join(info.notes)}")
    print(f"  Mass:     {info.temporal or '-'} | {info.sanctoral}")


if __name__ == "__main__":
    main()
