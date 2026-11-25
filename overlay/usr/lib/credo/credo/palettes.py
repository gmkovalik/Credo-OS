"""Color palettes for the Credo OS theme variants.

"liturgical" is resolved at runtime to one of the LITURGICAL_* palettes from the
color of the day in the 1954 calendar (see liturgy.py).
"""

VARIANTS = {
    # key: (English name, Latin name)
    "liturgical": ("Liturgical (follows the season)", "Liturgicus (secundum tempus)"),
    "papal": ("Papal - gold and white", "Pontificius - aureus et albus"),
    "marian": ("Marian - blue and white", "Marianus - caeruleus et albus"),
    "sanctus": ("Sanctus - crimson and gold", "Sanctus - coccineus et aureus"),
    "monastic": ("Monastic - dark and plain", "Monasticus - obscurus"),
    "ivory": ("Ivory - light and neutral", "Eburneus - clarus"),
}

LOGOS = {
    "chirho": ("Chi-Rho", "Chi-Rho"),
    "cross": ("Latin cross", "Crux Latina"),
    "ihs": ("IHS monogram", "Monogramma IHS"),
    "keys": ("Keys of St. Peter", "Claves Sancti Petri"),
    "marian": ("Marian monogram", "Monogramma Marianum"),
    "sacredheart": ("Sacred Heart", "Sacratissimum Cor"),
}


def _p(dark, bg, bg_alt, view, fg, fg_dim, accent, accent_fg, logo, wall_a, wall_b, motto):
    return dict(dark=dark, bg=bg, bg_alt=bg_alt, view=view, fg=fg, fg_dim=fg_dim,
                accent=accent, accent_fg=accent_fg, logo=logo,
                wall_a=wall_a, wall_b=wall_b, motto=motto)


STATIC = {
    "papal": _p(False, "#f6f1e3", "#ebe2c9", "#fffdf7", "#2b2417", "#7a6d55",
                "#b8902f", "#ffffff", "#9c7a1c", "#fffaf0", "#e6d6a8", "Tu es Petrus"),
    "marian": _p(False, "#eef3fa", "#dde7f5", "#ffffff", "#1c2a44", "#5d6b85",
                 "#2f5fa7", "#ffffff", "#2f5fa7", "#f7faff", "#b9cdea", "Ave Maria, gratia plena"),
    "sanctus": _p(True, "#211517", "#2c1c1f", "#180f11", "#f1e6dc", "#b8a69a",
                  "#b3262e", "#ffffff", "#d4af37", "#5a1218", "#14090b", "Sanctus, Sanctus, Sanctus"),
    # Dark green glass, as in the Credo desktop design (design/credo-desktop-mockup.html).
    "monastic": _p(True, "#17211c", "#1f2b25", "#141d18", "#ebe8df", "#9eaaa2",
                   "#3f6f55", "#ffffff", "#c9a85a", "#2b2620", "#0d0c0a", "Ora et labora"),
    "ivory": _p(False, "#fbf8f1", "#f0ebdf", "#ffffff", "#2a2a2a", "#6b665c",
                "#7a5c2e", "#ffffff", "#7a5c2e", "#fffdf8", "#e3dccb", "Ad maiorem Dei gloriam"),
}

# Liturgical colors: base is a dark neutral; the accent is the vestment color.
LITURGICAL = {
    "green": _p(True, "#181a17", "#20241f", "#121411", "#e8ece4", "#9fa898",
                "#2e7d32", "#ffffff", "#d4af37", "#1f4a26", "#0b140c", ""),
    "violet": _p(True, "#1a1720", "#231e2b", "#131118", "#ebe5f0", "#a59cb0",
                 "#6a1b9a", "#ffffff", "#c9a85a", "#3b1752", "#0f0914", ""),
    "white": _p(False, "#f8f4e8", "#ede5cf", "#fffdf6", "#2b2417", "#7a6d55",
                "#b8902f", "#ffffff", "#c9a227", "#fffaf0", "#e8d9ab", ""),
    "red": _p(True, "#1f1515", "#2a1c1c", "#170f0f", "#f2e6e2", "#b6a29c",
              "#b71c1c", "#ffffff", "#d4af37", "#5c1010", "#140707", ""),
    "rose": _p(False, "#faf1f4", "#f0dfe6", "#fffafc", "#3a2430", "#80606f",
               "#c2577f", "#ffffff", "#c2577f", "#fff6f9", "#e9c0d0", ""),
    "black": _p(True, "#121212", "#1b1b1b", "#0c0c0c", "#e6e6e6", "#9a9a9a",
                "#5a5a5a", "#ffffff", "#b0b0b0", "#262626", "#050505", ""),
}

SEASON_MOTTO = {
    "advent": "Rorate caeli desuper",
    "christmas": "Verbum caro factum est",
    "epiphany": "Vidimus stellam eius",
    "septuagesima": "Circumdederunt me gemitus mortis",
    "lent": "Memento, homo, quia pulvis es",
    "passiontide": "Vexilla Regis prodeunt",
    "easter": "Surrexit Dominus vere, alleluia",
    "pentecost": "Veni, Creator Spiritus",
}


def resolve(variant, day=None):
    """Return (scheme_key, palette) for a variant. day is a liturgy.Day or None."""
    if variant == "liturgical":
        if day is None:
            from . import liturgy
            day = liturgy.today()
        pal = dict(LITURGICAL[day.color])
        pal["motto"] = SEASON_MOTTO.get(day.season, "Credo in unum Deum")
        return f"Liturgical{day.color.capitalize()}", pal
    return variant.capitalize(), dict(STATIC.get(variant, STATIC["monastic"]))
