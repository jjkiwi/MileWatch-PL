"""MileWatch PL - aplikacja desktop (Tkinter, biblioteka standardowa).

Jedno okno, "jedno klikniecie":
  * przycisk "Odswiez promocje"  -> uruchamia darmowy scraping w tle,
  * filtry typ / partner / region + wyszukiwarka,
  * podwojny klik na promocji      -> otwiera zrodlo w przegladarce,
  * przycisk "Eksportuj / Udostepnij" -> zapisuje samodzielny plik HTML
    (mozna go wyslac na inne urzadzenie albo wrzucic na GitHub Pages).

Nie wymaga zadnego klucza API. Uruchom:  python gui.py
"""

import os
import shutil
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import Tk, ttk, StringVar, BooleanVar, messagebox, filedialog

import storage
import export_html
from digest import is_relevant
from sources import load_profile
from run import run_pipeline

TYPE_LABELS = {
    "buy_miles": "kup mile",
    "partner_bonus": "bonus partnera",
    "mileage_bargain": "okazja milowa",
    "card": "karta",
    "other": "inne",
    "error_fare": "BLAD CENOWY",
    "great_deal": "tani lot / mega",
    "business_class": "tania biznes",
}

# Kategorie "perelek" - wyrozniane kolorem i sortowane na gore listy.
PERLY = {"error_fare", "great_deal", "business_class"}


class MileWatchApp:
    def __init__(self, root):
        self.root = root
        self.profile = load_profile()
        self.all_promos = []
        self.busy = False
        self._typ_map = {}
        self._row_to_promo = {}

        root.title("MileWatch PL - promocje Miles & More")
        root.geometry("960x600")
        root.minsize(720, 420)

        self._build_toolbar()
        self._build_filters()
        self._build_table()
        self._build_statusbar()

        self.reload_from_db()

    # --- UI ------------------------------------------------------------------

    def _build_toolbar(self):
        bar = ttk.Frame(self.root, padding=(10, 8))
        bar.pack(fill="x")
        ttk.Label(bar, text="MileWatch PL", font=("", 14, "bold")).pack(side="left")
        self.export_btn = ttk.Button(bar, text="Eksportuj / Udostepnij", command=self.on_export)
        self.export_btn.pack(side="right")
        self.refresh_btn = ttk.Button(bar, text="Odswiez promocje", command=self.on_refresh)
        self.refresh_btn.pack(side="right", padx=(0, 8))

    def _build_filters(self):
        f = ttk.Frame(self.root, padding=(10, 0))
        f.pack(fill="x")

        self.q_var = StringVar()
        self.typ_var = StringVar()
        self.partner_var = StringVar()
        self.region_var = StringVar()
        self.profil_var = BooleanVar(value=False)
        self.perly_var = BooleanVar(value=False)

        ttk.Label(f, text="Szukaj:").pack(side="left")
        q = ttk.Entry(f, textvariable=self.q_var, width=22)
        q.pack(side="left", padx=(4, 10))
        q.bind("<KeyRelease>", lambda e: self.apply_filters())

        self.typ_cb = ttk.Combobox(f, textvariable=self.typ_var, width=14, state="readonly")
        self.partner_cb = ttk.Combobox(f, textvariable=self.partner_var, width=14, state="readonly")
        self.region_cb = ttk.Combobox(f, textvariable=self.region_var, width=14, state="readonly")
        for lbl, cb in (("Typ", self.typ_cb), ("Partner", self.partner_cb), ("Region", self.region_cb)):
            ttk.Label(f, text=lbl + ":").pack(side="left")
            cb.pack(side="left", padx=(4, 10))
            cb.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        ttk.Checkbutton(f, text="tylko z profilu", variable=self.profil_var,
                        command=self.apply_filters).pack(side="left", padx=(0, 8))
        ttk.Checkbutton(f, text="tylko perelki", variable=self.perly_var,
                        command=self.apply_filters).pack(side="left", padx=(0, 10))
        ttk.Button(f, text="Wyczysc", command=self.clear_filters).pack(side="left")

    def _build_table(self):
        wrap = ttk.Frame(self.root, padding=(10, 8))
        wrap.pack(fill="both", expand=True)

        cols = ("typ", "bonus", "tytul", "partner", "wazne_do", "zrodlo")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse")
        headings = {"typ": "Typ", "bonus": "Bonus", "tytul": "Tytul / opis",
                    "partner": "Partner", "wazne_do": "Wazne do", "zrodlo": "Zrodlo"}
        widths = {"typ": 110, "bonus": 60, "tytul": 380, "partner": 110,
                  "wazne_do": 95, "zrodlo": 120}
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="w", stretch=(c == "tytul"))
        self.tree.tag_configure("profil", background="#e8f5e8")
        self.tree.tag_configure("error", background="#ffd9d9")   # blad cenowy - czerwone
        self.tree.tag_configure("tani", background="#ffe6cc")    # tani lot / mega - pomaranczowe
        self.tree.tag_configure("biznes", background="#fff0c2")  # tania biznes - zlote

        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self.on_open_source)

    def _build_statusbar(self):
        self.status_var = StringVar(value="Gotowe.")
        bar = ttk.Frame(self.root, padding=(10, 4))
        bar.pack(fill="x")
        ttk.Label(bar, textvariable=self.status_var, foreground="#666").pack(side="left")
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=140)

    # --- Dane ----------------------------------------------------------------

    def reload_from_db(self):
        conn = storage.connect()
        self.all_promos = storage.get_all_promotions(conn)
        conn.close()
        self._refill_filter_options()
        self.apply_filters()
        self.status_var.set(f"Wczytano {len(self.all_promos)} promocji z bazy.")

    def _refill_filter_options(self):
        typy = sorted({p.typ for p in self.all_promos})
        partnerzy = sorted({p.partner for p in self.all_promos if p.partner})
        regiony = sorted({r for p in self.all_promos for r in p.regiony})
        self.typ_cb["values"] = ["(wszystkie)"] + [TYPE_LABELS.get(t, t) for t in typy]
        self._typ_map = {TYPE_LABELS.get(t, t): t for t in typy}
        self.partner_cb["values"] = ["(wszyscy)"] + partnerzy
        self.region_cb["values"] = ["(wszystkie)"] + regiony

    def _filtered(self):
        q = self.q_var.get().lower().strip()
        typ_label = self.typ_var.get()
        typ = self._typ_map.get(typ_label) if typ_label and typ_label != "(wszystkie)" else ""
        partner = self.partner_var.get()
        if partner in ("", "(wszyscy)"):
            partner = ""
        region = self.region_var.get()
        if region in ("", "(wszystkie)"):
            region = ""
        only_profil = self.profil_var.get()
        only_perly = self.perly_var.get()

        out = []
        for p in self.all_promos:
            if typ and p.typ != typ:
                continue
            if partner and p.partner != partner:
                continue
            if region and region not in p.regiony:
                continue
            if only_profil and not is_relevant(p, self.profile):
                continue
            if only_perly and p.typ not in PERLY:
                continue
            if q and q not in (p.tytul or "").lower() and q not in (p.streszczenie or "").lower():
                continue
            out.append(p)

        # Sortowanie: perelki z preferowanym wylotem na gorze, perelki zagraniczne nizej,
        # reszta na koncu.
        def _rank(p):
            perla = p.typ in PERLY
            zagr = "Wylot zagraniczny" in (p.regiony or [])
            if perla and not zagr:
                return 0
            if perla and zagr:
                return 1
            return 2
        out.sort(key=_rank)
        return out

    def apply_filters(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._row_to_promo = {}
        shown = self._filtered()
        for p in shown:
            bonus = f"+{p.bonus_pct}%" if p.bonus_pct else ""
            if p.typ == "error_fare":
                tag = ("error",)
            elif p.typ == "great_deal":
                tag = ("tani",)
            elif p.typ == "business_class":
                tag = ("biznes",)
            elif is_relevant(p, self.profile):
                tag = ("profil",)
            else:
                tag = ()
            iid = self.tree.insert(
                "", "end",
                values=(TYPE_LABELS.get(p.typ, p.typ), bonus, p.tytul,
                        p.partner or "", p.wazne_do or "", p.zrodlo_nazwa or ""),
                tags=tag,
            )
            self._row_to_promo[iid] = p
        if not self.busy:
            self.status_var.set(f"Pokazano {len(shown)} z {len(self.all_promos)} promocji.")

    def clear_filters(self):
        self.q_var.set("")
        self.typ_var.set("")
        self.partner_var.set("")
        self.region_var.set("")
        self.profil_var.set(False)
        self.perly_var.set(False)
        self.apply_filters()

    # --- Akcje ---------------------------------------------------------------

    def on_open_source(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        promo = self._row_to_promo.get(sel[0])
        if promo and promo.zrodlo_url:
            webbrowser.open(promo.zrodlo_url)

    def on_refresh(self):
        if self.busy:
            return
        self.busy = True
        self.refresh_btn.config(state="disabled")
        self.export_btn.config(state="disabled")
        self.progress.pack(side="right")
        self.progress.start(12)
        self.status_var.set("Pobieram promocje ze zrodel...")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self):
        error = None
        new_count = 0
        try:
            new = run_pipeline(progress=lambda m: self.root.after(0, self.status_var.set, m))
            new_count = len(new)
        except Exception as e:  # noqa: BLE001
            error = str(e)
        self.root.after(0, self._refresh_done, error, new_count)

    def _refresh_done(self, error, new_count):
        self.busy = False
        self.progress.stop()
        self.progress.pack_forget()
        self.refresh_btn.config(state="normal")
        self.export_btn.config(state="normal")
        if error:
            messagebox.showerror("Blad odswiezania", error)
            self.status_var.set("Blad podczas odswiezania.")
            return
        self.reload_from_db()
        self.status_var.set(f"Odswiezono. Nowych promocji: {new_count}.")

    def on_export(self):
        if not self.all_promos:
            messagebox.showinfo("Eksport", "Brak promocji do wyeksportowania. Najpierw odswiez.")
            return
        path = filedialog.asksaveasfilename(
            title="Zapisz eksport jako...",
            defaultextension=".html",
            initialfile="milewatch_promocje.html",
            filetypes=[("Strona HTML", "*.html")],
        )
        if not path:
            return
        export_html.write_export(self.all_promos, self.profile, path)
        self.status_var.set(f"Wyeksportowano do: {path}")
        if messagebox.askyesno("Eksport gotowy", "Plik zapisany. Otworzyc go teraz w przegladarce?"):
            webbrowser.open("file://" + os.path.abspath(path))


def _bootstrap_workdir():
    """Ustawia katalog roboczy obok pliku .exe i zapewnia istnienie config.yaml.

    W wersji spakowanej (PyInstaller) program musi czytac config.yaml i zapisywac baze
    data/ obok pliku .exe, a nie w katalogu tymczasowym. W trybie deweloperskim nie zmienia nic.
    """
    if getattr(sys, "frozen", False):
        app_dir = os.path.dirname(sys.executable)
        os.chdir(app_dir)
        cfg = os.path.join(app_dir, "config.yaml")
        if not os.path.exists(cfg):
            bundled = os.path.join(getattr(sys, "_MEIPASS", app_dir), "config.yaml")
            if os.path.exists(bundled):
                shutil.copy(bundled, cfg)


def main():
    _bootstrap_workdir()
    root = Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    MileWatchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
