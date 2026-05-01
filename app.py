import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import pandas as pd
from datetime import datetime

# ──────────────────────────────────────────
# Theme
# ──────────────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ──────────────────────────────────────────
# Colors & fonts
# ──────────────────────────────────────────
C_BG        = "#F5F7FA"
C_CARD      = "#FFFFFF"
C_BORDER    = "#E2E8F0"
C_PRIMARY   = "#1A56DB"
C_PRIMARY_H = "#1E429F"
C_SUCCESS   = "#057A55"
C_ERROR     = "#E02424"
C_WARN      = "#D97706"
C_TEXT      = "#111928"
C_MUTED     = "#6B7280"

# ──────────────────────────────────────────
# Pipeline logic (all 5 stages)
# ──────────────────────────────────────────
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

def run_pipeline(inv_path, kor_path, out_path, log):
    log("📂 Loading 1-invest.csv …")
    inv = pd.read_csv(inv_path)
    log("📂 Loading 1-korxona (Excel) …")
    kor = pd.read_excel(kor_path)

    for c in ["section","g2","g12","g13","g14","g15","g17","g18","g4","g5","g6"]:
        inv[c] = pd.to_numeric(inv[c], errors="coerce")
    kor["g1"]    = pd.to_numeric(kor["g1"], errors="coerce")
    kor["g3"]    = pd.to_numeric(kor["g3"], errors="coerce")
    kor["soato"] = kor["soato"].astype(str)

    all_frames = []

    # ── SCR1 ──────────────────────────────
    log("⚙️  SCR1 — pipeline (section=3) …")
    df = inv[inv["section"] == 3].copy()
    df["section"]  = 1
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
    s2 = ["davr","okpo","razdel","g3","g9","g5","g7","g2","g10",
          "g12","g13","g14","g15","g18","g11",
          "EdIzm","g7_test","g9_test","g10_test","npah","ehud","akt","tur"]
    df = df[[c for c in s2 if c in df.columns]]
    df["g2"] = df["g2"].astype(str).str.strip()
    keys      = ["okpo","g2","g3","g5","g7","g9","g10","g11"]
    excl      = ["311","321","331","332"]
    mx_excl   = ~df["g2"].isin(excl)
    mx_3x     =  df["g2"].isin(["31","32","33"])
    def agg(data, col, rename=None):
        out = data.groupby(keys, as_index=False, dropna=False)[col].sum(min_count=1)
        return out.rename(columns={col: rename or f"{col}_sum"})
    r1 = agg(df[mx_excl], "g12")
    r2 = agg(df[mx_excl], "g13")
    r3 = agg(df[mx_3x],   "g13", rename="g13_sum2")
    r4 = agg(df[mx_excl], "g14")
    r5 = agg(df[mx_excl], "g15")
    tmp6 = df[mx_3x].groupby(keys, as_index=False, dropna=False).agg(
        g12_s=("g12", lambda x: x.sum(min_count=1)),
        g13_s=("g13", lambda x: x.sum(min_count=1)),
    )
    tmp6["sum_12_13_ayirma"] = tmp6["g12_s"] - tmp6["g13_s"]
    r6 = tmp6[keys + ["sum_12_13_ayirma"]]
    r7 = agg(df[mx_excl], "g18")
    res = r1
    for r in [r2, r3, r4, r5, r6, r7]:
        res = res.merge(r, on=keys, how="outer")
    pt = ["davr","razdel","EdIzm","g7_test","g9_test","g10_test","npah","ehud","akt","tur"]
    pt_cols = [c for c in pt if c in df.columns]
    if pt_cols:
        pt_df = df.groupby(keys, as_index=False, dropna=False)[pt_cols].first()
        res   = res.merge(pt_df, on=keys, how="left")
    ac = ["davr","okpo","razdel","g3","g9","g5","g7","g2","g10","g11",
          "EdIzm","g7_test","g9_test","g10_test","npah","ehud","akt","tur",
          "g12_sum","g13_sum","g13_sum2","g14_sum","g15_sum","sum_12_13_ayirma","g18_sum"]
    res = res[[c for c in ac if c in res.columns]]
    res = res.rename(columns={
        "g3":"ns_name","g9":"SOATO","g5":"country","g7":"OKED",
        "g2":"ns","g10":"ns1","g11":"kurs",
        "g12_sum":"g1","g13_sum":"g2","g13_sum2":"g3",
        "g14_sum":"g4","g15_sum":"g5","sum_12_13_ayirma":"g6",
        "g18_sum":"g8","g7_test":"g7","g9_test":"g9","g10_test":"g10",
    })
    res.columns = res.columns.str.strip()
    for c in ["g1","g2","g6"]:
        res[c] = pd.to_numeric(res[c], errors="coerce").fillna(0)
    res["g7"] = res["g1"] - res["g2"] - res["g6"]
    for c in FINAL_COLS:
        if c not in res.columns: res[c] = None
    all_frames.append(res[FINAL_COLS])
    log(f"   ✓ SCR1 done — {len(res)} rows")

    # ── SCR2 n-tasks ──────────────────────
    log("⚙️  SCR2 — n-tasks (section=3, g12) …")
    N_TASKS = [
        (3,11,301),(3,21,302),(3,22,303),
        (3,[31,32,33],304),(3,[311,321,331],305),
        (3,31,306),(3,32,307),(3,33,308),(3,332,309),
        (3,[23,51,52,60,71,72,73,74,79,80],310),
    ]
    def proc_n(df, sv, g2f, nsv):
        mask = (df["section"]==sv) & (df["g2"].isin(g2f) if isinstance(g2f,list) else df["g2"]==g2f)
        r = df[mask].groupby(["okpo","g9","section"],as_index=False)["g12"].sum()
        r = r.rename(columns={"g9":"SOATO","section":"razdel","g12":"g1"})
        r["ns"] = nsv
        for c in BLANK_COLS: r[c] = ""
        return r[FINAL_COLS]
    for sv,g2f,nsv in N_TASKS:
        all_frames.append(proc_n(inv,sv,g2f,nsv))
    log(f"   ✓ SCR2 done — {len(N_TASKS)} tasks")

    # ── SCR3 p-tasks ──────────────────────
    log("⚙️  SCR3 — p-tasks (section=4, g6) …")
    P_TASKS = [
        (4,"g5",5,"g6",3,319),(4,"g5",4,"g6",3,318),(4,"g5",3,"g6",3,317),
        (4,"g5",2,"g6",3,316),(4,"g5",1,"g6",3,315),(4,"g4",1,"g6",3,314),
        (4,None,None,"g6",3,313),
    ]
    def proc_p(df, sv, fc, fv, sc, ro, no):
        mask = df["section"]==sv
        if fc: mask &= df[fc]==fv
        r = df[mask].groupby(["okpo","g3"],as_index=False).agg({sc:"sum"})
        r = r.rename(columns={"g3":"SOATO",sc:"g1"})
        r["razdel"]=ro; r["ns"]=no
        for c in BLANK_COLS:
            if c not in r.columns: r[c]=None
        return r[FINAL_COLS]
    for sv,fc,fv,sc,ro,no in P_TASKS:
        all_frames.append(proc_p(inv,sv,fc,fv,sc,ro,no))
    log(f"   ✓ SCR3 done — {len(P_TASKS)} tasks")

    # ── SCR4 k-tasks ──────────────────────
    log("⚙️  SCR4 — k-tasks (1-korxona) …")
    K_TASKS = [
        (5,114,2,201),(5,115,2,203),(9,181,2,203),
        (9,183,31,311),(9,184,31,312),(9,185,31,313),(9,186,31,314),
    ]
    def proc_k(df, sv, g1v, ro, no):
        f = df[(df["section"]==sv)&(df["g1"]==g1v)].copy()
        f["SOATO"] = f["soato"].str[:7]
        r = f.groupby(["okpo","SOATO"],as_index=False)["g3"].sum()
        r = r.rename(columns={"g3":"g1"})
        r["razdel"]=ro; r["ns"]=no
        for c in FINAL_COLS:
            if c not in r.columns: r[c]=None
        return r[FINAL_COLS]
    for sv,g1v,ro,no in K_TASKS:
        all_frames.append(proc_k(kor,sv,g1v,ro,no))
    log(f"   ✓ SCR4 done — {len(K_TASKS)} tasks")

    # ── SCR5 t-tasks ──────────────────────
    log("⚙️  SCR5 — t-tasks (section=3, g13/g17/g18) …")
    T_TASKS = [
        (3,80,"g17",402,4),(3,80,"g18",403,4),
        (3,51,"g13",404,4),(3,52,"g13",405,4),(3,23,"g13",407,4),
        (3,60,"g13",408,4),(3,73,"g13",409,4),(3,74,"g13",410,4),
        (3,71,"g13",411,4),(3,72,"g13",412,4),(3,79,"g13",413,4),
    ]
    def proc_t(df, sv, g2v, sc, nsv, rv):
        f = df[(df["section"]==sv)&(df["g2"]==g2v)]
        r = f.groupby(["okpo","g9"],as_index=False)[sc].sum()
        r = r.rename(columns={"g9":"SOATO",sc:"g1"})
        r["ns"]=nsv; r["razdel"]=rv
        for c in BLANK_COLS: r[c]=""
        return r[FINAL_COLS]
    for sv,g2v,sc,nsv,rv in T_TASKS:
        all_frames.append(proc_t(inv,sv,g2v,sc,nsv,rv))
    log(f"   ✓ SCR5 done — {len(T_TASKS)} tasks")

    # ── Concat & save ─────────────────────
    log("💾 Concatenating and saving …")
    final = pd.concat(all_frames, ignore_index=True)
    final.to_csv(out_path, index=False, encoding="utf-8-sig")
    log(f"✅ Done! {len(final):,} rows saved → {os.path.basename(out_path)}")
    return len(final)


# ──────────────────────────────────────────
# GUI
# ──────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("1-Invest Data Processor")
        self.geometry("780x680")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)

        self.inv_path = ctk.StringVar()
        self.kor_path = ctk.StringVar()
        self.out_path = ctk.StringVar()
        self.running  = False

        self._build_ui()

    # ── UI construction ───────────────────
    def _build_ui(self):
        # ── Header / logo ─────────────────
        hdr = ctk.CTkFrame(self, fg_color=C_PRIMARY, corner_radius=0, height=80)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr,
            text="UZSTAT",
            font=ctk.CTkFont(family="Arial", size=26, weight="bold"),
            text_color="#FFFFFF"
        ).pack(side="left", padx=28, pady=0)

        ctk.CTkLabel(
            hdr,
            text="1-Invest Data Processing System",
            font=ctk.CTkFont(family="Arial", size=13),
            text_color="#BFD7FF"
        ).pack(side="left", padx=4)

        ctk.CTkLabel(
            hdr,
            text="O'zbekiston Respublikasi Davlat Statistika Qo'mitasi",
            font=ctk.CTkFont(family="Arial", size=10),
            text_color="#93C5FD"
        ).pack(side="right", padx=20)

        # ── Main content ──────────────────
        body = ctk.CTkFrame(self, fg_color=C_BG)
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # ── File inputs card ──────────────
        self._card_label(body, "📁  Input Files")
        card1 = self._card(body)

        self._file_row(card1, "1-invest.csv",   self.inv_path,
                       [("CSV files","*.csv"),("All","*.*")], row=0)
        self._file_row(card1, "1-korxona (xlsx)", self.kor_path,
                       [("Excel/CSV","*.xlsx *.csv"),("All","*.*")], row=1)

        # ── Output card ───────────────────
        self._card_label(body, "💾  Output File")
        card2 = self._card(body)
        self._out_row(card2)

        # ── Run button ────────────────────
        self.run_btn = ctk.CTkButton(
            body,
            text="▶  Run Pipeline",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=46,
            corner_radius=10,
            fg_color=C_PRIMARY,
            hover_color=C_PRIMARY_H,
            command=self._on_run
        )
        self.run_btn.pack(fill="x", pady=(14, 4))

        # ── Progress bar ──────────────────
        self.progress = ctk.CTkProgressBar(body, height=6, corner_radius=4)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 14))

        # ── Log card ──────────────────────
        self._card_label(body, "📋  Log")
        log_card = self._card(body, expand=True)

        self.log_box = ctk.CTkTextbox(
            log_card,
            font=ctk.CTkFont(family="Courier", size=12),
            fg_color="#F8FAFC",
            text_color=C_TEXT,
            border_width=0,
            wrap="word",
            state="disabled"
        )
        self.log_box.pack(fill="both", expand=True, padx=2, pady=2)

        # ── Status bar ────────────────────
        self.status_var = ctk.StringVar(value="Ready")
        sb = ctk.CTkFrame(self, fg_color=C_BORDER, height=28, corner_radius=0)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)
        ctk.CTkLabel(sb, textvariable=self.status_var,
                     font=ctk.CTkFont(size=11), text_color=C_MUTED).pack(side="left", padx=12)

    # ── Helper: section label ─────────────
    def _card_label(self, parent, text):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_MUTED
        ).pack(anchor="w", pady=(4, 2))

    # ── Helper: card frame ────────────────
    def _card(self, parent, expand=False):
        f = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=10,
                         border_width=1, border_color=C_BORDER)
        f.pack(fill="both", expand=expand, pady=(0, 10))
        return f

    # ── Helper: file browse row ───────────
    def _file_row(self, parent, label, var, ftypes, row):
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.pack(fill="x", padx=14, pady=8)

        ctk.CTkLabel(fr, text=label, width=160,
                     font=ctk.CTkFont(size=12), text_color=C_TEXT,
                     anchor="w").pack(side="left")

        entry = ctk.CTkEntry(fr, textvariable=var, height=34,
                             placeholder_text="Click Browse to select file…",
                             font=ctk.CTkFont(size=11))
        entry.pack(side="left", fill="x", expand=True, padx=(8, 8))

        ctk.CTkButton(
            fr, text="Browse", width=80, height=34,
            corner_radius=8,
            fg_color="#EEF2FF", hover_color="#E0E7FF",
            text_color=C_PRIMARY, font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda v=var, ft=ftypes: self._browse(v, ft)
        ).pack(side="left")

    # ── Helper: output row ────────────────
    def _out_row(self, parent):
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.pack(fill="x", padx=14, pady=8)

        ctk.CTkLabel(fr, text="Save as (.csv)", width=160,
                     font=ctk.CTkFont(size=12), text_color=C_TEXT,
                     anchor="w").pack(side="left")

        entry = ctk.CTkEntry(fr, textvariable=self.out_path, height=34,
                             placeholder_text="output.csv",
                             font=ctk.CTkFont(size=11))
        entry.pack(side="left", fill="x", expand=True, padx=(8, 8))

        ctk.CTkButton(
            fr, text="Browse", width=80, height=34,
            corner_radius=8,
            fg_color="#EEF2FF", hover_color="#E0E7FF",
            text_color=C_PRIMARY, font=ctk.CTkFont(size=11, weight="bold"),
            command=self._browse_save
        ).pack(side="left")

    # ── File dialogs ──────────────────────
    def _browse(self, var, ftypes):
        p = filedialog.askopenfilename(filetypes=ftypes)
        if p:
            var.set(p)
            # Auto-set output path next to input
            if not self.out_path.get():
                d = os.path.dirname(p)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.out_path.set(os.path.join(d, f"output_{ts}.csv"))

    def _browse_save(self):
        p = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV","*.csv"),("All","*.*")]
        )
        if p:
            self.out_path.set(p)

    # ── Logging ───────────────────────────
    def _log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.status_var.set(msg[:80])
        self.update_idletasks()

    # ── Run ───────────────────────────────
    def _on_run(self):
        if self.running:
            return

        inv = self.inv_path.get().strip()
        kor = self.kor_path.get().strip()
        out = self.out_path.get().strip()

        if not inv or not os.path.exists(inv):
            messagebox.showerror("Missing file", "Please select a valid 1-invest.csv file.")
            return
        if not kor or not os.path.exists(kor):
            messagebox.showerror("Missing file", "Please select a valid 1-korxona file.")
            return
        if not out:
            messagebox.showerror("Missing path", "Please specify an output file path.")
            return

        self.running = True
        self.run_btn.configure(state="disabled", text="⏳  Running…")
        self.progress.configure(mode="indeterminate")
        self.progress.start()

        # Clear log
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        self._log(f"▶ Starting pipeline  [{datetime.now().strftime('%H:%M:%S')}]")
        self._log(f"   invest  : {os.path.basename(inv)}")
        self._log(f"   korxona : {os.path.basename(kor)}")
        self._log(f"   output  : {os.path.basename(out)}")
        self._log("─" * 55)

        def worker():
            try:
                n = run_pipeline(inv, kor, out, self._log)
                self.after(0, lambda: self._on_done(n, out))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, n_rows, out_path):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(1.0)
        self.running = False
        self.run_btn.configure(state="normal", text="▶  Run Pipeline")
        self._log("─" * 55)
        self._log(f"🎉  Pipeline complete — {n_rows:,} total rows")
        self._log(f"📄  Saved → {out_path}")
        self.status_var.set(f"✓ Done — {n_rows:,} rows saved")
        messagebox.showinfo("Done", f"Pipeline finished!\n\n{n_rows:,} rows saved to:\n{out_path}")

    def _on_error(self, err):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(0)
        self.running = False
        self.run_btn.configure(state="normal", text="▶  Run Pipeline")
        self._log(f"❌  ERROR: {err}")
        self.status_var.set(f"Error: {err[:60]}")
        messagebox.showerror("Error", f"Pipeline failed:\n\n{err}")


if __name__ == "__main__":
    app = App()
    app.mainloop()