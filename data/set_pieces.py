"""
Designated set-piece takers per national team (3-letter code).
Source: published WC 2026 set-piece taker chart (PK / FK / CK).

Each role maps to an ordered list of taker name-fragments, PRIMARY first.
Fragments are surnames (with optional initials) matched against the squad
in data_engine._assign_set_pieces — they need not be exact full names.

Roles:
  PK = penalties   -> expected-goals bonus (pos-weighted goal points)
  FK = free kicks  -> small direct-goal xG bonus
  CK = corners     -> expected-assist bonus
"""

SET_PIECES = {
    "ALG": {"PK": ["Mahrez"],               "FK": ["Mahrez", "Chaibi"],      "CK": ["Chaibi", "Mahrez"]},
    "ARG": {"PK": ["Messi"],                "FK": ["Messi"],                 "CK": ["Almada", "Messi"]},
    "AUS": {"PK": ["Boyle"],                "FK": ["Hrustic"],               "CK": ["Hrustic", "Boyle"]},
    "AUT": {"PK": ["Arnautovic", "Sabitzer"], "FK": ["Sabitzer", "Alaba"],   "CK": ["Alaba", "Sabitzer"]},
    "BEL": {"PK": ["Lukaku", "De Bruyne"],  "FK": ["De Bruyne"],             "CK": ["De Bruyne"]},
    "BIH": {"PK": ["Dzeko", "Demirovic"],   "FK": ["Bajraktarevic"],         "CK": ["Bajraktarevic", "Alajbegovic"]},
    "BRA": {"PK": ["Raphinha"],             "FK": ["Raphinha"],              "CK": ["Raphinha"]},
    "CPV": {"PK": ["Mendes", "Livramento"], "FK": ["Monteiro"],              "CK": ["Semedo", "Cabral"]},
    "CAN": {"PK": ["David"],                "FK": ["Estaquio", "Davies"],    "CK": ["Estaquio", "Davies"]},
    "COL": {"PK": ["J.Rodriguez"],          "FK": ["J.Rodriguez", "Arias"],  "CK": ["J.Rodriguez"]},
    "COD": {"PK": ["Wissa"],                "FK": ["Bongonda", "Wissa"],     "CK": ["Masuaku", "Bongonda"]},
    "CRO": {"PK": ["Modric"],               "FK": ["Modric"],                "CK": ["Modric", "Pasalic"]},
    "CUW": {"PK": ["L. Bacuna"],            "FK": ["J. Bacuna"],             "CK": ["J. Bacuna", "L. Bacuna"]},
    "CZE": {"PK": ["Schick", "Soucek"],     "FK": ["Sulc"],                  "CK": ["Coufal"]},
    "CIV": {"PK": ["Kessie"],               "FK": ["Amad"],                  "CK": ["Amad", "Diomande"]},
    "ECU": {"PK": ["Valencia", "Alcivar"],  "FK": ["Valencia", "Estupinan"], "CK": ["Alcivar", "Caicedo"]},
    "EGY": {"PK": ["Salah"],                "FK": ["Salah", "Marmoush"],     "CK": ["Salah"]},
    "ENG": {"PK": ["Kane"],                 "FK": ["Rice"],                  "CK": ["Rice", "Saka"]},
    "FRA": {"PK": ["Mbappe"],               "FK": ["Olise"],                 "CK": ["Olise"]},
    "GER": {"PK": ["Havertz", "Kimmich"],   "FK": ["Kimmich", "Wirtz"],      "CK": ["Kimmich", "Wirtz"]},
    "GHA": {"PK": ["Ayew"],                 "FK": ["Ayew", "Semenyo"],       "CK": ["Ayew", "Semenyo"]},
    "HAI": {"PK": ["Nazon", "Isidor"],      "FK": ["Bellegarde"],            "CK": ["Bellegarde"]},
    "IRN": {"PK": ["Taremi"],               "FK": ["Ghoddos", "Taremi"],     "CK": ["Ghoddos"]},
    "IRQ": {"PK": ["Al-Ammari", "Hussein"], "FK": ["Al-Ammari"],             "CK": ["Al-Ammari"]},
    "JPN": {"PK": ["Ueda", "Kubo"],         "FK": ["Kubo", "Doan"],          "CK": ["Kubo", "Kamada"]},
    "JOR": {"PK": ["Olwan"],                "FK": ["Tamari"],                "CK": ["Tamari"]},
    "KOR": {"PK": ["Son"],                  "FK": ["Son"],                   "CK": ["Kang-In Lee", "Son"]},
    "MEX": {"PK": ["Jimenez"],              "FK": ["Chavez", "Jimenez"],     "CK": ["Gutierrez"]},
    "MAR": {"PK": ["Diaz"],                 "FK": ["Hakimi", "Diaz"],        "CK": ["Hakimi"]},
    "NED": {"PK": ["Gakpo", "Depay"],       "FK": ["Depay"],                 "CK": ["Depay", "Gakpo"]},
    "NZL": {"PK": ["Wood"],                 "FK": ["Singh"],                 "CK": ["Singh"]},
    "NOR": {"PK": ["Haaland"],              "FK": ["Odegaard"],              "CK": ["Odegaard", "Ryerson"]},
    "PAN": {"PK": ["Davis", "Diaz"],        "FK": ["Carrasquilla", "Murillo"], "CK": ["Carrasquilla", "Davis"]},
    "PAR": {"PK": ["Enciso"],               "FK": ["Gomez", "Enciso"],       "CK": ["Gomez", "Enciso"]},
    "POR": {"PK": ["Ronaldo", "Fernandes"], "FK": ["Fernandes"],             "CK": ["Fernandes"]},
    "QAT": {"PK": ["Afif"],                 "FK": ["Afif"],                  "CK": ["Afif"]},
    "KSA": {"PK": ["Al-Darsawi"],           "FK": ["Al-Darsawi"],            "CK": ["Al-Darsawi"]},
    "SCO": {"PK": ["McTominay", "McGinn"],  "FK": ["McGinn"],                "CK": ["McGinn", "Ferguson"]},
    "SEN": {"PK": ["Mane"],                 "FK": ["Mane"],                  "CK": ["Diouf", "Camara"]},
    "RSA": {"PK": ["Foster", "Appollis"],   "FK": ["Modiba", "Appollis"],    "CK": ["Appollis", "Mokoena"]},
    "ESP": {"PK": ["Oyarzabal", "Yamal"],   "FK": ["Yamal"],                 "CK": ["Yamal", "Pedri"]},
    "SWE": {"PK": ["Gyokeres", "Isak"],     "FK": ["Nygren", "Gyokeres"],   "CK": ["Nygren", "Elanga"]},
    "SUI": {"PK": ["Xhaka"],                "FK": ["Xhaka"],                 "CK": ["Vargas", "Rieder"]},
    "TUN": {"PK": ["Abdi"],                 "FK": ["Hannibal"],              "CK": ["Hannibal", "Abdi"]},
    "TUR": {"PK": ["Calhanoglu"],           "FK": ["Calhanoglu"],            "CK": ["Calhanoglu", "Guler"]},
    "USA": {"PK": ["Balogun", "Pulisic"],   "FK": ["Tillman", "Pulisic"],    "CK": ["Tillman", "Pulisic"]},
    "URU": {"PK": ["Valverde"],             "FK": ["Valverde"],              "CK": ["De Arrascaeta", "Valverde"]},
    "UZB": {"PK": ["Shukurov"],             "FK": ["Fayzullayev"],           "CK": ["Fayzullayev", "Shukurov"]},
}
