"""English / Latin strings shared by Credo apps."""
from . import config

STRINGS = {
    "library": ("Catholic Library", "Bibliotheca Catholica"),
    "search": ("Search", "Quaere"),
    "search_ph": ("Search papal documents, saints, missal, catechism…", "Quaere in documentis, sanctis, missali…"),
    "all": ("All collections", "Omnes collectiones"),
    "any_lang": ("Any language", "Quaelibet lingua"),
    "results": ("results", "eventus"),
    "no_results": ("Nothing found.", "Nihil inventum."),
    "today": ("Today", "Hodie"),
    "season": ("Season", "Tempus"),
    "color": ("Color", "Color"),
    "mass_day": ("Mass of the Day", "Missa Diei"),
    "temporal": ("Proper of the Season", "Proprium de Tempore"),
    "sanctoral": ("Proper of the Saints", "Proprium Sanctorum"),
    "calendar": ("Calendar", "Calendarium"),
    "collections": ("Collections", "Collectiones"),
    "documents": ("documents", "documenta"),
    "empty": ("The library is empty. Open Credo Center → Library to download it, or run: credo-library fetch all",
              "Bibliotheca vacua est. Aperi Credo Center → Bibliotheca, vel exsequere: credo-library fetch all"),
    "other_lang": ("Read in the other language", "Lege in altera lingua"),
    "source": ("Source", "Fons"),
    "prev": ("Previous", "Prior"),
    "next": ("Next", "Sequens"),
    "missing_mass": ("This Mass is not in the library yet (download the Missal).",
                     "Haec Missa nondum in bibliotheca est."),
    "ordinary": ("Ordinary of the Mass", "Ordo Missae"),
    "latin": ("Latin", "Latine"),
    "rosary": ("Rosary", "Rosarium"),
    "prayers": ("Prayers", "Preces"),
    "examen": ("Examen", "Examen"),
    "english": ("English", "Anglice"),
}


def t(key, lang=None):
    lang = lang or config.language()
    en, la = STRINGS.get(key, (key, key))
    return la if lang == "la" else en
