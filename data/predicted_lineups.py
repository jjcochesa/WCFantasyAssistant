"""
Predicted starting XIs for the WC 2026 QUARTER-FINALS, keyed by 3-letter team code.

Names must match the FIFA Fantasy feed (data/fifa_players.json) after
normalisation — use the exact roster spellings. These XIs are AUTHORITATIVE:
a player in the XI is projected STARTER_MINUTES, everyone else on a listed team
gets BENCH_MINUTES (no blending with past WC minutes — the manager's call wins).
Teams not listed fall back to the stats pipeline (starter_rate + WC minutes).

User-supplied lineups for MD6 (QF), 08.07.26.
"""

STARTER_MINUTES = 80   # projected minutes for a predicted starter
BENCH_MINUTES   = 20   # projected minutes for a non-starter on a team with a known XI

PREDICTED_XI: dict[str, list[str]] = {
    "FRA": [
        "Mike Maignan",
        "Jules Koundé", "Dayot Upamecano", "William Saliba", "Lucas Digne",
        "Manu Koné", "Adrien Rabiot",
        "Michael Olise", "Ousmane Dembélé", "Bradley Barcola",
        "Kylian Mbappé",
    ],
    "MAR": [
        "Yassine Bounou",
        "Achraf Hakimi", "Issa Diop", "Chadi Riad", "Noussair Mazraoui",
        "Azzedine Ounahi", "Ayyoub Bouaddi", "Neil El Aynaoui",
        "Bilal El Khannouss", "Brahim Díaz", "Ismael Saibari",
    ],
    "ESP": [
        "Unai Simón",
        "Pedro Porro", "Pau Cubarsí", "Aymeric Laporte", "Marc Cucurella",
        "Pedri", "Rodri", "Dani Olmo",
        "Lamine Yamal", "Mikel Oyarzabal", "Álex Baena",
    ],
    "BEL": [
        "Thibaut Courtois",
        "Timothy Castagne", "Brandon Mechele", "Nathan Ngoy", "Maxim De Cuyper",
        "Youri Tielemans", "Kevin De Bruyne", "Hans Vanaken",
        "Jérémy Doku", "Charles De Ketelaere", "Leandro Trossard",
    ],
    "ENG": [
        "Jordan Pickford",
        "Djed Spence", "Ezri Konsa", "Marc Guéhi", "Nico O'Reilly",
        "Elliot Anderson", "Declan Rice", "Jude Bellingham",
        "Bukayo Saka", "Harry Kane", "Anthony Gordon",
    ],
    "NOR": [
        "Ørjan Nyland",
        "Julian Ryerson", "Kristoffer Ajer", "Torbjørn Heggem", "David Møller Wolfe",
        "Patrick Berg", "Sander Berge",
        "Martin Ødegaard", "Oscar Bobb",
        "Erling Haaland", "Antonio Nusa",
    ],
    "ARG": [
        "Emiliano Martínez",
        "Nahuel Molina", "Cristian Romero", "Lisandro Martínez", "Nicolás Tagliafico",
        "Leandro Paredes", "Rodrigo De Paul", "Alexis Mac Allister", "Enzo Fernández",
        "Lionel Messi", "Julián Alvarez",
    ],
    "SUI": [
        "Gregor Kobel",
        "Denis Zakaria", "Manuel Akanji", "Nico Elvedi", "Ricardo Rodríguez",
        "Remo Freuler", "Granit Xhaka",
        "Rubén Vargas", "Johan Manzambi",
        "Breel Embolo", "Dan Ndoye",
    ],
}
