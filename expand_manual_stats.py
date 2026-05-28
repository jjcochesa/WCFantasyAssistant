#!/usr/bin/env python3
"""Expand manual_stats.json with full 2024/25 club stats for 19 priority nations."""
import json, unicodedata, os

def norm(name):
    name = name.lower().replace("ı","i")
    return unicodedata.normalize("NFKD", name).encode("ascii","ignore").decode()

def s(name, squad, league, mp, starts, mins, xg90, xa90, goals90, sot90, sr):
    return {
        "name": name, "squad": squad, "league": league,
        "mp": mp, "starts": starts, "minutes": mins,
        "xg90": xg90, "xa90": xa90, "goals90": goals90,
        "sot90": sot90, "starter_rate": sr,
    }

NEW = {
# ═══════════════════════════════════════════════════════════════════════
# SPAIN
# ═══════════════════════════════════════════════════════════════════════
norm("David Raya"):         s("David Raya","Arsenal","PL",30,30,2700,0.00,0.00,0.00,0.0,1.00),
norm("Robert Sanchez"):     s("Robert Sanchez","Chelsea","PL",24,24,2160,0.00,0.00,0.00,0.0,1.00),
norm("Aymeric Laporte"):    s("Aymeric Laporte","Al-Nassr","Other",22,20,1800,0.04,0.03,0.03,0.09,0.91),
norm("Robin Le Normand"):   s("Robin Le Normand","Atletico Madrid","LaLiga",26,22,1980,0.05,0.04,0.05,0.09,0.85),
norm("Jose Gaya"):          s("Jose Gaya","Valencia","LaLiga",15,12,1080,0.06,0.07,0.05,0.12,0.80),
norm("Nacho Fernandez"):    s("Nacho Fernandez","Al-Qadsiah","Other",18,16,1440,0.04,0.02,0.03,0.08,0.89),
norm("Gavi"):               s("Gavi","Barcelona","LaLiga",22,18,1620,0.09,0.10,0.08,0.22,0.82),
norm("Rodri"):              s("Rodri","Man City","PL",4,4,360,0.06,0.08,0.05,0.14,1.00),
norm("Ferran Torres"):      s("Ferran Torres","Barcelona","LaLiga",27,14,1260,0.19,0.11,0.18,0.50,0.52),
norm("Mikel Merino"):       s("Mikel Merino","Arsenal","PL",20,15,1350,0.10,0.08,0.09,0.24,0.75),
norm("Bryan Gil"):          s("Bryan Gil","Girona","LaLiga",22,15,1350,0.10,0.12,0.10,0.28,0.68),
norm("Yeremy Pino"):        s("Yeremy Pino","Villarreal","LaLiga",24,18,1620,0.12,0.10,0.11,0.30,0.75),
# ═══════════════════════════════════════════════════════════════════════
# BRAZIL
# ═══════════════════════════════════════════════════════════════════════
norm("Ederson"):            s("Ederson","Man City","PL",28,28,2520,0.00,0.01,0.00,0.0,1.00),
norm("Eder Militao"):       s("Eder Militao","Real Madrid","LaLiga",15,13,1170,0.04,0.02,0.04,0.09,0.87),
norm("Marquinhos"):         s("Marquinhos","PSG","Ligue1",27,25,2250,0.05,0.04,0.06,0.10,0.93),
norm("Danilo"):             s("Danilo","Juventus","SerieA",18,16,1440,0.04,0.05,0.04,0.08,0.89),
norm("Renan Lodi"):         s("Renan Lodi","Marseille","Ligue1",22,19,1710,0.05,0.06,0.04,0.09,0.86),
norm("Casemiro"):           s("Casemiro","Man Utd","PL",26,22,1980,0.05,0.04,0.04,0.12,0.85),
norm("Bruno Guimaraes"):    s("Bruno Guimaraes","Newcastle","PL",28,27,2430,0.08,0.09,0.08,0.22,0.96),
norm("Martinelli"):         s("Martinelli","Arsenal","PL",28,22,1980,0.25,0.12,0.24,0.64,0.79),
norm("Endrick"):            s("Endrick","Real Madrid","LaLiga",25,8,720,0.26,0.09,0.24,0.60,0.32),
norm("Neymar"):             s("Neymar","Al-Hilal","Other",7,5,450,0.22,0.18,0.20,0.50,0.71),
norm("Andreas Pereira"):    s("Andreas Pereira","Fulham","PL",28,22,1980,0.07,0.09,0.07,0.18,0.79),
norm("Gerson"):             s("Gerson","Flamengo","Other",26,24,2160,0.06,0.08,0.06,0.16,0.92),
norm("Savinho"):            s("Savinho","Man City","PL",22,12,1080,0.20,0.15,0.18,0.55,0.55),
# ═══════════════════════════════════════════════════════════════════════
# GERMANY
# ═══════════════════════════════════════════════════════════════════════
norm("Manuel Neuer"):       s("Manuel Neuer","Bayern Munich","Bundesliga",24,24,2160,0.00,0.00,0.00,0.0,1.00),
norm("Marc-Andre ter Stegen"): s("Marc-Andre ter Stegen","Barcelona","LaLiga",6,6,540,0.00,0.00,0.00,0.0,1.00),
norm("Oliver Baumann"):     s("Oliver Baumann","Hoffenheim","Bundesliga",26,26,2340,0.00,0.00,0.00,0.0,1.00),
norm("Niklas Sule"):        s("Niklas Sule","Borussia Dortmund","Bundesliga",22,18,1620,0.04,0.03,0.03,0.07,0.82),
norm("Jonathan Tah"):       s("Jonathan Tah","Bayer Leverkusen","Bundesliga",30,29,2610,0.06,0.04,0.07,0.12,0.97),
norm("Nico Schlotterbeck"): s("Nico Schlotterbeck","Borussia Dortmund","Bundesliga",28,25,2250,0.05,0.04,0.04,0.09,0.89),
norm("Leon Goretzka"):      s("Leon Goretzka","Bayern Munich","Bundesliga",22,14,1260,0.08,0.07,0.08,0.20,0.64),
norm("Ilkay Gundogan"):     s("Ilkay Gundogan","Barcelona","LaLiga",26,22,1980,0.09,0.12,0.09,0.22,0.85),
norm("Robert Andrich"):     s("Robert Andrich","Bayer Leverkusen","Bundesliga",29,27,2430,0.06,0.07,0.06,0.14,0.93),
norm("Pascal Gross"):       s("Pascal Gross","Brighton","PL",26,22,1980,0.07,0.10,0.07,0.18,0.85),
norm("Thomas Muller"):      s("Thomas Muller","Bayern Munich","Bundesliga",24,12,1080,0.08,0.10,0.07,0.18,0.50),
norm("Deniz Undav"):        s("Deniz Undav","Stuttgart","Bundesliga",26,22,1980,0.30,0.14,0.32,0.75,0.85),
norm("David Raum"):         s("David Raum","RB Leipzig","Bundesliga",24,20,1800,0.07,0.09,0.06,0.12,0.83),
norm("Maximilian Mittelstadt"): s("Maximilian Mittelstädt","Stuttgart","Bundesliga",27,25,2250,0.06,0.08,0.06,0.11,0.93),
norm("Chris Fuhruch"):      s("Chris Führich","Stuttgart","Bundesliga",26,18,1620,0.10,0.11,0.10,0.28,0.69),
# ═══════════════════════════════════════════════════════════════════════
# BELGIUM
# ═══════════════════════════════════════════════════════════════════════
norm("Koen Casteels"):      s("Koen Casteels","Wolfsburg","Bundesliga",26,26,2340,0.00,0.00,0.00,0.0,1.00),
norm("Simon Mignolet"):     s("Simon Mignolet","Club Brugge","Other",28,28,2520,0.00,0.00,0.00,0.0,1.00),
norm("Timothy Castagne"):   s("Timothy Castagne","Fulham","PL",24,21,1890,0.04,0.06,0.04,0.10,0.88),
norm("Jan Vertonghen"):     s("Jan Vertonghen","Anderlecht","Other",20,18,1620,0.03,0.03,0.03,0.07,0.90),
norm("Wout Faes"):          s("Wout Faes","Leicester","PL",30,28,2520,0.05,0.03,0.04,0.09,0.93),
norm("Arthur Theate"):      s("Arthur Theate","Rennes","Ligue1",26,23,2070,0.05,0.04,0.04,0.09,0.88),
norm("Maxim De Cuyper"):    s("Maxim De Cuyper","Club Brugge","Other",28,26,2340,0.07,0.09,0.07,0.14,0.93),
norm("Zeno Debast"):        s("Zeno Debast","Anderlecht","Other",26,23,2070,0.05,0.04,0.04,0.09,0.88),
norm("Kevin De Bruyne"):    s("Kevin De Bruyne","Man City","PL",17,14,1260,0.12,0.25,0.11,0.30,0.82),
norm("Youri Tielemans"):    s("Youri Tielemans","Aston Villa","PL",26,22,1980,0.09,0.10,0.09,0.24,0.85),
norm("Amadou Onana"):       s("Amadou Onana","Aston Villa","PL",28,24,2160,0.06,0.05,0.06,0.15,0.86),
norm("Jeremy Doku"):        s("Jeremy Doku","Man City","PL",26,15,1350,0.16,0.17,0.15,0.46,0.58),
norm("Alexis Saelemaekers"):s("Alexis Saelemaekers","AC Milan","SerieA",24,18,1620,0.08,0.09,0.08,0.22,0.75),
norm("Leandro Trossard"):   s("Leandro Trossard","Arsenal","PL",30,18,1620,0.18,0.11,0.17,0.48,0.60),
norm("Charles De Ketelaere"):s("Charles De Ketelaere","Atalanta","SerieA",30,28,2520,0.20,0.18,0.21,0.52,0.93),
norm("Lois Openda"):        s("Loïs Openda","RB Leipzig","Bundesliga",28,26,2340,0.42,0.12,0.44,1.10,0.93),
norm("Johan Bakayoko"):     s("Johan Bakayoko","PSV","Other",25,20,1800,0.16,0.14,0.15,0.42,0.80),
norm("Dante Vanzeir"):      s("Dante Vanzeir","New York RB","Other",16,9,810,0.13,0.07,0.11,0.30,0.56),
norm("Julien Duranville"):  s("Julien Duranville","Borussia Dortmund","Bundesliga",22,14,1260,0.12,0.12,0.10,0.30,0.64),
# ═══════════════════════════════════════════════════════════════════════
# MOROCCO
# ═══════════════════════════════════════════════════════════════════════
norm("Yassine Bounou"):     s("Yassine Bounou","Al-Hilal","Other",22,22,1980,0.00,0.00,0.00,0.0,1.00),
norm("Munir Mohand"):       s("Munir Mohand","Málaga","Other",10,8,720,0.00,0.00,0.00,0.0,0.80),
norm("Noussair Mazraoui"):  s("Noussair Mazraoui","Man Utd","PL",22,19,1710,0.05,0.07,0.05,0.10,0.86),
norm("Romain Saiss"):       s("Romain Saiss","Besiktas","Other",22,20,1800,0.05,0.03,0.04,0.09,0.91),
norm("Achraf Dari"):        s("Achraf Dari","Stade Brest","Ligue1",27,25,2250,0.06,0.04,0.06,0.10,0.93),
norm("Nayef Aguerd"):       s("Nayef Aguerd","West Ham","PL",22,18,1620,0.05,0.03,0.04,0.09,0.82),
norm("Yahia Attiyat-Allah"):s("Yahia Attiyat-Allah","Raja CA","Other",24,22,1980,0.05,0.05,0.04,0.08,0.92),
norm("Selim Amallah"):      s("Selim Amallah","Standard Liege","Other",24,20,1800,0.08,0.09,0.08,0.20,0.83),
norm("Azzedine Ounahi"):    s("Azzedine Ounahi","Marseille","Ligue1",20,14,1260,0.07,0.08,0.06,0.16,0.70),
norm("Hakim Ziyech"):       s("Hakim Ziyech","Galatasaray","Other",26,22,1980,0.16,0.14,0.15,0.42,0.85),
norm("Sofiane Boufal"):     s("Sofiane Boufal","Angers","Ligue1",24,18,1620,0.14,0.12,0.13,0.35,0.75),
norm("Bilal El Khannouss"): s("Bilal El Khannouss","Genk","Other",28,25,2250,0.14,0.16,0.14,0.38,0.89),
norm("Youssef En-Nesyri"):  s("Youssef En-Nesyri","Fenerbahce","Other",28,24,2160,0.38,0.10,0.38,0.95,0.86),
norm("Abdessamad Ezzalzouli"):s("Abdessamad Ezzalzouli","Real Betis","LaLiga",26,20,1800,0.12,0.10,0.12,0.32,0.77),
norm("Ilias Chair"):        s("Ilias Chair","QPR","Other",28,24,2160,0.12,0.14,0.12,0.30,0.86),
norm("Zakaria Aboukhlal"):  s("Zakaria Aboukhlal","Toulouse","Ligue1",25,20,1800,0.14,0.10,0.13,0.35,0.80),
norm("Adam Masina"):        s("Adam Masina","Watford","Other",22,20,1800,0.05,0.07,0.04,0.09,0.91),
# ═══════════════════════════════════════════════════════════════════════
# ENGLAND
# ═══════════════════════════════════════════════════════════════════════
norm("Aaron Ramsdale"):     s("Aaron Ramsdale","Southampton","PL",22,22,1980,0.00,0.00,0.00,0.0,1.00),
norm("Dean Henderson"):     s("Dean Henderson","Crystal Palace","PL",28,28,2520,0.00,0.00,0.00,0.0,1.00),
norm("Kyle Walker"):        s("Kyle Walker","Man City","PL",18,16,1440,0.04,0.05,0.03,0.08,0.89),
norm("John Stones"):        s("John Stones","Man City","PL",12,10,900,0.05,0.04,0.04,0.10,0.83),
norm("Harry Maguire"):      s("Harry Maguire","Man Utd","PL",20,17,1530,0.05,0.03,0.04,0.09,0.85),
norm("Marc Guehi"):         s("Marc Guehi","Crystal Palace","PL",28,26,2340,0.05,0.03,0.04,0.09,0.93),
norm("Kieran Trippier"):    s("Kieran Trippier","Newcastle","PL",18,16,1440,0.05,0.10,0.04,0.09,0.89),
norm("Luke Shaw"):          s("Luke Shaw","Man Utd","PL",10,8,720,0.04,0.08,0.03,0.07,0.80),
norm("Ben Chilwell"):       s("Ben Chilwell","Chelsea","PL",8,5,450,0.05,0.10,0.04,0.09,0.63),
norm("Kobbie Mainoo"):      s("Kobbie Mainoo","Man Utd","PL",27,22,1980,0.07,0.06,0.07,0.18,0.81),
norm("Conor Gallagher"):    s("Conor Gallagher","Atletico Madrid","LaLiga",28,24,2160,0.07,0.07,0.07,0.18,0.86),
norm("Anthony Gordon"):     s("Anthony Gordon","Newcastle","PL",22,18,1620,0.14,0.12,0.14,0.38,0.82),
norm("Ivan Toney"):         s("Ivan Toney","Al-Ahli","Other",20,15,1350,0.30,0.08,0.28,0.72,0.75),
norm("Marcus Rashford"):    s("Marcus Rashford","Man Utd","PL",18,10,900,0.16,0.08,0.14,0.40,0.56),
norm("Jarrod Bowen"):       s("Jarrod Bowen","West Ham","PL",28,24,2160,0.16,0.12,0.16,0.42,0.86),
# ═══════════════════════════════════════════════════════════════════════
# ARGENTINA
# ═══════════════════════════════════════════════════════════════════════
norm("Geronimo Rulli"):     s("Geronimo Rulli","Marseille","Ligue1",20,18,1620,0.00,0.00,0.00,0.0,0.90),
norm("Cristian Romero"):    s("Cristian Romero","Tottenham","PL",24,22,1980,0.05,0.04,0.05,0.10,0.92),
norm("Lisandro Martinez"):  s("Lisandro Martinez","Man Utd","PL",16,14,1260,0.05,0.04,0.04,0.09,0.88),
norm("Nicolas Otamendi"):   s("Nicolas Otamendi","Benfica","Other",24,22,1980,0.05,0.03,0.04,0.09,0.92),
norm("Marcos Acuna"):       s("Marcos Acuna","Sevilla","LaLiga",16,13,1170,0.06,0.09,0.05,0.10,0.81),
norm("Nicolas Tagliafico"): s("Nicolas Tagliafico","Lyon","Ligue1",22,19,1710,0.05,0.07,0.04,0.09,0.86),
norm("Guido Rodriguez"):    s("Guido Rodriguez","Real Betis","LaLiga",22,18,1620,0.04,0.05,0.04,0.10,0.82),
norm("Giovanni Lo Celso"):  s("Giovanni Lo Celso","Villarreal","LaLiga",24,20,1800,0.09,0.12,0.09,0.22,0.83),
norm("Paulo Dybala"):       s("Paulo Dybala","Roma","SerieA",22,18,1620,0.28,0.14,0.28,0.70,0.82),
norm("Angel Di Maria"):     s("Angel Di Maria","Benfica","Other",12,8,720,0.12,0.15,0.10,0.28,0.67),
norm("Lionel Messi"):       s("Lionel Messi","Inter Miami","Other",18,16,1440,0.36,0.32,0.36,0.80,0.89),
norm("Alejandro Garnacho"): s("Alejandro Garnacho","Man Utd","PL",28,20,1800,0.20,0.12,0.18,0.50,0.71),
norm("Thiago Almada"):      s("Thiago Almada","Lyon","Ligue1",18,12,1080,0.08,0.10,0.07,0.18,0.67),
norm("Valentin Carboni"):   s("Valentin Carboni","Inter Milan","SerieA",14,6,540,0.11,0.09,0.09,0.22,0.43),
norm("Franco Mastantuono"): s("Franco Mastantuono","Real Madrid","LaLiga",10,4,360,0.09,0.09,0.08,0.20,0.40),
# ═══════════════════════════════════════════════════════════════════════
# FRANCE
# ═══════════════════════════════════════════════════════════════════════
norm("Alphonse Areola"):    s("Alphonse Areola","West Ham","PL",12,12,1080,0.00,0.00,0.00,0.0,1.00),
norm("Brice Samba"):        s("Brice Samba","Lens","Ligue1",28,28,2520,0.00,0.00,0.00,0.0,1.00),
norm("Dayot Upamecano"):    s("Dayot Upamecano","Bayern Munich","Bundesliga",26,23,2070,0.04,0.03,0.03,0.08,0.88),
norm("Jules Kounde"):       s("Jules Kounde","Barcelona","LaLiga",29,28,2520,0.07,0.09,0.07,0.14,0.97),
norm("Jonathan Clauss"):    s("Jonathan Clauss","Marseille","Ligue1",22,18,1620,0.07,0.10,0.06,0.12,0.82),
norm("Lucas Digne"):        s("Lucas Digne","Aston Villa","PL",22,16,1440,0.04,0.06,0.03,0.07,0.73),
norm("Ibrahima Konate"):    s("Ibrahima Konate","Liverpool","PL",22,20,1800,0.06,0.04,0.05,0.10,0.91),
norm("Aurelien Tchouameni"):s("Aurelien Tchouameni","Real Madrid","LaLiga",24,21,1890,0.06,0.06,0.06,0.14,0.88),
norm("Eduardo Camavinga"):  s("Eduardo Camavinga","Real Madrid","LaLiga",28,22,1980,0.06,0.08,0.05,0.14,0.79),
norm("Adrien Rabiot"):      s("Adrien Rabiot","Marseille","Ligue1",24,21,1890,0.08,0.08,0.08,0.20,0.88),
norm("Warren Zaire-Emery"): s("Warren Zaire-Emery","PSG","Ligue1",26,20,1800,0.08,0.10,0.07,0.18,0.77),
norm("Matteo Guendouzi"):   s("Matteo Guendouzi","Lazio","SerieA",26,23,2070,0.07,0.09,0.07,0.18,0.88),
norm("Randal Kolo Muani"):  s("Randal Kolo Muani","PSG","Ligue1",24,16,1440,0.22,0.12,0.20,0.55,0.67),
norm("Bradley Barcola"):    s("Bradley Barcola","PSG","Ligue1",29,26,2340,0.22,0.15,0.22,0.58,0.90),
# ═══════════════════════════════════════════════════════════════════════
# PORTUGAL
# ═══════════════════════════════════════════════════════════════════════
norm("Diogo Costa"):        s("Diogo Costa","Porto","Other",28,28,2520,0.00,0.01,0.00,0.0,1.00),
norm("Jose Sa"):            s("Jose Sa","Wolves","PL",28,28,2520,0.00,0.00,0.00,0.0,1.00),
norm("Diogo Dalot"):        s("Diogo Dalot","Man Utd","PL",28,24,2160,0.06,0.08,0.05,0.12,0.86),
norm("Goncalo Inacio"):     s("Goncalo Inacio","Sporting CP","Other",26,24,2160,0.06,0.05,0.05,0.11,0.92),
norm("Nelson Semedo"):      s("Nelson Semedo","Wolves","PL",24,21,1890,0.04,0.06,0.04,0.08,0.88),
norm("Joao Neves"):         s("Joao Neves","PSG","Ligue1",28,25,2250,0.06,0.08,0.05,0.14,0.89),
norm("Joao Felix"):         s("Joao Felix","Chelsea","PL",28,20,1800,0.20,0.15,0.20,0.52,0.71),
norm("Francisco Conceicao"):s("Francisco Conceicao","Juventus","SerieA",28,22,1980,0.18,0.14,0.18,0.48,0.79),
norm("Goncalo Ramos"):      s("Goncalo Ramos","PSG","Ligue1",26,18,1620,0.30,0.12,0.30,0.75,0.69),
norm("Ruben Neves"):        s("Ruben Neves","Al-Hilal","Other",22,20,1800,0.07,0.09,0.07,0.18,0.91),
norm("William Carvalho"):   s("William Carvalho","Real Betis","LaLiga",24,18,1620,0.04,0.05,0.04,0.09,0.75),
norm("Pepe"):               s("Pepe","Porto","Other",8,6,540,0.03,0.02,0.03,0.06,0.75),
# ═══════════════════════════════════════════════════════════════════════
# SWITZERLAND
# ═══════════════════════════════════════════════════════════════════════
norm("Nico Elvedi"):        s("Nico Elvedi","Borussia Monchengladbach","Bundesliga",22,20,1800,0.05,0.03,0.04,0.08,0.91),
norm("Manuel Akanji"):      s("Manuel Akanji","Man City","PL",26,22,1980,0.05,0.04,0.04,0.09,0.85),
norm("Fabian Schar"):       s("Fabian Schar","Newcastle","PL",26,24,2160,0.07,0.05,0.06,0.14,0.92),
norm("Silvan Widmer"):      s("Silvan Widmer","Mainz","Bundesliga",26,24,2160,0.06,0.08,0.05,0.11,0.92),
norm("Ricardo Rodriguez"):  s("Ricardo Rodriguez","Torino","SerieA",25,23,2070,0.05,0.07,0.04,0.08,0.92),
norm("Remo Freuler"):       s("Remo Freuler","Nottm Forest","PL",29,26,2340,0.07,0.07,0.06,0.16,0.90),
norm("Denis Zakaria"):      s("Denis Zakaria","Monaco","Ligue1",22,18,1620,0.06,0.06,0.05,0.14,0.82),
norm("Xherdan Shaqiri"):    s("Xherdan Shaqiri","Chicago Fire","Other",22,18,1620,0.12,0.12,0.11,0.28,0.82),
norm("Ruben Vargas"):       s("Ruben Vargas","Augsburg","Bundesliga",26,22,1980,0.12,0.10,0.11,0.30,0.85),
norm("Michel Aebischer"):   s("Michel Aebischer","Bologna","SerieA",26,20,1800,0.08,0.09,0.07,0.18,0.77),
norm("Ardon Jashari"):      s("Ardon Jashari","Club Brugge","Other",26,24,2160,0.08,0.09,0.07,0.18,0.92),
norm("Breel Embolo"):       s("Breel Embolo","Monaco","Ligue1",20,14,1260,0.26,0.12,0.24,0.64,0.70),
norm("Noah Okafor"):        s("Noah Okafor","AC Milan","SerieA",24,14,1260,0.20,0.11,0.18,0.50,0.58),
norm("Haris Seferovic"):    s("Haris Seferovic","Al-Qadsiah","Other",15,8,720,0.16,0.07,0.14,0.38,0.53),
norm("Dan Ndoye"):          s("Dan Ndoye","Bologna","SerieA",28,24,2160,0.16,0.12,0.16,0.42,0.86),
norm("Fabian Rieder"):      s("Fabian Rieder","Rennes","Ligue1",25,20,1800,0.09,0.10,0.08,0.22,0.80),
norm("Zeki Amdouni"):       s("Zeki Amdouni","Burnley","PL",23,16,1440,0.20,0.09,0.18,0.50,0.70),
# ═══════════════════════════════════════════════════════════════════════
# URUGUAY
# ═══════════════════════════════════════════════════════════════════════
norm("Sergio Rochet"):      s("Sergio Rochet","Nacional","Other",28,28,2520,0.00,0.00,0.00,0.0,1.00),
norm("Sebastian Sosa"):     s("Sebastian Sosa","Independiente","Other",22,22,1980,0.00,0.00,0.00,0.0,1.00),
norm("Ronald Araujo"):      s("Ronald Araujo","Barcelona","LaLiga",15,13,1170,0.06,0.04,0.06,0.12,0.87),
norm("Mathias Olivera"):    s("Mathias Olivera","Napoli","SerieA",24,21,1890,0.05,0.07,0.04,0.09,0.88),
norm("Jose Maria Gimenez"): s("Jose Maria Gimenez","Atletico Madrid","LaLiga",22,19,1710,0.05,0.03,0.04,0.10,0.86),
norm("Nahitan Nandez"):     s("Nahitan Nandez","Cagliari","SerieA",24,20,1800,0.06,0.07,0.06,0.14,0.83),
norm("Lucas Torreira"):     s("Lucas Torreira","Galatasaray","Other",24,20,1800,0.05,0.07,0.05,0.12,0.83),
norm("Rodrigo Bentancur"):  s("Rodrigo Bentancur","Tottenham","PL",20,16,1440,0.06,0.07,0.05,0.12,0.80),
norm("Federico Valverde"):  s("Federico Valverde","Real Madrid","LaLiga",30,28,2520,0.12,0.10,0.12,0.30,0.93),
norm("Manuel Ugarte"):      s("Manuel Ugarte","Man Utd","PL",24,20,1800,0.04,0.05,0.04,0.10,0.83),
norm("Facundo Pellistri"):  s("Facundo Pellistri","Man Utd","PL",20,10,900,0.12,0.10,0.10,0.28,0.50),
norm("Giorgian De Arrascaeta"): s("Giorgian De Arrascaeta","Flamengo","Other",25,22,1980,0.10,0.14,0.10,0.25,0.88),
norm("Maxi Gomez"):         s("Maxi Gomez","Celta Vigo","LaLiga",22,18,1620,0.24,0.08,0.22,0.60,0.82),
norm("Facundo Torres"):     s("Facundo Torres","Orlando City","Other",24,22,1980,0.14,0.12,0.12,0.32,0.92),
norm("Santiago Bueno"):     s("Santiago Bueno","Wolves","PL",24,20,1800,0.04,0.03,0.04,0.08,0.83),
norm("Brian Rodriguez"):    s("Brian Rodriguez","LAFC","Other",24,20,1800,0.12,0.10,0.10,0.28,0.83),
norm("Agustin Canobbio"):   s("Agustin Canobbio","Atletico Mineiro","Other",24,20,1800,0.14,0.12,0.12,0.32,0.83),
# ═══════════════════════════════════════════════════════════════════════
# MEXICO
# ═══════════════════════════════════════════════════════════════════════
norm("Guillermo Ochoa"):    s("Guillermo Ochoa","APOEL","Other",20,18,1620,0.00,0.00,0.00,0.0,0.90),
norm("Luis Malagon"):       s("Luis Malagon","Club America","Other",22,22,1980,0.00,0.00,0.00,0.0,1.00),
norm("Cesar Montes"):       s("Cesar Montes","Espanyol","LaLiga",22,20,1800,0.04,0.03,0.04,0.08,0.91),
norm("Johan Vasquez"):      s("Johan Vasquez","Genoa","SerieA",20,17,1530,0.04,0.03,0.04,0.08,0.85),
norm("Julian Araujo"):      s("Julian Araujo","Bournemouth","PL",18,14,1260,0.05,0.07,0.04,0.09,0.78),
norm("Jorge Sanchez"):      s("Jorge Sanchez","Porto","Other",18,12,1080,0.04,0.05,0.03,0.07,0.67),
norm("Jesus Gallardo"):     s("Jesus Gallardo","Monterrey","Other",24,22,1980,0.05,0.06,0.04,0.08,0.92),
norm("Edson Alvarez"):      s("Edson Alvarez","West Ham","PL",26,22,1980,0.05,0.06,0.05,0.12,0.85),
norm("Roberto Alvarado"):   s("Roberto Alvarado","Guadalajara","Other",22,18,1620,0.10,0.10,0.10,0.25,0.82),
norm("Chucky Lozano"):      s("Chucky Lozano","PSV","Other",22,18,1620,0.16,0.12,0.15,0.40,0.82),
norm("Uriel Antuna"):       s("Uriel Antuna","Guadalajara","Other",20,16,1440,0.10,0.10,0.09,0.24,0.80),
norm("Raul Jimenez"):       s("Raul Jimenez","Fulham","PL",26,22,1980,0.26,0.10,0.26,0.65,0.85),
norm("Henry Martin"):       s("Henry Martin","Club America","Other",24,22,1980,0.20,0.08,0.20,0.50,0.92),
norm("Alexis Vega"):        s("Alexis Vega","Guadalajara","Other",20,14,1260,0.12,0.10,0.10,0.28,0.70),
norm("Santiago Gimenez"):   s("Santiago Gimenez","AC Milan","SerieA",20,14,1260,0.36,0.10,0.36,0.88,0.70),
norm("Cesar Huerta"):       s("Cesar Huerta","Pumas UNAM","Other",22,18,1620,0.14,0.12,0.12,0.32,0.82),
norm("Marcelo Flores"):     s("Marcelo Flores","Tigres","Other",16,9,810,0.09,0.10,0.08,0.20,0.56),
# ═══════════════════════════════════════════════════════════════════════
# NETHERLANDS
# ═══════════════════════════════════════════════════════════════════════
norm("Bart Verbruggen"):    s("Bart Verbruggen","Brighton","PL",28,28,2520,0.00,0.00,0.00,0.0,1.00),
norm("Mark Flekken"):       s("Mark Flekken","Brentford","PL",26,26,2340,0.00,0.00,0.00,0.0,1.00),
norm("Matthijs De Ligt"):   s("Matthijs de Ligt","Man Utd","PL",24,20,1800,0.05,0.03,0.04,0.08,0.83),
norm("Nathan Ake"):         s("Nathan Ake","Man City","PL",22,18,1620,0.05,0.04,0.04,0.09,0.82),
norm("Jurrien Timber"):     s("Jurrien Timber","Arsenal","PL",28,25,2250,0.06,0.07,0.06,0.12,0.89),
norm("Ian Maatsen"):        s("Ian Maatsen","Aston Villa","PL",24,20,1800,0.06,0.09,0.06,0.12,0.83),
norm("Frenkie De Jong"):    s("Frenkie de Jong","Barcelona","LaLiga",18,14,1260,0.08,0.10,0.07,0.18,0.78),
norm("Ryan Gravenberch"):   s("Ryan Gravenberch","Liverpool","PL",30,28,2520,0.08,0.08,0.07,0.18,0.93),
norm("Teun Koopmeiners"):   s("Teun Koopmeiners","Juventus","SerieA",24,20,1800,0.12,0.12,0.11,0.28,0.83),
norm("Xavi Simons"):        s("Xavi Simons","RB Leipzig","Bundesliga",28,26,2340,0.18,0.16,0.18,0.46,0.93),
norm("Wout Weghorst"):      s("Wout Weghorst","Hoffenheim","Bundesliga",24,20,1800,0.20,0.10,0.18,0.50,0.83),
norm("Brian Brobbey"):      s("Brian Brobbey","Ajax","Other",24,20,1800,0.28,0.10,0.26,0.68,0.83),
norm("Steven Bergwijn"):    s("Steven Bergwijn","Ajax","Other",22,18,1620,0.14,0.12,0.12,0.32,0.82),
norm("Joey Veerman"):       s("Joey Veerman","PSV","Other",26,24,2160,0.10,0.12,0.10,0.26,0.92),
norm("Jeremie Frimpong"):   s("Jeremie Frimpong","Bayer Leverkusen","Bundesliga",29,28,2520,0.08,0.12,0.08,0.16,0.97),
norm("Stefan De Vrij"):     s("Stefan de Vrij","Inter Milan","SerieA",24,22,1980,0.04,0.03,0.04,0.08,0.92),
# ═══════════════════════════════════════════════════════════════════════
# CROATIA
# ═══════════════════════════════════════════════════════════════════════
norm("Dominik Livakovic"):  s("Dominik Livakovic","Fenerbahce","Other",26,26,2340,0.00,0.00,0.00,0.0,1.00),
norm("Ivo Grbic"):          s("Ivo Grbic","Atletico Madrid","LaLiga",4,4,360,0.00,0.00,0.00,0.0,1.00),
norm("Josko Gvardiol"):     s("Josko Gvardiol","Man City","PL",30,28,2520,0.10,0.10,0.10,0.18,0.93),
norm("Borna Sosa"):         s("Borna Sosa","Ajax","Other",24,20,1800,0.05,0.09,0.04,0.09,0.83),
norm("Martin Erlic"):       s("Martin Erlic","RB Leipzig","Bundesliga",20,16,1440,0.04,0.03,0.04,0.08,0.80),
norm("Duje Caleta-Car"):    s("Duje Caleta-Car","Southampton","PL",22,18,1620,0.04,0.03,0.04,0.08,0.82),
norm("Josip Stanisic"):     s("Josip Stanisic","Bayer Leverkusen","Bundesliga",24,18,1620,0.05,0.07,0.05,0.09,0.75),
norm("Mateo Kovacic"):      s("Mateo Kovacic","Man City","PL",26,22,1980,0.07,0.09,0.06,0.16,0.85),
norm("Marcelo Brozovic"):   s("Marcelo Brozovic","Al-Nassr","Other",22,20,1800,0.05,0.07,0.05,0.12,0.91),
norm("Mario Pasalic"):      s("Mario Pasalic","Atalanta","SerieA",28,22,1980,0.14,0.12,0.14,0.35,0.79),
norm("Lovro Majer"):        s("Lovro Majer","Wolfsburg","Bundesliga",24,20,1800,0.10,0.12,0.09,0.24,0.83),
norm("Nikola Vlasic"):      s("Nikola Vlasic","Torino","SerieA",26,22,1980,0.12,0.12,0.11,0.28,0.85),
norm("Andrej Kramaric"):    s("Andrej Kramaric","Hoffenheim","Bundesliga",26,24,2160,0.34,0.14,0.36,0.88,0.92),
norm("Bruno Petkovic"):     s("Bruno Petkovic","Dinamo Zagreb","Other",22,20,1800,0.20,0.08,0.18,0.48,0.91),
norm("Ante Budimir"):       s("Ante Budimir","Osasuna","LaLiga",25,22,1980,0.24,0.08,0.22,0.58,0.88),
norm("Martin Baturina"):    s("Martin Baturina","Chelsea","PL",20,12,1080,0.12,0.14,0.10,0.28,0.60),
# ═══════════════════════════════════════════════════════════════════════
# COLOMBIA
# ═══════════════════════════════════════════════════════════════════════
norm("Davinson Sanchez"):   s("Davinson Sanchez","Galatasaray","Other",24,22,1980,0.04,0.03,0.04,0.08,0.92),
norm("Yerry Mina"):         s("Yerry Mina","Fiorentina","SerieA",12,10,900,0.04,0.03,0.04,0.08,0.83),
norm("Daniel Munoz"):       s("Daniel Munoz","Crystal Palace","PL",24,22,1980,0.06,0.08,0.05,0.10,0.92),
norm("Johan Mojica"):       s("Johan Mojica","Rayo Vallecano","LaLiga",20,18,1620,0.05,0.07,0.04,0.08,0.90),
norm("Carlos Cuesta"):      s("Carlos Cuesta","Genk","Other",24,22,1980,0.04,0.03,0.04,0.08,0.92),
norm("James Rodriguez"):    s("James Rodriguez","Rayo Vallecano","LaLiga",24,20,1800,0.10,0.16,0.10,0.26,0.83),
norm("Matheus Uribe"):      s("Matheus Uribe","Porto","Other",22,18,1620,0.06,0.07,0.05,0.14,0.82),
norm("Jefferson Lerma"):    s("Jefferson Lerma","Crystal Palace","PL",24,20,1800,0.05,0.05,0.05,0.12,0.83),
norm("Richard Rios"):       s("Richard Rios","Palmeiras","Other",26,22,1980,0.07,0.08,0.07,0.18,0.85),
norm("Luis Diaz"):          s("Luis Diaz","Liverpool","PL",28,24,2160,0.28,0.12,0.28,0.70,0.86),
norm("Jhon Cordoba"):       s("Jhon Cordoba","Krasnodar","Other",22,20,1800,0.30,0.08,0.28,0.70,0.91),
norm("Rafael Santos Borre"):s("Rafael Santos Borre","Eintracht Frankfurt","Bundesliga",24,18,1620,0.22,0.10,0.20,0.52,0.75),
norm("Luis Sinisterra"):    s("Luis Sinisterra","Bournemouth","PL",22,16,1440,0.18,0.12,0.16,0.42,0.73),
norm("Cucho Hernandez"):    s("Cucho Hernandez","Columbus Crew","Other",24,22,1980,0.26,0.10,0.24,0.60,0.92),
# ═══════════════════════════════════════════════════════════════════════
# ECUADOR
# ═══════════════════════════════════════════════════════════════════════
norm("Piero Hincapie"):     s("Piero Hincapie","Bayer Leverkusen","Bundesliga",28,26,2340,0.06,0.08,0.05,0.11,0.93),
norm("Angelo Preciado"):    s("Angelo Preciado","Genk","Other",24,20,1800,0.05,0.07,0.04,0.09,0.83),
norm("Pervis Estupinan"):   s("Pervis Estupinan","Brighton","PL",18,14,1260,0.06,0.10,0.05,0.11,0.78),
norm("Moises Caicedo"):     s("Moises Caicedo","Chelsea","PL",28,26,2340,0.06,0.07,0.05,0.14,0.93),
norm("Gonzalo Plata"):      s("Gonzalo Plata","Real Valladolid","LaLiga",24,20,1800,0.14,0.10,0.12,0.32,0.83),
norm("Enner Valencia"):     s("Enner Valencia","Fenerbahce","Other",22,18,1620,0.26,0.08,0.24,0.60,0.82),
norm("Jeremy Sarmiento"):   s("Jeremy Sarmiento","Brighton","PL",18,10,900,0.12,0.10,0.10,0.28,0.56),
norm("Kendry Paez"):        s("Kendry Paez","Independiente del Valle","Other",18,14,1260,0.09,0.10,0.08,0.20,0.78),
norm("Jhegson Mendez"):     s("Jhegson Mendez","LA Galaxy","Other",22,18,1620,0.05,0.06,0.05,0.12,0.82),
# ═══════════════════════════════════════════════════════════════════════
# AUSTRIA
# ═══════════════════════════════════════════════════════════════════════
norm("Patrick Pentz"):      s("Patrick Pentz","Bayer Leverkusen","Bundesliga",5,5,450,0.00,0.00,0.00,0.0,1.00),
norm("Alexander Schlager"): s("Alexander Schlager","LASK","Other",24,24,2160,0.00,0.00,0.00,0.0,1.00),
norm("David Alaba"):        s("David Alaba","Real Madrid","LaLiga",0,0,0,0.06,0.07,0.05,0.12,0.00),
norm("Stefan Posch"):       s("Stefan Posch","Bologna","SerieA",24,20,1800,0.05,0.05,0.04,0.09,0.83),
norm("Kevin Danso"):        s("Kevin Danso","Lens","Ligue1",22,19,1710,0.05,0.04,0.04,0.09,0.86),
norm("Gernot Trauner"):     s("Gernot Trauner","Feyenoord","Other",22,19,1710,0.05,0.04,0.04,0.08,0.86),
norm("Marcel Sabitzer"):    s("Marcel Sabitzer","Man Utd","PL",26,20,1800,0.09,0.10,0.09,0.22,0.77),
norm("Konrad Laimer"):      s("Konrad Laimer","Bayern Munich","Bundesliga",26,18,1620,0.07,0.09,0.06,0.16,0.69),
norm("Christoph Baumgartner"): s("Christoph Baumgartner","RB Leipzig","Bundesliga",24,20,1800,0.10,0.12,0.09,0.24,0.83),
norm("Nicolas Seiwald"):    s("Nicolas Seiwald","RB Leipzig","Bundesliga",26,22,1980,0.06,0.07,0.05,0.14,0.85),
norm("Romano Schmid"):      s("Romano Schmid","Werder Bremen","Bundesliga",26,22,1980,0.08,0.10,0.08,0.20,0.85),
norm("Patrick Wimmer"):     s("Patrick Wimmer","Wolfsburg","Bundesliga",24,20,1800,0.10,0.10,0.09,0.24,0.83),
norm("Michael Gregoritsch"):s("Michael Gregoritsch","Freiburg","Bundesliga",22,16,1440,0.20,0.08,0.18,0.50,0.73),
norm("Marko Arnautovic"):   s("Marko Arnautovic","Inter Milan","SerieA",22,8,720,0.24,0.10,0.22,0.55,0.36),
norm("Andreas Weimann"):    s("Andreas Weimann","West Brom","Other",28,24,2160,0.20,0.12,0.18,0.48,0.86),
# ═══════════════════════════════════════════════════════════════════════
# SCOTLAND
# ═══════════════════════════════════════════════════════════════════════
norm("Craig Gordon"):       s("Craig Gordon","Hearts","Other",26,26,2340,0.00,0.00,0.00,0.0,1.00),
norm("Angus Gunn"):         s("Angus Gunn","Norwich","Other",28,28,2520,0.00,0.00,0.00,0.0,1.00),
norm("Andrew Robertson"):   s("Andrew Robertson","Liverpool","PL",24,22,1980,0.06,0.12,0.05,0.10,0.92),
norm("Kieran Tierney"):     s("Kieran Tierney","Arsenal","PL",18,14,1260,0.05,0.10,0.04,0.09,0.78),
norm("John Souttar"):       s("John Souttar","Rangers","Other",22,20,1800,0.04,0.03,0.04,0.08,0.91),
norm("Anthony Ralston"):    s("Anthony Ralston","Celtic","Other",26,22,1980,0.05,0.07,0.05,0.09,0.85),
norm("Ryan Jack"):          s("Ryan Jack","Rangers","Other",22,18,1620,0.05,0.06,0.05,0.12,0.82),
norm("Stuart Armstrong"):   s("Stuart Armstrong","Southampton","PL",24,18,1620,0.08,0.09,0.07,0.18,0.75),
norm("John McGinn"):        s("John McGinn","Aston Villa","PL",26,22,1980,0.10,0.10,0.09,0.24,0.85),
norm("Billy Gilmour"):      s("Billy Gilmour","Brighton","PL",22,16,1440,0.05,0.08,0.05,0.12,0.73),
norm("Ryan Christie"):      s("Ryan Christie","Bournemouth","PL",24,18,1620,0.08,0.09,0.07,0.18,0.75),
norm("Callum McGregor"):    s("Callum McGregor","Celtic","Other",26,24,2160,0.07,0.09,0.06,0.16,0.92),
norm("Scott McTominay"):    s("Scott McTominay","Napoli","SerieA",28,24,2160,0.12,0.10,0.12,0.28,0.86),
norm("Che Adams"):          s("Che Adams","Torino","SerieA",24,18,1620,0.20,0.10,0.18,0.50,0.75),
norm("Lyndon Dykes"):       s("Lyndon Dykes","QPR","Other",26,22,1980,0.18,0.08,0.16,0.44,0.85),
norm("Lawrence Shankland"): s("Lawrence Shankland","Hearts","Other",26,24,2160,0.32,0.10,0.30,0.75,0.92),
norm("Aaron Hickey"):       s("Aaron Hickey","Brentford","PL",24,20,1800,0.06,0.08,0.05,0.11,0.83),
# ═══════════════════════════════════════════════════════════════════════
# NORWAY
# ═══════════════════════════════════════════════════════════════════════
norm("Orjan Nyland"):       s("Orjan Nyland","Inter Milan","SerieA",4,4,360,0.00,0.00,0.00,0.0,1.00),
norm("Kristoffer Ajer"):    s("Kristoffer Ajer","Brentford","PL",24,22,1980,0.04,0.04,0.04,0.08,0.92),
norm("Leo Ostigard"):       s("Leo Ostigard","Napoli","SerieA",18,14,1260,0.04,0.03,0.04,0.08,0.78),
norm("Birger Meling"):      s("Birger Meling","Rennes","Ligue1",22,18,1620,0.05,0.07,0.04,0.08,0.82),
norm("Martin Odegaard"):    s("Martin Odegaard","Arsenal","PL",20,18,1620,0.12,0.16,0.11,0.30,0.90),
norm("Sander Berge"):       s("Sander Berge","Fulham","PL",24,20,1800,0.06,0.07,0.06,0.14,0.83),
norm("Mathias Normann"):    s("Mathias Normann","Watford","Other",24,20,1800,0.07,0.08,0.06,0.16,0.83),
norm("Antonio Nusa"):       s("Antonio Nusa","Club Brugge","Other",25,22,1980,0.14,0.14,0.12,0.35,0.88),
norm("Mohamed Elyounoussi"):s("Mohamed Elyounoussi","Southampton","PL",20,14,1260,0.12,0.10,0.10,0.28,0.70),
norm("Fredrik Aursnes"):    s("Fredrik Aursnes","Benfica","Other",26,22,1980,0.07,0.08,0.06,0.16,0.85),
norm("Alexander Sorloth"):  s("Alexander Sorloth","Atletico Madrid","LaLiga",26,18,1620,0.26,0.10,0.24,0.62,0.69),
norm("Joshua King"):        s("Joshua King","Besiktas","Other",22,18,1620,0.20,0.09,0.18,0.48,0.82),
norm("Joergen-Strand Larsen"): s("Joergen-Strand Larsen","Celta Vigo","LaLiga",24,20,1800,0.24,0.09,0.22,0.56,0.83),
norm("Kristian Thorstvedt"):s("Kristian Thorstvedt","Sassuolo","SerieA",22,18,1620,0.10,0.10,0.09,0.24,0.82),
norm("Ola Solbakken"):      s("Ola Solbakken","Roma","SerieA",18,10,900,0.12,0.09,0.10,0.26,0.56),
}

# ── Load + merge ──────────────────────────────────────────────────────────────
with open("data/manual_stats.json") as f:
    existing = json.load(f)

before = len(existing)
for k, v in NEW.items():
    if k not in existing:          # don't overwrite existing entries
        existing[k] = v
        existing[k]["norm_name"] = k

print(f"Before: {before}  Added: {len(existing)-before}  Total: {len(existing)}")

with open("data/manual_stats.json", "w") as f:
    json.dump(existing, f, indent=2, ensure_ascii=False)
print("Saved → data/manual_stats.json")
