#!/usr/bin/env python3
"""Transcribe the FPL Schaden MD1-8 team projection boards (goals + clean sheets)
and validate before writing a board file for build_md_projections.py."""
import json, os, sys
sys.path.insert(0, "/home/user/WCFantasyAssistant")

# ── Clean sheets board: code -> ([md1..md8], stated_total) ────────────────────
CS = {
 "ARS": ([0.41,0.53,0.20,0.39,0.40,0.35,0.40,0.63], 3.31),
 "MCI": ([0.38,0.35,0.47,0.31,0.42,0.19,0.41,0.37], 2.90),
 "LIV": ([0.37,0.40,0.35,0.33,0.33,0.38,0.23,0.45], 2.84),
 "RMA": ([0.37,0.30,0.35,0.34,0.30,0.19,0.49,0.35], 2.69),
 "INT": ([0.17,0.43,0.45,0.30,0.38,0.25,0.26,0.44], 2.68),
 "BAR": ([0.47,0.31,0.20,0.32,0.46,0.21,0.22,0.41], 2.60),
 "POR": ([0.20,0.34,0.32,0.40,0.31,0.19,0.42,0.42], 2.60),
 "PSG": ([0.64,0.13,0.20,0.24,0.36,0.23,0.30,0.39], 2.49),
 "BAY": ([0.40,0.27,0.25,0.23,0.35,0.38,0.21,0.39], 2.48),
 "SPO": ([0.37,0.34,0.47,0.32,0.30,0.28,0.21,0.13], 2.42),
 "NAP": ([0.23,0.24,0.32,0.27,0.13,0.40,0.46,0.36], 2.41),
 "ROM": ([0.30,0.23,0.48,0.20,0.18,0.29,0.30,0.42], 2.40),
 "AEK": ([0.39,0.32,0.13,0.25,0.31,0.40,0.37,0.22], 2.39),
 "COM": ([0.32,0.25,0.28,0.32,0.39,0.28,0.26,0.12], 2.22),
 "ATM": ([0.19,0.31,0.27,0.20,0.37,0.21,0.25,0.41], 2.21),
 "MUN": ([0.53,0.20,0.28,0.34,0.19,0.29,0.16,0.22], 2.21),
 "AVL": ([0.28,0.37,0.33,0.12,0.28,0.25,0.28,0.27], 2.18),
 "BET": ([0.28,0.32,0.31,0.18,0.37,0.36,0.21,0.09], 2.12),
 "DOR": ([0.31,0.18,0.40,0.33,0.13,0.24,0.18,0.35], 2.12),
 "LIL": ([0.35,0.14,0.35,0.20,0.15,0.22,0.46,0.24], 2.11),
 "BOD": ([0.05,0.24,0.20,0.37,0.40,0.27,0.25,0.24], 2.02),
 "VIL": ([0.18,0.29,0.11,0.22,0.23,0.49,0.25,0.24], 2.01),
 "STU": ([0.38,0.30,0.21,0.21,0.12,0.33,0.29,0.11], 1.95),
 "SLA": ([0.31,0.39,0.24,0.19,0.26,0.08,0.20,0.25], 1.92),
 "LEN": ([0.28,0.25,0.26,0.35,0.19,0.27,0.16,0.12], 1.88),
 "RBL": ([0.24,0.22,0.12,0.15,0.36,0.16,0.35,0.21], 1.81),
 "PSV": ([0.41,0.15,0.17,0.29,0.09,0.21,0.17,0.24], 1.73),
 "SHK": ([0.13,0.31,0.13,0.21,0.30,0.31,0.16,0.16], 1.71),
 "FEN": ([0.29,0.14,0.27,0.14,0.22,0.28,0.23,0.14], 1.71),
 "FEY": ([0.05,0.30,0.20,0.20,0.26,0.18,0.21,0.23], 1.63),
 "GAL": ([0.19,0.12,0.24,0.24,0.21,0.21,0.25,0.11], 1.57),
 "VIK": ([0.09,0.11,0.14,0.44,0.14,0.25,0.18,0.17], 1.52),
 "SAB": ([0.07,0.28,0.21,0.18,0.13,0.16,0.26,0.10], 1.39),
 "LSK": ([0.18,0.10,0.09,0.34,0.11,0.24,0.06,0.20], 1.32),
 "CLB": ([0.24,0.10,0.28,0.09,0.11,0.14,0.13,0.19], 1.28),
 "SLB": ([0.04,0.13,0.09,0.15,0.16,0.18,0.13,0.09], 0.97),
}

# ── Goals board: code -> ([md1..md8], stated_total) ───────────────────────────
GOALS = {
 "BAY": ([3.53,2.61,1.91,1.92,2.20,3.04,2.14,2.79], 20.14),
 "BAR": ([3.43,2.46,1.87,2.51,2.41,1.93,1.84,2.47], 18.92),
 "LIV": ([1.98,2.68,2.59,2.30,2.57,1.97,1.58,2.53], 18.20),
 "MCI": ([1.88,2.43,2.39,2.25,2.39,1.85,2.16,2.39], 17.74),
 "RMA": ([2.10,1.71,2.49,1.64,2.81,1.25,3.23,2.13], 17.36),
 "INT": ([1.18,2.73,2.39,1.90,2.45,1.70,1.74,2.78], 16.87),
 "PSG": ([3.81,1.25,1.90,1.79,2.02,1.63,1.60,2.59], 16.59),
 "ARS": ([1.71,2.31,1.62,1.98,2.44,1.95,1.82,2.72], 16.55),
 "PSV": ([2.42,1.79,1.34,2.84,1.41,1.86,1.99,2.55], 16.20),
 "STU": ([2.87,2.42,1.55,1.67,1.14,1.78,2.37,1.69], 15.49),
 "MUN": ([3.13,1.39,1.51,1.90,1.43,2.18,1.81,1.69], 15.04),
 "AVL": ([1.68,2.28,2.28,1.33,1.81,1.75,2.03,1.64], 14.80),
 "ATM": ([1.16,1.89,1.82,1.72,2.30,1.83,1.65,2.30], 14.67),
 "SPO": ([1.95,1.62,2.78,1.84,1.96,1.47,1.77,1.16], 14.55),
 "BOD": ([1.08,2.00,1.33,1.89,2.63,1.53,1.65,1.98], 14.09),
 "DOR": ([2.03,1.70,1.84,1.99,1.07,1.63,1.50,1.78], 13.54),
 "RBL": ([1.34,2.26,1.24,1.39,1.94,1.44,2.19,1.74], 13.54),
 "VIL": ([1.36,1.66,1.23,1.69,1.58,2.17,1.73,1.80], 13.22),
 "POR": ([1.14,1.35,2.08,1.54,1.60,1.15,1.87,1.88], 12.61),
 "ROM": ([1.44,1.40,2.88,1.28,1.19,1.49,1.17,1.67], 12.52),
 "NAP": ([1.06,1.44,1.89,1.09,1.01,2.31,1.60,2.07], 12.47),
 "VIK": ([1.13,1.52,1.29,2.01,1.17,2.02,2.06,1.20], 12.40),
 "FEY": ([0.90,1.64,1.36,1.42,1.39,1.62,1.63,1.86], 11.82),
 "BET": ([1.25,1.27,1.87,1.31,2.15,1.49,1.08,1.10], 11.52),
 "FEN": ([1.41,1.17,1.69,1.32,1.42,1.69,1.64,1.06], 11.40),
 "GAL": ([1.17,1.37,1.22,1.86,1.49,1.09,1.84,1.11], 11.15),
 "CLB": ([1.48,1.00,1.60,1.47,1.32,1.09,1.46,1.69], 11.11),
 "AEK": ([1.99,1.38,0.88,1.27,1.12,1.81,1.41,1.25], 11.11),
 "SLA": ([1.49,1.50,1.52,1.11,1.71,1.13,1.02,1.56], 11.04),
 "LIL": ([1.51,0.74,1.66,1.18,1.23,1.30,2.39,1.02], 11.03),
 "SHK": ([1.06,1.33,0.95,1.33,1.76,2.01,1.25,1.25], 10.94),
 "COM": ([1.70,1.43,1.50,1.25,1.38,1.21,1.40,1.06], 10.93),
 "LEN": ([1.38,1.28,1.49,1.35,1.20,1.55,1.05,0.95], 10.25),
 "LSK": ([1.12,1.08,0.89,2.20,1.09,1.51,0.84,1.02], 9.75),
 "SLB": ([0.53,1.40,0.86,1.28,1.17,1.37,0.92,0.96], 8.49),
 "SAB": ([0.74,1.12,1.09,0.96,0.91,0.85,0.92,0.55], 7.14),
}


def check_totals(name, board, tol=0.011):
    """Each row's eight values must sum to the printed Total — a checksum on
    my transcription that the source itself provides."""
    bad = []
    for code, (vals, stated) in board.items():
        if len(vals) != 8:
            bad.append(f"{code}: {len(vals)} values, expected 8")
            continue
        got = round(sum(vals), 2)
        if abs(got - stated) > tol:
            bad.append(f"{code}: values sum to {got}, printed total is {stated} "
                       f"(off by {got - stated:+.2f})")
    print(f"{name}: {len(board)} clubs, {len(board) - len(bad)} rows reconcile "
          f"with their printed total")
    for b in bad:
        print(f"   MISMATCH  {b}")
    return not bad


def main():
    import data.team_stats as ts
    ok = check_totals("clean sheets", CS) & check_totals("goals", GOALS)

    missing = (set(ts.TEAM_NAMES) - set(CS)) | (set(ts.TEAM_NAMES) - set(GOALS))
    print(f"\nclubs not covered by both boards: {sorted(missing) or 'none'}")

    # ── Independent check: a club's clean-sheet odds and its opponent's goals
    # describe the SAME event from two sides. Under Poisson, cs = exp(-lambda_opp).
    # If I have mis-assigned a row to the wrong club, this falls apart.
    print("\nconsistency of the two boards against each other "
          "(cs vs exp(-opponent goals)):")
    import math
    errs = []
    for md in range(1, 9):
        for code in ts.TEAM_NAMES:
            opp = ts.get_md_fixture(md, code)
            if not opp:
                continue
            implied = math.exp(-GOALS[opp][0][md - 1])
            errs.append((abs(CS[code][0][md - 1] - implied), code, opp, md,
                         CS[code][0][md - 1], implied))
    errs.sort(reverse=True)
    mean = sum(e[0] for e in errs) / len(errs)
    print(f"  {len(errs)} club-matchdays | mean |cs - exp(-opp goals)| = {mean:.3f}")
    print("  worst five:")
    for d, code, opp, md, cs, imp in errs[:5]:
        print(f"    {code} MD{md} vs {opp}: board cs {cs:.2f}, "
              f"implied by {opp}'s {GOALS[opp][0][md-1]:.2f} goals {imp:.2f}  (Δ{d:.2f})")

    if not ok:
        sys.exit("\nTranscription does not reconcile — not writing the board.")

    board = {}
    for md in range(1, 9):
        board[str(md)] = {code: {"goals": GOALS[code][0][md - 1],
                                 "cs": CS[code][0][md - 1]}
                          for code in ts.TEAM_NAMES}
    out = "/home/user/WCFantasyAssistant/data/ucl_board_md1_8.json"
    json.dump(board, open(out, "w"), indent=2)
    print(f"\nSaved board -> {out}")


if __name__ == "__main__":
    main()
