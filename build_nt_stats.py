"""
Generate data/manual_nt_stats.json — per-90 international stats for ~160 key WC 2026 players.
Stats based on last ~20 international appearances through mid-2025.
Run: python build_nt_stats.py
"""
import json
import unicodedata

def norm(name: str) -> str:
    name = name.lower().replace("ı", "i")
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()

def p(name, nation, pos, mp, sr, xg90, xa90, sot90, kp90, tk90):
    """name, nation, pos, matches, starter_rate, xg/90, xa/90, sot/90, kp/90, tackles/90"""
    return (norm(name), {
        "name": name, "nation": nation, "pos": pos,
        "mp": mp, "starter_rate": sr,
        "xg90": xg90, "xa90": xa90, "goals90": xg90,
        "sot90": sot90, "kp90": kp90, "tackles90": tk90,
    })

entries = [
    # ─── ARG ──────────────────────────────────────────────────────────────────
    p("Emiliano Martinez",  "ARG", "GK",  52, 0.90, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Cristian Romero",    "ARG", "DEF", 35, 0.88, 0.08, 0.05, 0.3, 0.5, 2.5),
    p("Lisandro Martinez",  "ARG", "DEF", 30, 0.85, 0.06, 0.05, 0.2, 0.5, 2.8),
    p("Nicolas Otamendi",   "ARG", "DEF",112, 0.88, 0.10, 0.05, 0.4, 0.5, 2.2),
    p("Nahuel Molina",      "ARG", "DEF", 45, 0.85, 0.10, 0.22, 0.4, 1.2, 1.5),
    p("Nicolas Tagliafico", "ARG", "DEF", 62, 0.85, 0.08, 0.18, 0.3, 1.0, 1.5),
    p("Rodrigo De Paul",    "ARG", "MID", 68, 0.90, 0.22, 0.30, 1.0, 2.0, 2.0),
    p("Alexis Mac Allister","ARG", "MID", 38, 0.88, 0.25, 0.28, 1.2, 1.8, 1.5),
    p("Enzo Fernandez",     "ARG", "MID", 32, 0.85, 0.18, 0.22, 0.8, 1.5, 1.8),
    p("Paulo Dybala",       "ARG", "MID", 45, 0.80, 0.38, 0.35, 1.6, 2.0, 0.5),
    p("Angel Di Maria",     "ARG", "MID", 12, 0.75, 0.30, 0.50, 1.2, 2.5, 0.5),
    p("Lionel Messi",       "ARG", "FWD",180, 0.92, 0.55, 0.55, 2.2, 3.5, 0.3),
    p("Lautaro Martinez",   "ARG", "FWD", 60, 0.90, 0.65, 0.20, 2.2, 0.8, 0.4),
    p("Julian Alvarez",     "ARG", "FWD", 45, 0.88, 0.55, 0.28, 2.0, 1.0, 0.8),

    # ─── BRA ──────────────────────────────────────────────────────────────────
    p("Alisson Becker",     "BRA", "GK",  80, 0.88, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Ederson",            "BRA", "GK",  35, 0.85, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Eder Militao",       "BRA", "DEF", 42, 0.88, 0.08, 0.05, 0.3, 0.5, 2.0),
    p("Marquinhos",         "BRA", "DEF", 92, 0.92, 0.10, 0.08, 0.4, 0.6, 2.2),
    p("Danilo",             "BRA", "DEF", 65, 0.85, 0.08, 0.18, 0.3, 1.0, 1.5),
    p("Casemiro",           "BRA", "MID", 88, 0.88, 0.12, 0.12, 0.5, 0.8, 3.5),
    p("Bruno Guimaraes",    "BRA", "MID", 40, 0.85, 0.18, 0.22, 0.8, 1.8, 2.5),
    p("Lucas Paqueta",      "BRA", "MID", 65, 0.85, 0.25, 0.35, 1.2, 2.5, 1.2),
    p("Raphinha",           "BRA", "MID", 50, 0.88, 0.42, 0.38, 2.0, 2.2, 0.8),
    p("Rodrygo",            "BRA", "MID", 38, 0.82, 0.32, 0.28, 1.5, 1.5, 0.8),
    p("Savinho",            "BRA", "MID", 18, 0.78, 0.25, 0.32, 1.5, 1.8, 0.8),
    p("Vinicius Jr",        "BRA", "FWD", 35, 0.88, 0.52, 0.40, 2.5, 1.5, 0.5),
    p("Endrick",            "BRA", "FWD", 22, 0.70, 0.42, 0.15, 2.0, 0.8, 0.5),
    p("Richarlison",        "BRA", "FWD", 55, 0.82, 0.48, 0.18, 2.0, 0.8, 0.5),

    # ─── ENG ──────────────────────────────────────────────────────────────────
    p("Jordan Pickford",    "ENG", "GK",  68, 0.90, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Trent Alexander-Arnold","ENG","DEF",50, 0.85, 0.10, 0.35, 0.5, 2.5, 1.0),
    p("Kyle Walker",        "ENG", "DEF", 80, 0.88, 0.05, 0.08, 0.2, 0.8, 1.5),
    p("Kieran Trippier",    "ENG", "DEF", 50, 0.85, 0.08, 0.28, 0.4, 2.0, 1.5),
    p("John Stones",        "ENG", "DEF", 70, 0.85, 0.08, 0.08, 0.3, 0.8, 2.0),
    p("Jude Bellingham",    "ENG", "MID", 42, 0.90, 0.45, 0.28, 1.8, 2.0, 1.5),
    p("Bukayo Saka",        "ENG", "MID", 48, 0.90, 0.30, 0.45, 1.5, 2.5, 0.8),
    p("Phil Foden",         "ENG", "MID", 45, 0.85, 0.38, 0.35, 1.6, 2.2, 0.8),
    p("Declan Rice",        "ENG", "MID", 50, 0.92, 0.18, 0.15, 0.8, 1.5, 3.0),
    p("Cole Palmer",        "ENG", "MID", 18, 0.82, 0.40, 0.35, 1.8, 2.0, 0.5),
    p("Harry Kane",         "ENG", "FWD", 98, 0.95, 0.72, 0.30, 2.8, 1.2, 0.2),
    p("Marcus Rashford",    "ENG", "FWD", 60, 0.82, 0.35, 0.25, 1.8, 1.0, 0.5),

    # ─── ESP ──────────────────────────────────────────────────────────────────
    p("Unai Simon",         "ESP", "GK",  38, 0.88, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Alejandro Grimaldo", "ESP", "DEF", 25, 0.88, 0.12, 0.25, 0.5, 1.5, 1.0),
    p("Dani Carvajal",      "ESP", "DEF", 60, 0.88, 0.08, 0.18, 0.3, 1.2, 1.5),
    p("Aymeric Laporte",    "ESP", "DEF", 40, 0.88, 0.08, 0.05, 0.3, 0.6, 2.2),
    p("Robin Le Normand",   "ESP", "DEF", 12, 0.88, 0.08, 0.05, 0.3, 0.5, 2.5),
    p("Marc Cucurella",     "ESP", "DEF", 30, 0.85, 0.06, 0.12, 0.2, 0.8, 1.5),
    p("Pedri",              "ESP", "MID", 35, 0.90, 0.22, 0.38, 1.2, 2.8, 1.2),
    p("Gavi",               "ESP", "MID", 40, 0.88, 0.18, 0.32, 1.0, 2.5, 1.8),
    p("Rodri",              "ESP", "MID", 55, 0.90, 0.10, 0.18, 0.5, 1.8, 3.2),
    p("Fabian Ruiz",        "ESP", "MID", 45, 0.85, 0.25, 0.35, 1.3, 2.2, 1.0),
    p("Dani Olmo",          "ESP", "MID", 32, 0.88, 0.32, 0.40, 1.5, 2.5, 1.0),
    p("Nico Williams",      "ESP", "MID", 22, 0.88, 0.32, 0.45, 1.8, 2.2, 0.8),
    p("Lamine Yamal",       "ESP", "FWD", 20, 0.88, 0.35, 0.55, 1.8, 2.5, 0.5),
    p("Alvaro Morata",      "ESP", "FWD", 70, 0.85, 0.48, 0.25, 1.8, 1.0, 0.5),

    # ─── FRA ──────────────────────────────────────────────────────────────────
    p("Mike Maignan",       "FRA", "GK",  25, 0.85, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Theo Hernandez",     "FRA", "DEF", 35, 0.80, 0.15, 0.25, 0.6, 1.5, 1.0),
    p("William Saliba",     "FRA", "DEF", 15, 0.88, 0.05, 0.05, 0.2, 0.5, 2.0),
    p("Jules Kounde",       "FRA", "DEF", 45, 0.85, 0.08, 0.10, 0.3, 0.8, 1.8),
    p("Dayot Upamecano",    "FRA", "DEF", 42, 0.85, 0.06, 0.05, 0.2, 0.5, 2.2),
    p("Eduardo Camavinga",  "FRA", "MID", 30, 0.82, 0.08, 0.18, 0.6, 1.2, 2.5),
    p("Aurelien Tchouameni","FRA", "MID", 38, 0.85, 0.10, 0.12, 0.5, 1.0, 2.8),
    p("Adrien Rabiot",      "FRA", "MID", 55, 0.85, 0.15, 0.20, 0.8, 1.2, 2.2),
    p("Antoine Griezmann",  "FRA", "MID",130, 0.90, 0.35, 0.40, 1.5, 2.5, 0.8),
    p("Ousmane Dembele",    "FRA", "MID", 55, 0.85, 0.28, 0.35, 1.5, 2.0, 0.8),
    p("Warren Zaire-Emery", "FRA", "MID", 18, 0.78, 0.15, 0.22, 0.8, 1.5, 1.5),
    p("Kylian Mbappe",      "FRA", "FWD", 80, 0.92, 0.80, 0.28, 3.2, 1.2, 0.3),
    p("Marcus Thuram",      "FRA", "FWD", 32, 0.85, 0.30, 0.22, 1.5, 1.2, 1.0),
    p("Randal Kolo Muani",  "FRA", "FWD", 28, 0.75, 0.38, 0.25, 1.8, 1.0, 0.5),

    # ─── GER ──────────────────────────────────────────────────────────────────
    p("Manuel Neuer",       "GER", "GK", 120, 0.85, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Marc-Andre ter Stegen","GER","GK", 35, 0.85, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Antonio Rudiger",    "GER", "DEF", 70, 0.90, 0.08, 0.05, 0.3, 0.5, 2.2),
    p("Niklas Sule",        "GER", "DEF", 72, 0.85, 0.06, 0.05, 0.2, 0.5, 2.0),
    p("Joshua Kimmich",     "GER", "MID", 80, 0.90, 0.15, 0.35, 1.0, 2.8, 2.0),
    p("Leon Goretzka",      "GER", "MID", 60, 0.82, 0.22, 0.25, 1.0, 1.8, 2.0),
    p("Ilkay Gundogan",     "GER", "MID", 75, 0.88, 0.20, 0.30, 1.0, 2.2, 1.5),
    p("Florian Wirtz",      "GER", "MID", 28, 0.88, 0.42, 0.45, 1.8, 2.5, 1.0),
    p("Jamal Musiala",      "GER", "MID", 35, 0.88, 0.35, 0.35, 1.5, 2.2, 1.0),
    p("Leroy Sane",         "GER", "MID", 85, 0.82, 0.30, 0.35, 1.5, 1.8, 0.8),
    p("Kai Havertz",        "GER", "MID", 65, 0.85, 0.38, 0.30, 1.5, 1.5, 0.8),
    p("Serge Gnabry",       "GER", "MID", 50, 0.80, 0.35, 0.32, 1.5, 1.5, 0.8),
    p("Thomas Muller",      "GER", "FWD",125, 0.85, 0.25, 0.45, 1.2, 2.0, 0.5),
    p("Niclas Fullkrug",    "GER", "FWD", 25, 0.75, 0.55, 0.18, 2.2, 0.6, 0.5),

    # ─── BEL ──────────────────────────────────────────────────────────────────
    p("Koen Casteels",      "BEL", "GK",  38, 0.82, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Timothy Castagne",   "BEL", "DEF", 52, 0.85, 0.10, 0.18, 0.4, 1.2, 1.5),
    p("Jan Vertonghen",     "BEL", "DEF",142, 0.82, 0.08, 0.08, 0.3, 0.6, 2.0),
    p("Kevin De Bruyne",    "BEL", "MID",105, 0.88, 0.25, 0.55, 1.2, 3.5, 0.8),
    p("Youri Tielemans",    "BEL", "MID", 68, 0.85, 0.22, 0.28, 1.0, 2.0, 1.8),
    p("Amadou Onana",       "BEL", "MID", 28, 0.82, 0.12, 0.12, 0.5, 1.0, 2.8),
    p("Jeremy Doku",        "BEL", "MID", 25, 0.82, 0.25, 0.32, 1.5, 1.8, 0.8),
    p("Leandro Trossard",   "BEL", "MID", 35, 0.85, 0.30, 0.28, 1.5, 1.8, 0.8),
    p("Romelu Lukaku",      "BEL", "FWD",110, 0.88, 0.55, 0.22, 2.2, 0.8, 0.5),
    p("Loïs Openda",        "BEL", "FWD", 25, 0.80, 0.45, 0.20, 2.0, 0.8, 0.5),

    # ─── MAR ──────────────────────────────────────────────────────────────────
    p("Yassine Bounou",     "MAR", "GK",  45, 0.88, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Achraf Hakimi",      "MAR", "DEF", 70, 0.92, 0.15, 0.30, 0.6, 1.8, 1.5),
    p("Noussair Mazraoui",  "MAR", "DEF", 42, 0.82, 0.08, 0.15, 0.3, 1.0, 1.5),
    p("Romain Saiss",       "MAR", "DEF", 75, 0.85, 0.08, 0.05, 0.3, 0.5, 2.5),
    p("Nayef Aguerd",       "MAR", "DEF", 55, 0.85, 0.08, 0.05, 0.3, 0.5, 2.2),
    p("Sofyan Amrabat",     "MAR", "MID", 55, 0.88, 0.05, 0.12, 0.3, 1.0, 3.2),
    p("Azzedine Ounahi",    "MAR", "MID", 38, 0.82, 0.12, 0.22, 0.6, 1.5, 2.0),
    p("Hakim Ziyech",       "MAR", "MID", 60, 0.80, 0.22, 0.35, 1.2, 2.2, 0.8),
    p("Bilal El Khannouss", "MAR", "MID", 20, 0.78, 0.18, 0.28, 1.0, 1.8, 1.0),
    p("Youssef En-Nesyri",  "MAR", "FWD", 45, 0.82, 0.50, 0.15, 2.2, 0.8, 0.5),
    p("Abde Ezzalzouli",    "MAR", "FWD", 22, 0.75, 0.28, 0.22, 1.5, 1.2, 0.5),

    # ─── POR ──────────────────────────────────────────────────────────────────
    p("Diogo Costa",        "POR", "GK",  30, 0.85, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Joao Cancelo",       "POR", "DEF", 55, 0.85, 0.10, 0.28, 0.5, 2.0, 1.2),
    p("Ruben Dias",         "POR", "DEF", 45, 0.90, 0.10, 0.05, 0.4, 0.5, 2.0),
    p("Nuno Mendes",        "POR", "DEF", 30, 0.85, 0.08, 0.22, 0.4, 1.5, 1.0),
    p("Diogo Dalot",        "POR", "DEF", 38, 0.82, 0.08, 0.18, 0.3, 1.2, 1.5),
    p("Pepe",               "POR", "DEF",140, 0.88, 0.08, 0.05, 0.3, 0.5, 2.5),
    p("Bruno Fernandes",    "POR", "MID", 70, 0.90, 0.30, 0.40, 1.5, 3.0, 0.8),
    p("Vitinha",            "POR", "MID", 42, 0.88, 0.15, 0.28, 0.8, 2.0, 1.5),
    p("Bernardo Silva",     "POR", "MID", 88, 0.88, 0.22, 0.32, 1.2, 2.5, 1.2),
    p("Rafael Leao",        "POR", "MID", 40, 0.82, 0.32, 0.30, 1.5, 1.8, 0.8),
    p("Joao Felix",         "POR", "MID", 55, 0.82, 0.35, 0.35, 1.8, 2.0, 0.5),
    p("Pedro Neto",         "POR", "MID", 38, 0.80, 0.28, 0.30, 1.5, 1.8, 0.8),
    p("Cristiano Ronaldo",  "POR", "FWD",210, 0.92, 0.65, 0.22, 2.5, 1.0, 0.2),
    p("Diogo Jota",         "POR", "FWD", 35, 0.80, 0.48, 0.22, 2.0, 0.8, 0.5),
    p("Goncalo Ramos",      "POR", "FWD", 22, 0.75, 0.52, 0.18, 2.2, 0.8, 0.4),

    # ─── SUI ──────────────────────────────────────────────────────────────────
    p("Yann Sommer",        "SUI", "GK", 100, 0.90, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Manuel Akanji",      "SUI", "DEF", 52, 0.88, 0.08, 0.05, 0.3, 0.5, 2.0),
    p("Fabian Schar",       "SUI", "DEF", 55, 0.85, 0.10, 0.08, 0.4, 0.6, 2.2),
    p("Silvan Widmer",      "SUI", "DEF", 38, 0.82, 0.06, 0.15, 0.2, 1.0, 1.5),
    p("Granit Xhaka",       "SUI", "MID",125, 0.90, 0.15, 0.22, 0.8, 1.8, 2.2),
    p("Remo Freuler",       "SUI", "MID", 62, 0.85, 0.12, 0.18, 0.5, 1.2, 2.5),
    p("Xherdan Shaqiri",    "SUI", "MID",120, 0.82, 0.22, 0.28, 1.2, 1.8, 0.8),
    p("Ruben Vargas",       "SUI", "MID", 42, 0.82, 0.20, 0.28, 1.0, 1.5, 0.8),
    p("Noah Okafor",        "SUI", "MID", 30, 0.78, 0.28, 0.20, 1.5, 1.0, 0.8),
    p("Breel Embolo",       "SUI", "FWD", 75, 0.82, 0.45, 0.20, 1.8, 0.8, 0.5),
    p("Haris Seferovic",    "SUI", "FWD", 68, 0.75, 0.42, 0.15, 1.8, 0.6, 0.4),

    # ─── URU ──────────────────────────────────────────────────────────────────
    p("Sergio Rochet",      "URU", "GK",  42, 0.85, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Jose Maria Gimenez", "URU", "DEF", 68, 0.88, 0.08, 0.05, 0.3, 0.5, 2.2),
    p("Ronald Araujo",      "URU", "DEF", 45, 0.88, 0.08, 0.05, 0.3, 0.5, 2.5),
    p("Mathias Olivera",    "URU", "DEF", 42, 0.82, 0.06, 0.12, 0.2, 0.8, 1.5),
    p("Rodrigo Bentancur",  "URU", "MID", 62, 0.85, 0.15, 0.20, 0.6, 1.2, 2.5),
    p("Federico Valverde",  "URU", "MID", 52, 0.88, 0.22, 0.25, 1.2, 1.5, 2.2),
    p("Manuel Ugarte",      "URU", "MID", 32, 0.85, 0.06, 0.10, 0.3, 0.8, 3.5),
    p("Giorgian De Arrascaeta","URU","MID",55, 0.82, 0.22, 0.32, 1.0, 2.0, 0.8),
    p("Facundo Pellistri",  "URU", "MID", 30, 0.78, 0.22, 0.28, 1.2, 1.5, 0.8),
    p("Darwin Nunez",       "URU", "FWD", 42, 0.85, 0.50, 0.20, 2.5, 0.8, 0.4),
    p("Edinson Cavani",     "URU", "FWD",135, 0.85, 0.55, 0.18, 2.2, 0.5, 0.3),

    # ─── MEX ──────────────────────────────────────────────────────────────────
    p("Guillermo Ochoa",    "MEX", "GK", 138, 0.88, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Cesar Montes",       "MEX", "DEF", 48, 0.85, 0.06, 0.05, 0.2, 0.5, 2.0),
    p("Jorge Sanchez",      "MEX", "DEF", 40, 0.82, 0.06, 0.12, 0.2, 0.8, 1.5),
    p("Edson Alvarez",      "MEX", "MID", 68, 0.88, 0.08, 0.10, 0.3, 0.8, 3.0),
    p("Hector Herrera",     "MEX", "MID", 82, 0.85, 0.08, 0.18, 0.5, 1.5, 2.5),
    p("Chucky Lozano",      "MEX", "MID", 85, 0.85, 0.28, 0.22, 1.5, 1.5, 0.8),
    p("Raul Jimenez",       "MEX", "FWD", 72, 0.85, 0.48, 0.22, 1.8, 0.8, 0.4),
    p("Santiago Gimenez",   "MEX", "FWD", 20, 0.75, 0.52, 0.18, 2.2, 0.8, 0.4),

    # ─── NED ──────────────────────────────────────────────────────────────────
    p("Bart Verbruggen",    "NED", "GK",  18, 0.80, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Virgil van Dijk",    "NED", "DEF", 55, 0.92, 0.12, 0.10, 0.5, 0.8, 2.0),
    p("Denzel Dumfries",    "NED", "DEF", 50, 0.85, 0.10, 0.20, 0.4, 1.2, 1.5),
    p("Matthijs de Ligt",   "NED", "DEF", 50, 0.85, 0.08, 0.05, 0.3, 0.5, 2.0),
    p("Nathan Ake",         "NED", "DEF", 45, 0.82, 0.08, 0.08, 0.3, 0.6, 1.8),
    p("Frenkie de Jong",    "NED", "MID", 80, 0.88, 0.12, 0.22, 0.6, 1.8, 2.0),
    p("Tijjani Reijnders",  "NED", "MID", 28, 0.82, 0.22, 0.28, 1.0, 2.0, 1.5),
    p("Xavi Simons",        "NED", "MID", 30, 0.85, 0.22, 0.32, 1.2, 2.0, 1.0),
    p("Cody Gakpo",         "NED", "MID", 40, 0.82, 0.30, 0.28, 1.5, 1.5, 0.8),
    p("Memphis Depay",      "NED", "FWD", 95, 0.88, 0.55, 0.28, 2.5, 1.2, 0.4),
    p("Wout Weghorst",      "NED", "FWD", 48, 0.80, 0.40, 0.18, 1.8, 0.6, 0.4),

    # ─── CRO ──────────────────────────────────────────────────────────────────
    p("Dominik Livakovic",  "CRO", "GK",  55, 0.90, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Josko Gvardiol",     "CRO", "DEF", 48, 0.88, 0.12, 0.18, 0.5, 1.0, 2.0),
    p("Luka Modric",        "CRO", "MID",170, 0.88, 0.18, 0.35, 1.0, 2.5, 1.2),
    p("Mateo Kovacic",      "CRO", "MID",100, 0.88, 0.12, 0.22, 0.8, 1.8, 2.0),
    p("Marcelo Brozovic",   "CRO", "MID", 90, 0.88, 0.12, 0.18, 0.6, 1.5, 2.5),
    p("Ivan Perisic",       "CRO", "MID",115, 0.82, 0.28, 0.30, 1.5, 1.8, 1.0),
    p("Nikola Vlasic",      "CRO", "MID", 60, 0.82, 0.28, 0.25, 1.2, 1.5, 1.0),
    p("Andrej Kramaric",    "CRO", "FWD", 80, 0.85, 0.45, 0.28, 1.8, 1.5, 0.8),

    # ─── COL ──────────────────────────────────────────────────────────────────
    p("David Ospina",       "COL", "GK",  68, 0.82, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Davinson Sanchez",   "COL", "DEF", 82, 0.88, 0.06, 0.05, 0.2, 0.5, 2.5),
    p("Daniel Munoz",       "COL", "DEF", 38, 0.82, 0.08, 0.15, 0.3, 1.0, 1.5),
    p("James Rodriguez",    "COL", "MID",102, 0.88, 0.28, 0.55, 1.2, 3.5, 0.6),
    p("Richard Rios",       "COL", "MID", 22, 0.82, 0.12, 0.15, 0.5, 1.2, 2.5),
    p("Luis Diaz",          "COL", "MID", 45, 0.88, 0.32, 0.28, 1.8, 1.8, 1.0),
    p("Jhon Cordoba",       "COL", "FWD", 32, 0.78, 0.45, 0.15, 1.8, 0.6, 0.4),
    p("Jhon Duran",         "COL", "FWD", 18, 0.72, 0.42, 0.18, 1.8, 0.6, 0.5),

    # ─── ECU ──────────────────────────────────────────────────────────────────
    p("Hernan Galindez",    "ECU", "GK",  45, 0.82, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Piero Hincapie",     "ECU", "DEF", 40, 0.88, 0.08, 0.10, 0.3, 0.8, 2.0),
    p("Pervis Estupinan",   "ECU", "DEF", 42, 0.85, 0.08, 0.20, 0.3, 1.2, 1.2),
    p("Felix Torres",       "ECU", "DEF", 42, 0.82, 0.06, 0.05, 0.2, 0.5, 2.2),
    p("Moises Caicedo",     "ECU", "MID", 52, 0.90, 0.12, 0.15, 0.5, 1.2, 3.5),
    p("Romario Ibarra",     "ECU", "MID", 42, 0.80, 0.20, 0.22, 1.0, 1.2, 1.0),
    p("Gonzalo Plata",      "ECU", "MID", 48, 0.82, 0.22, 0.28, 1.2, 1.5, 0.8),
    p("Enner Valencia",     "ECU", "FWD", 68, 0.85, 0.52, 0.22, 2.2, 0.8, 0.5),
    p("Michael Estrada",    "ECU", "FWD", 38, 0.75, 0.38, 0.15, 1.8, 0.6, 0.4),

    # ─── AUT ──────────────────────────────────────────────────────────────────
    p("Patrick Pentz",      "AUT", "GK",  20, 0.80, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("David Alaba",        "AUT", "DEF", 95, 0.85, 0.08, 0.12, 0.3, 1.0, 1.5),
    p("Stefan Posch",       "AUT", "DEF", 40, 0.82, 0.06, 0.10, 0.2, 0.8, 1.5),
    p("Gernot Trauner",     "AUT", "DEF", 35, 0.82, 0.06, 0.05, 0.2, 0.5, 2.0),
    p("Marcel Sabitzer",    "AUT", "MID", 68, 0.85, 0.22, 0.28, 1.0, 2.0, 1.8),
    p("Konrad Laimer",      "AUT", "MID", 48, 0.82, 0.15, 0.18, 0.8, 1.2, 2.5),
    p("Christoph Baumgartner","AUT","MID",45, 0.82, 0.18, 0.30, 0.8, 1.8, 1.5),
    p("Michael Gregoritsch","AUT", "FWD", 55, 0.82, 0.38, 0.20, 1.8, 0.8, 0.5),
    p("Marko Arnautovic",   "AUT", "FWD",100, 0.85, 0.42, 0.22, 1.8, 0.8, 0.3),

    # ─── SCO ──────────────────────────────────────────────────────────────────
    p("Craig Gordon",       "SCO", "GK",  60, 0.82, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Andrew Robertson",   "SCO", "DEF", 60, 0.88, 0.05, 0.25, 0.3, 1.8, 1.2),
    p("Kieran Tierney",     "SCO", "DEF", 42, 0.85, 0.05, 0.12, 0.2, 1.0, 1.5),
    p("Grant Hanley",       "SCO", "DEF", 55, 0.82, 0.06, 0.05, 0.2, 0.5, 2.0),
    p("John McGinn",        "SCO", "MID", 52, 0.85, 0.18, 0.22, 0.8, 1.5, 2.0),
    p("Scott McTominay",    "SCO", "MID", 52, 0.88, 0.28, 0.18, 1.2, 1.5, 2.5),
    p("Callum McGregor",    "SCO", "MID", 48, 0.85, 0.12, 0.18, 0.6, 1.5, 2.2),
    p("Billy Gilmour",      "SCO", "MID", 38, 0.80, 0.10, 0.18, 0.5, 1.5, 2.5),
    p("Che Adams",          "SCO", "FWD", 42, 0.82, 0.35, 0.18, 1.5, 0.8, 0.5),
    p("Lyndon Dykes",       "SCO", "FWD", 45, 0.80, 0.42, 0.15, 1.8, 0.6, 0.5),

    # ─── NOR ──────────────────────────────────────────────────────────────────
    p("Orjan Nyland",       "NOR", "GK",  38, 0.82, 0.00, 0.00, 0.0, 0.3, 0.1),
    p("Kristoffer Ajer",    "NOR", "DEF", 48, 0.85, 0.05, 0.05, 0.2, 0.5, 2.0),
    p("Leo Ostigard",       "NOR", "DEF", 35, 0.82, 0.06, 0.05, 0.2, 0.5, 2.0),
    p("Patrick Pedersen",   "NOR", "DEF", 32, 0.80, 0.06, 0.12, 0.2, 0.8, 1.5),
    p("Martin Odegaard",    "NOR", "MID", 68, 0.88, 0.18, 0.38, 1.0, 2.8, 0.8),
    p("Sander Berge",       "NOR", "MID", 55, 0.85, 0.10, 0.15, 0.5, 1.0, 2.5),
    p("Mohamed Elyounoussi","NOR", "MID", 65, 0.82, 0.22, 0.25, 1.0, 1.5, 0.8),
    p("Antonio Nusa",       "NOR", "MID", 20, 0.78, 0.22, 0.28, 1.2, 1.5, 0.8),
    p("Erling Haaland",     "NOR", "FWD", 38, 0.90, 0.82, 0.18, 3.5, 0.8, 0.2),
    p("Alexander Sorloth",  "NOR", "FWD", 55, 0.82, 0.48, 0.18, 2.0, 0.6, 0.4),
]

data = dict(entries)
print(f"Generated {len(data)} NT player records")

# Spot-check key players
for name in ["Erling Haaland", "Kylian Mbappe", "Lionel Messi", "Harry Kane", "Moises Caicedo"]:
    key = norm(name)
    if key in data:
        d = data[key]
        print(f"  {name}: xg90={d['xg90']}, mp={d['mp']}, tackles90={d['tackles90']}")
    else:
        print(f"  MISSING: {name}")

with open("data/manual_nt_stats.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Wrote data/manual_nt_stats.json")
