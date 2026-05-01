import pandas as pd

# ─────────────────────────────────────────
# Load source files once
# ─────────────────────────────────────────
inv = pd.read_csv("1-invest.csv")
# 1-korxona.csv is actually an Excel file (.xlsx) with a .csv extension
kor = pd.read_excel("1-korxona.csv")

# Numeric conversions — invest
inv["section"] = pd.to_numeric(inv["section"], errors="coerce")
inv["g2"]      = pd.to_numeric(inv["g2"],      errors="coerce")
inv["g12"]     = pd.to_numeric(inv["g12"],     errors="coerce")
inv["g13"]     = pd.to_numeric(inv["g13"],     errors="coerce")
inv["g14"]     = pd.to_numeric(inv["g14"],     errors="coerce")
inv["g15"]     = pd.to_numeric(inv["g15"],     errors="coerce")
inv["g17"]     = pd.to_numeric(inv["g17"],     errors="coerce")
inv["g18"]     = pd.to_numeric(inv["g18"],     errors="coerce")
inv["g4"]      = pd.to_numeric(inv["g4"],      errors="coerce")
inv["g5"]      = pd.to_numeric(inv["g5"],      errors="coerce")
inv["g6"]      = pd.to_numeric(inv["g6"],      errors="coerce")

# Numeric conversions — korxona
kor["g1"]    = pd.to_numeric(kor["g1"], errors="coerce")
kor["g3"]    = pd.to_numeric(kor["g3"], errors="coerce")
kor["soato"] = kor["soato"].astype(str)

FINAL_COLS = [
    "davr", "okpo", "razdel", "ns_name", "SOATO", "country", "OKED",
    "ns", "ns1", "EdIzm", "g1", "g2", "g3", "g4", "g5", "g6",
    "g7", "g8", "g9", "g10", "npah", "kurs", "ehud", "akt", "tur"
]

BLANK_COLS = [
    "davr", "ns_name", "country", "OKED", "ns1", "EdIzm",
    "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9", "g10",
    "npah", "kurs", "ehud", "akt", "tur"
]

def add_blanks(result):
    for col in BLANK_COLS:
        if col not in result.columns:
            result[col] = None
    return result[FINAL_COLS]

all_frames = []

# ─────────────────────────────────────────
# SCR1 — pipeline (section==3, multi-stage)
# ─────────────────────────────────────────
print("\n=== SCR1 (pipeline) ===")
df = inv[inv["section"] == 3].copy()
df["section"] = 1
df["davr"]     = 12
df["EdIzm"]    = ""
df["g7_test"]  = ""
df["g9_test"]  = ""
df["g10_test"] = ""
df["npah"]     = 1000
df["ehud"]     = df["g9"].astype(str).str[:4]
df["akt"]      = ""
df["tur"]      = "1-invest"
df = df.rename(columns={"section": "razdel"})

stage2_cols = [
    "davr", "okpo", "razdel",
    "g3", "g9", "g5", "g7", "g2", "g10",
    "g12", "g13", "g14", "g15", "g18", "g11",
    "EdIzm", "g7_test", "g9_test", "g10_test", "npah", "ehud", "akt", "tur"
]
df = df[[c for c in stage2_cols if c in df.columns]]
df["g2"] = df["g2"].astype(str).str.strip()

keys     = ["okpo", "g2", "g3", "g5", "g7", "g9", "g10", "g11"]
excl     = ["311", "321", "331", "332"]
mask_excl = ~df["g2"].isin(excl)
mask_3x   =  df["g2"].isin(["31", "32", "33"])

def agg(data, col, rename=None):
    out = data.groupby(keys, as_index=False, dropna=False)[col].sum(min_count=1)
    return out.rename(columns={col: rename or f"{col}_sum"})

r1 = agg(df[mask_excl], "g12")
r2 = agg(df[mask_excl], "g13")
r3 = agg(df[mask_3x],   "g13", rename="g13_sum2")
r4 = agg(df[mask_excl], "g14")
r5 = agg(df[mask_excl], "g15")
tmp6 = df[mask_3x].groupby(keys, as_index=False, dropna=False).agg(
    g12_s=("g12", lambda x: x.sum(min_count=1)),
    g13_s=("g13", lambda x: x.sum(min_count=1)),
)
tmp6["sum_12_13_ayirma"] = tmp6["g12_s"] - tmp6["g13_s"]
r6 = tmp6[keys + ["sum_12_13_ayirma"]]
r7 = agg(df[mask_excl], "g18")

result = r1
for r in [r2, r3, r4, r5, r6, r7]:
    result = result.merge(r, on=keys, how="outer")

passthrough = ["davr", "razdel", "EdIzm", "g7_test", "g9_test", "g10_test", "npah", "ehud", "akt", "tur"]
pt_cols = [c for c in passthrough if c in df.columns]
if pt_cols:
    pt_df  = df.groupby(keys, as_index=False, dropna=False)[pt_cols].first()
    result = result.merge(pt_df, on=keys, how="left")

agg_cols = [
    "davr", "okpo", "razdel", "g3", "g9", "g5", "g7", "g2", "g10", "g11",
    "EdIzm", "g7_test", "g9_test", "g10_test", "npah", "ehud", "akt", "tur",
    "g12_sum", "g13_sum", "g13_sum2", "g14_sum", "g15_sum", "sum_12_13_ayirma", "g18_sum"
]
result = result[[c for c in agg_cols if c in result.columns]]
result = result.rename(columns={
    "g3": "ns_name", "g9": "SOATO", "g5": "country", "g7": "OKED",
    "g2": "ns", "g10": "ns1", "g11": "kurs",
    "g12_sum": "g1", "g13_sum": "g2", "g13_sum2": "g3",
    "g14_sum": "g4", "g15_sum": "g5", "sum_12_13_ayirma": "g6",
    "g18_sum": "g8", "g7_test": "g7", "g9_test": "g9", "g10_test": "g10",
})
result.columns = result.columns.str.strip()
for col in ["g1", "g2", "g6"]:
    result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0)
result["g7"] = result["g1"] - result["g2"] - result["g6"]
for col in FINAL_COLS:
    if col not in result.columns:
        result[col] = None
scr1 = result[FINAL_COLS]
print(f"  SCR1 rows: {len(scr1)}")
all_frames.append(scr1)

# ─────────────────────────────────────────
# SCR2 — n-tasks (1-invest, section==3, g12)
# ─────────────────────────────────────────
print("\n=== SCR2 (n-tasks) ===")
N_TASKS = [
    (3, 11,                              301),
    (3, 21,                              302),
    (3, 22,                              303),
    (3, [31, 32, 33],                    304),
    (3, [311, 321, 331],                 305),
    (3, 31,                              306),
    (3, 32,                              307),
    (3, 33,                              308),
    (3, 332,                             309),
    (3, [23,51,52,60,71,72,73,74,79,80], 310),
]
def process_n(df, section_val, g2_filter, ns_val):
    mask = (df["section"] == section_val) & (
        df["g2"].isin(g2_filter) if isinstance(g2_filter, list) else df["g2"] == g2_filter
    )
    filtered = df[mask]
    result = filtered.groupby(["okpo", "g9", "section"], as_index=False)["g12"].sum()
    result = result.rename(columns={"g9": "SOATO", "section": "razdel", "g12": "g1"})
    result["ns"] = ns_val
    for col in BLANK_COLS:
        result[col] = ""
    return result[FINAL_COLS]

for i, (sec, g2f, ns) in enumerate(N_TASKS, 1):
    print(f"  [n{i}] section={sec}, g2={g2f}, ns={ns}")
    all_frames.append(process_n(inv, sec, g2f, ns))

# ─────────────────────────────────────────
# SCR3 — p-tasks (1-invest, section==4, g6)
# ─────────────────────────────────────────
print("\n=== SCR3 (p-tasks) ===")
P_TASKS = [
    (4, "g5", 5,    "g6", 3, 319),
    (4, "g5", 4,    "g6", 3, 318),
    (4, "g5", 3,    "g6", 3, 317),
    (4, "g5", 2,    "g6", 3, 316),
    (4, "g5", 1,    "g6", 3, 315),
    (4, "g4", 1,    "g6", 3, 314),
    (4, None, None, "g6", 3, 313),
]
def process_p(df, section_val, filter_col, filter_val, sum_col, razdel_out, ns_out):
    mask = df["section"] == section_val
    if filter_col is not None:
        mask &= df[filter_col] == filter_val
    filtered = df[mask]
    result = filtered.groupby(["okpo", "g3"], as_index=False).agg({sum_col: "sum"})
    result = result.rename(columns={"g3": "SOATO", sum_col: "g1"})
    result["razdel"] = razdel_out
    result["ns"]     = ns_out
    for col in BLANK_COLS:
        if col not in result.columns:
            result[col] = None
    return result[FINAL_COLS]

for i, (sec, fcol, fval, scol, razdel, ns) in enumerate(P_TASKS, 1):
    print(f"  [p{i}] section={sec}, {fcol}={fval}, ns={ns}")
    all_frames.append(process_p(inv, sec, fcol, fval, scol, razdel, ns))

# ─────────────────────────────────────────
# SCR4 — k-tasks (1-korxona)
# ─────────────────────────────────────────
print("\n=== SCR4 (k-tasks) ===")
K_TASKS = [
    (5, 114, 2,  201),
    (5, 115, 2,  203),
    (9, 181, 2,  203),
    (9, 183, 31, 311),
    (9, 184, 31, 312),
    (9, 185, 31, 313),
    (9, 186, 31, 314),
]
def process_k(df, section_val, g1_val, razdel_out, ns_out):
    filtered = df[(df["section"] == section_val) & (df["g1"] == g1_val)].copy()
    filtered["SOATO"] = filtered["soato"].str[:7]
    result = filtered.groupby(["okpo", "SOATO"], as_index=False)["g3"].sum()
    result = result.rename(columns={"g3": "g1"})
    result["razdel"] = razdel_out
    result["ns"]     = ns_out
    for col in FINAL_COLS:
        if col not in result.columns:
            result[col] = None
    return result[FINAL_COLS]

for i, (sec, g1v, razdel, ns) in enumerate(K_TASKS, 1):
    print(f"  [k{i}] section={sec}, g1={g1v}, ns={ns}")
    all_frames.append(process_k(kor, sec, g1v, razdel, ns))

# ─────────────────────────────────────────
# SCR5 — t-tasks (1-invest, section==3, g17/g18/g13)
# ─────────────────────────────────────────
print("\n=== SCR5 (t-tasks) ===")
T_TASKS = [
    (3, 80, "g17", 402, 4),
    (3, 80, "g18", 403, 4),
    (3, 51, "g13", 404, 4),
    (3, 52, "g13", 405, 4),
    (3, 23, "g13", 407, 4),
    (3, 60, "g13", 408, 4),
    (3, 73, "g13", 409, 4),
    (3, 74, "g13", 410, 4),
    (3, 71, "g13", 411, 4),
    (3, 72, "g13", 412, 4),
    (3, 79, "g13", 413, 4),
]
def process_t(df, section_val, g2_val, sum_col, ns_val, razdel_val):
    filtered = df[(df["section"] == section_val) & (df["g2"] == g2_val)]
    result = filtered.groupby(["okpo", "g9"], as_index=False)[sum_col].sum()
    result = result.rename(columns={"g9": "SOATO", sum_col: "g1"})
    result["ns"]     = ns_val
    result["razdel"] = razdel_val
    for col in BLANK_COLS:
        result[col] = ""
    return result[FINAL_COLS]

for i, (sec, g2, scol, ns, razdel) in enumerate(T_TASKS, 1):
    print(f"  [t{i}] section={sec}, g2={g2}, ns={ns}")
    all_frames.append(process_t(inv, sec, g2, scol, ns, razdel))

# ─────────────────────────────────────────
# Concatenate all and save
# ─────────────────────────────────────────
final = pd.concat(all_frames, ignore_index=True)
final.to_csv("output.csv", index=False, encoding="utf-8-sig")
print(f"\n✓ All done. Total rows: {len(final)}")
print(f"  Saved → output.csv")