"""
Predicted starting XIs for WC 2026, keyed by 3-letter team code.

Names match the FIFA Fantasy feed (data/fifa_players.json). Used to assign
projected minutes: a player in the XI is projected ~STARTER_MINUTES, everyone
else on a team WITH a defined XI gets ~BENCH_MINUTES. Teams not listed here
fall back to each player's starter_rate from the stats pipeline.

Add more teams over time — partial coverage is fine.
"""

STARTER_MINUTES = 70   # projected minutes for a predicted starter
BENCH_MINUTES   = 20   # projected minutes for a non-starter on a team with a known XI

PREDICTED_XI: dict[str, list[str]] = {
    "ARG": [
        "Emiliano Martínez", "Nahuel Molina", "Cristian Romero",
        "Lisandro Martínez", "Nicolás Tagliafico", "Leandro Paredes",
        "Enzo Fernández", "Alexis Mac Allister", "Lionel Messi",
        "Thiago Almada", "Julián Alvarez",
    ],
    "ESP": [
        "Unai Simón", "Marcos Llorente", "Pau Cubarsí", "Aymeric Laporte",
        "Marc Cucurella", "Rodri", "Pedri", "Fabián Ruiz",
        "Lamine Yamal", "Nico Williams", "Mikel Oyarzabal",
    ],
    "BRA": [
        "Alisson Becker", "Wesley", "Marquinhos", "Gabriel Magalhães",
        "Douglas Santos", "Casemiro", "Bruno Guimarães", "Matheus Cunha",
        "Raphinha", "Vinícius Júnior", "Endrick",
    ],
    "GER": [
        "Manuel Neuer", "Joshua Kimmich", "Jonathan Tah", "Nico Schlotterbeck",
        "David Raum", "Aleksandar Pavlovic", "Angelo Stiller", "Jamal Musiala",
        "Leroy Sané", "Florian Wirtz", "Kai Havertz",
    ],
    "ENG": [
        "Jordan Pickford", "Reece James", "Marc Guéhi", "Ezri Konsa",
        "Nico O'Reilly", "Elliot Anderson", "Declan Rice", "Jude Bellingham",
        "Bukayo Saka", "Anthony Gordon", "Harry Kane",
    ],
    "FRA": [
        "Mike Maignan", "Jules Koundé", "William Saliba", "Dayot Upamecano",
        "Theo Hernández", "Aurélien Tchouaméni", "N'Golo Kanté", "Rayan Cherki",
        "Michael Olise", "Ousmane Dembélé", "Kylian Mbappé",
    ],
    "NED": [
        "Bart Verbruggen", "Denzel Dumfries", "Jurriën Timber", "Virgil van Dijk",
        "Micky van de Ven", "Frenkie de Jong", "Ryan Gravenberch",
        "Tijjani Reijnders", "Donyell Malen", "Cody Gakpo", "Memphis Depay",
    ],
    "POR": [
        "Diogo Costa", "João Cancelo", "Rúben Dias", "Gonçalo Inácio",
        "Nuno Mendes", "João Neves", "Vitinha", "Bruno Fernandes",
        "Bernardo Silva", "João Félix", "Cristiano Ronaldo",
    ],
    "MAR": [
        "Yassine Bounou", "Achraf Hakimi", "Issa Diop", "Nayef Aguerd",
        "Noussair Mazraoui", "Neil El Aynaoui", "Ismael Saibari", "Bilal El Khannouss",
        "Brahim Díaz", "Abde Ezzalzouli", "Ayoub El Kaabi",
    ],
}
