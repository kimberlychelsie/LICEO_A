"""Compute the Excel example and compare with LMS logic."""
from decimal import Decimal, ROUND_HALF_UP

# --- EXCEL WORKBOOK DATA (Term1, Row 14 = Dela Cruz, Juan) ---
# Written Works: QUIZ=72, ACT=64, ASS=42  HPS: 85+70+44=199
ww_earned = 72 + 64 + 42   # = 178
ww_hps = 85 + 70 + 44       # = 199
ww_ps = round((ww_earned / ww_hps) * 100, 2)  # Percentage Score
ww_ws = round(ww_ps * 0.20, 2)               # Weighted Score (M12=0.2)

print(f"=== WRITTEN WORKS ===")
print(f"  Earned: {ww_earned}, HPS: {ww_hps}")
print(f"  PS = ({ww_earned}/{ww_hps})*100 = {ww_ps}")
print(f"  WS = {ww_ps} * 0.20 = {ww_ws}")

# Performance Tasks: P=179, A=100, R=98  HPS: 190+100+98=388
pt_earned = 179 + 100 + 98  # = 377
pt_hps = 190 + 100 + 98     # = 388
pt_ps = round((pt_earned / pt_hps) * 100, 2)
pt_ws = round(pt_ps * 0.50, 2)  # S12=0.5

print(f"\n=== PERFORMANCE TASKS ===")
print(f"  Earned: {pt_earned}, HPS: {pt_hps}")
print(f"  PS = ({pt_earned}/{pt_hps})*100 = {pt_ps}")
print(f"  WS = {pt_ps} * 0.50 = {pt_ws}")

# Summative Tests & Term Exam:
# ST1 raw=51, HPS=70 -> WS_ST1 = (51/70)*30 = 21.86
# ST2 raw=38, HPS=50 -> WS_ST2 = (38/50)*30 = 22.8
# TE raw=45.5, HPS=60 -> WS_TE = (45.5/60)*40 = 30.33
st1_raw, st1_hps = 51, 70
st2_raw, st2_hps = 38, 50
te_raw, te_hps = 45.5, 60

ws_st1 = round((st1_raw / st1_hps) * 30, 2)
ws_st2 = round((st2_raw / st2_hps) * 30, 2)
ws_te = round((te_raw / te_hps) * 40, 2)
ps_ste = round(ws_st1 + ws_st2 + ws_te, 2)  # This is the internal percentage (0-100)
ws_ste = round(ps_ste * 0.30, 2)  # AB12=0.3

print(f"\n=== SUMMATIVE TESTS & TERM EXAM ===")
print(f"  ST1: {st1_raw}/{st1_hps} -> WS_ST1 = ({st1_raw}/{st1_hps})*30 = {ws_st1}")
print(f"  ST2: {st2_raw}/{st2_hps} -> WS_ST2 = ({st2_raw}/{st2_hps})*30 = {ws_st2}")
print(f"  TE:  {te_raw}/{te_hps} -> WS_TE = ({te_raw}/{te_hps})*40 = {ws_te}")
print(f"  PS(ST&TE) = WS_ST1 + WS_ST2 + WS_TE = {ps_ste}")
print(f"  WS = {ps_ste} * 0.30 = {ws_ste}")

# Initial Grade
ig = round(ww_ws + pt_ws + ws_ste, 2)
print(f"\n=== INITIAL GRADE ===")
print(f"  IG = WW_WS + PT_WS + STE_WS = {ww_ws} + {pt_ws} + {ws_ste} = {ig}")

# --- TRANSMUTATION TABLE LOOKUP ---
TRANSMUTATION_RANGES = [
    (0.00, 4.67, 60), (4.68, 9.34, 61), (9.35, 14.00, 62),
    (14.01, 18.67, 63), (18.68, 23.34, 64), (23.35, 28.00, 65),
    (28.01, 32.67, 66), (32.68, 37.33, 67), (37.34, 42.00, 68),
    (42.01, 46.66, 69), (46.67, 51.33, 70), (51.34, 56.00, 71),
    (56.01, 60.66, 72), (60.67, 65.33, 73), (65.34, 69.99, 74),
    (70.00, 71.17, 75), (71.18, 72.35, 76), (72.36, 73.53, 77),
    (73.54, 74.71, 78), (74.72, 75.89, 79), (75.90, 77.07, 80),
    (77.08, 78.25, 81), (78.26, 79.43, 82), (79.44, 80.61, 83),
    (80.62, 81.79, 84), (81.80, 82.97, 85), (82.98, 84.15, 86),
    (84.16, 85.33, 87), (85.34, 86.51, 88), (86.52, 87.69, 89),
    (87.70, 88.87, 90), (88.88, 90.05, 91), (90.06, 91.23, 92),
    (91.24, 92.41, 93), (92.42, 93.59, 94), (93.60, 94.77, 95),
    (94.78, 95.95, 96), (95.96, 97.13, 97), (97.14, 98.31, 98),
    (98.32, 99.49, 99), (99.50, 100.00, 100),
]

transmuted = None
for lower, upper, t in TRANSMUTATION_RANGES:
    if lower <= ig <= upper:
        transmuted = t
        break

print(f"  Transmuted Grade = {transmuted}")
print(f"  (Range: {lower:.2f} - {upper:.2f})")

# --- NOW LMS COMPUTATION ---
print(f"\n{'='*60}")
print("=== LMS COMPUTATION (how teacher.py would compute) ===")
print(f"{'='*60}")

# LMS WW:  earned/possible * 100 -> quiz_scores[eid] 
lms_ww_ps = ww_earned / ww_hps * 100
print(f"  WW PS = {ww_earned}/{ww_hps}*100 = {lms_ww_ps:.6f}")

# LMS PT:  earned/possible * 100 -> pt_score
lms_pt_ps = pt_earned / pt_hps * 100
print(f"  PT PS = {pt_earned}/{pt_hps}*100 = {lms_pt_ps:.6f}")

# LMS STE: Each slot: (earned/possible*100) * internal_weight
lms_st1 = (st1_raw / st1_hps * 100) * 0.30
lms_st2 = (st2_raw / st2_hps * 100) * 0.30
lms_te = (te_raw / te_hps * 100) * 0.40
lms_qa_score = max(0, min(100, lms_st1 + lms_st2 + lms_te))
print(f"  ST1 PS = ({st1_raw}/{st1_hps})*100 = {st1_raw/st1_hps*100:.6f}, * 0.30 = {lms_st1:.6f}")
print(f"  ST2 PS = ({st2_raw}/{st2_hps})*100 = {st2_raw/st2_hps*100:.6f}, * 0.30 = {lms_st2:.6f}")
print(f"  TE  PS = ({te_raw}/{te_hps})*100 = {te_raw/te_hps*100:.6f}, * 0.40 = {lms_te:.6f}")
print(f"  QA Score = {lms_qa_score:.6f}")

# LMS Initial Grade: ww_score*w['ww'] + pt_score*w['pt'] + qa_score*w['qa']
# where w['ww']=0.20, w['pt']=0.50, w['qa']=0.30
lms_ig_raw = lms_ww_ps * 0.20 + lms_pt_ps * 0.50 + lms_qa_score * 0.30
# Normalize: Decimal quantize
lms_ig = float(Decimal(str(lms_ig_raw)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
print(f"\n  LMS IG (raw) = {lms_ww_ps:.6f}*0.20 + {lms_pt_ps:.6f}*0.50 + {lms_qa_score:.6f}*0.30")
print(f"             = {lms_ig_raw:.6f}")
print(f"  LMS IG (normalized) = {lms_ig}")

# Find transmuted
lms_transmuted = None
for lower, upper, t in TRANSMUTATION_RANGES:
    if lower <= lms_ig <= upper:
        lms_transmuted = t
        break
print(f"  LMS Transmuted = {lms_transmuted}")

# --- EXCEL RESULT COMPARISON ---
print(f"\n{'='*60}")
print("=== COMPARISON ===")
print(f"{'='*60}")
print(f"  Excel IG: {ig}  |  LMS IG: {lms_ig}  |  MATCH: {ig == lms_ig}")
print(f"  Excel TG: {transmuted}  |  LMS TG: {lms_transmuted}  |  MATCH: {transmuted == lms_transmuted}")

# KEY DIFFERENCE: Rounding
print(f"\n=== ROUNDING ANALYSIS ===")
print(f"  Excel rounds each WS to 2 decimals at each step (ROUND(..., 2))")
print(f"  LMS does NOT round PS/WS intermediates — only normalizes the final IG")
print(f"")
print(f"  Excel: WW_WS = ROUND({ww_ps} * 0.20, 2) = {ww_ws}")
excel_ww_ws_exact = ww_ps * 0.20
print(f"  Exact:                {ww_ps} * 0.20     = {excel_ww_ws_exact}")
print(f"  LMS:   WW contrib    = {lms_ww_ps * 0.20:.6f}")
print(f"")
print(f"  Excel: PT_WS = ROUND({pt_ps} * 0.50, 2) = {pt_ws}")
print(f"  LMS:   PT contrib    = {lms_pt_ps * 0.50:.6f}")
print(f"")
print(f"  Excel: STE_WS = ROUND({ps_ste} * 0.30, 2) = {ws_ste}")
print(f"  LMS:   QA contrib    = {lms_qa_score * 0.30:.6f}")

# Summary worksheet: Final Grade
print(f"\n=== FINAL GRADE (Summary worksheet) ===")
print(f"  Excel: ROUND(AVERAGE(Term1_TG, Term2_TG, Term3_TG), 0)")
print(f"  LMS:   round(sum(avail) / 3, 2) — NOTE: rounds to 2 decimals, NOT 0")
