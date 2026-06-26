#!/usr/bin/env python3
"""
Claude Usage Widget per Windows
=================================
Widget flottante always-on-top con Session (5h) e Quota Settimanale.

AUTH — supporta DUE metodi, scegli quello che preferisci:

  Metodo A – sessionKey (raccomandato, zero installazioni)
    1. Apri Edge/Chrome e vai su claude.ai (già loggato)
    2. Premi F12 → Application → Storage → Cookies → https://claude.ai
    3. Copia il valore di  sessionKey  (inizia con sk-ant-sid01-...)
    4. Incollalo nel campo "sessionKey" del dialog di setup

  Metodo B – OAuth token (se hai già eseguito claude login)
    Il widget legge ~/.claude/.credentials.json automaticamente.
    Oppure incolla il token sk-ant-oat01-... nel campo apposito.

Dipendenze:
    pip install requests
    (tkinter è già incluso in Python standard)
"""

import tkinter as tk
import threading
import json
import os
import sys
import re
import webbrowser
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "requests", "-q"])
    import requests

# ── Endpoint ──────────────────────────────────────────────────────────────────
OAUTH_URL    = "https://api.anthropic.com/api/oauth/usage"
BETA_HEADER  = "oauth-2025-04-20"
ORGS_URL     = "https://claude.ai/api/organizations"

CREDS_FILE   = os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")
CFG_FILE     = os.path.join(os.path.expanduser("~"), ".claude_usage_widget.json")
REFRESH_SEC     = 300
CTX_REFRESH_SEC = 60
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
CTX_MAX_TOKENS  = 200_000

# ── Tema ──────────────────────────────────────────────────────────────────────
C = dict(
    bg      = "#0d0d1a",
    bg2     = "#191930",
    fg      = "#e2e2e2",
    accent  = "#e88c30",
    gray    = "#555",
    green   = "#22c55e",
    yellow  = "#f59e0b",
    red     = "#ef4444",
    blue    = "#3b82f6",
    purple  = "#a78bfa",
    track   = "#252540",
)

WIN_W = 264

# ── Auth helpers ──────────────────────────────────────────────────────────────

def _load_cfg() -> dict:
    try:
        with open(CFG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_cfg(data: dict):
    with open(CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_credentials() -> dict:
    """
    Restituisce un dict con le chiavi trovate:
      - 'oauth'   : token Bearer  (sk-ant-oat01-...)
      - 'session' : session key   (sk-ant-sid01-...)
    """
    result = {}

    # 1) file di configurazione locale del widget
    cfg = _load_cfg()
    if cfg.get("session_key"):
        result["session"] = cfg["session_key"]
    if cfg.get("oauth_token"):
        result["oauth"] = cfg["oauth_token"]

    # 2) credenziali di Claude Code CLI  (~/.claude/.credentials.json)
    if not result.get("oauth"):
        try:
            with open(CREDS_FILE, encoding="utf-8") as f:
                d = json.load(f)
            oauth_obj = d.get("claudeAiOauth") or d.get("oauth") or {}
            t = oauth_obj.get("accessToken") or d.get("accessToken") or ""
            if t:
                result["oauth"] = t
        except Exception:
            pass

    return result

# ── Fetch ─────────────────────────────────────────────────────────────────────

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")


def _fetch_with_oauth(token: str) -> dict:
    """Usa l'endpoint OAuth ufficiale."""
    r = requests.get(
        OAUTH_URL,
        headers={
            "Authorization":  f"Bearer {token}",
            "anthropic-beta": BETA_HEADER,
            "Content-Type":   "application/json",
        },
        timeout=12,
    )
    r.raise_for_status()
    return r.json()


def _fetch_with_session(session_key: str) -> dict:
    """
    Usa il sessionKey cookie per chiamare le API interne di claude.ai.
    Endpoint confermato: GET /api/organizations/{uuid}/usage
    """
    cookies = {"sessionKey": session_key}
    headers = {
        "User-Agent":       UA,
        "Accept":           "application/json, text/plain, */*",
        "Accept-Language":  "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer":          "https://claude.ai/settings/usage",
        "Origin":           "https://claude.ai",
        "sec-fetch-dest":   "empty",
        "sec-fetch-mode":   "cors",
        "sec-fetch-site":   "same-origin",
    }

    # Passo 1: ottieni l'org UUID
    r = requests.get(ORGS_URL, cookies=cookies, headers=headers, timeout=12)
    if r.status_code == 401:
        raise RuntimeError("sessionKey non valido o scaduto (401) — ricopialo da Edge")
    r.raise_for_status()

    body = r.json()
    orgs = body if isinstance(body, list) else body.get("organizations", [body])
    if not orgs:
        raise RuntimeError("Nessuna organizzazione trovata")
    org_uuid = orgs[0]["uuid"]

    # Passo 2: endpoint corretto confermato da estensioni open-source
    usage_url = f"https://claude.ai/api/organizations/{org_uuid}/usage"
    r2 = requests.get(usage_url, cookies=cookies, headers=headers, timeout=12)
    if r2.status_code == 404:
        raise RuntimeError("Endpoint /usage non trovato (404)")
    r2.raise_for_status()
    return r2.json()


def fetch_usage(creds: dict) -> dict:
    """Prova OAuth prima, poi sessionKey."""
    errs = []

    if creds.get("oauth"):
        try:
            return _fetch_with_oauth(creds["oauth"])
        except Exception as e:
            errs.append(f"OAuth: {e}")

    if creds.get("session"):
        try:
            return _fetch_with_session(creds["session"])
        except Exception as e:
            errs.append(f"Session: {e}")

    raise RuntimeError(" | ".join(errs) or "Nessun metodo di autenticazione disponibile")


def fetch_context_window() -> dict | None:
    """
    Legge il .jsonl più recente in ~/.claude/projects/*/
    e restituisce {pct, tokens_used, tokens_max, age_min}
    oppure None se nessuna sessione attiva trovata (>4h).
    """
    try:
        jsonl_files = list(CLAUDE_PROJECTS.glob("*/*.jsonl"))
        if not jsonl_files:
            return None

        latest = max(jsonl_files, key=lambda f: f.stat().st_mtime)
        age_min = (time.time() - latest.stat().st_mtime) / 60
        if age_min > 240:
            return None

        lines = latest.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") == "assistant":
                msg   = obj.get("message") or {}
                usage = msg.get("usage") or {}
                tokens = (
                    int(usage.get("input_tokens") or 0)
                    + int(usage.get("cache_read_input_tokens") or 0)
                    + int(usage.get("cache_creation_input_tokens") or 0)
                )
                if tokens == 0:
                    return None
                return {
                    "pct":         min(tokens / CTX_MAX_TOKENS * 100, 100),
                    "tokens_used": tokens,
                    "tokens_max":  CTX_MAX_TOKENS,
                    "age_min":     int(age_min),
                    "model":       _fmt_model(msg.get("model") or ""),
                }
        return None
    except Exception:
        return None


def _fmt_model(model_id: str) -> str:
    """'claude-sonnet-4-6' → 'Sonnet 4.6',  'claude-haiku-4-5-20251001' → 'Haiku 4.5'"""
    m = re.match(r"claude-(\w+)-(\d+)-(\d+)", model_id)
    if m:
        return f"{m.group(1).capitalize()} {m.group(2)}.{m.group(3)}"
    return model_id

# ── Utilità UI ────────────────────────────────────────────────────────────────

def bar_color(pct: float) -> str:
    if pct >= 85: return C["red"]
    if pct >= 65: return C["yellow"]
    return C["green"]


def fmt_reset(iso_str: str) -> str:
    if not iso_str:
        return ""
    try:
        dt   = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        diff = dt - datetime.now(timezone.utc)
        s    = int(diff.total_seconds())
        if s <= 0:
            return "Reset imminente"
        d, rem = divmod(s, 86400)
        h, rem = divmod(rem, 3600)
        m       = rem // 60
        if d:   return f"Reset tra {d}g {h}h"
        if h:   return f"Reset tra {h}h {m:02d}m"
        return f"Reset tra {m}m"
    except Exception:
        return ""

# ── Widget ─────────────────────────────────────────────────────────────────────

class UsageWidget:

    def __init__(self):
        self.creds     = {}
        self.root      = tk.Tk()
        self._drag_ox  = 0
        self._drag_oy  = 0
        self._bars     = {}
        self._setup_window()
        self._build_ui()
        self._position_window()
        self._start()

    # ── finestra ──────────────────────────────────────────────────────────────

    def _setup_window(self):
        r = self.root
        r.title("Claude Usage")
        r.configure(bg=C["bg"])
        r.attributes("-topmost", True)
        r.attributes("-alpha",   0.94)
        r.overrideredirect(True)
        r.bind("<ButtonPress-1>", self._drag_start)
        r.bind("<B1-Motion>",     self._drag_move)
        r.bind("<Button-3>",      self._ctx_menu)

    def _position_window(self):
        r = self.root
        r.update_idletasks()
        h = r.winfo_reqheight()
        sw = r.winfo_screenwidth()
        sh = r.winfo_screenheight()
        r.geometry(f"{WIN_W}x{h}+{sw - WIN_W - 16}+{sh - h - 52}")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = tk.Frame(self.root, bg=C["bg"], padx=10, pady=8)
        outer.pack(fill=tk.BOTH, expand=True)

        hdr = tk.Frame(outer, bg=C["bg"])
        hdr.pack(fill=tk.X, pady=(0, 8))
        tk.Label(hdr, text="⬡  Claude Usage",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(side=tk.LEFT)
        self._dot = tk.Label(hdr, text="●", font=("Segoe UI", 10),
                              bg=C["bg"], fg=C["gray"])
        self._dot.pack(side=tk.RIGHT)
        gear = tk.Label(hdr, text="⚙", font=("Segoe UI", 10),
                        bg=C["bg"], fg=C["gray"], cursor="hand2")
        gear.pack(side=tk.RIGHT, padx=(0, 6))
        gear.bind("<Button-1>", lambda _: self._show_setup())

        self._bar_frame = tk.Frame(outer, bg=C["bg"])
        self._bar_frame.pack(fill=tk.BOTH, expand=True)

        # Barra Contesto: creata per prima così pack(before=) funziona correttamente
        f, cv, pl, rl, tl = self._make_bar(self._bar_frame, "Contesto", C["purple"])
        self._bars["context"] = (f, cv, pl, rl)
        self._ctx_title_lbl = tl
        f.pack_forget()  # mostrata solo se c'è una sessione attiva

        for key, label, color in [
            ("five_hour",        "Sessione  (5h)",  C["blue"]),
            ("seven_day",        "Settimana",        C["green"]),
            ("seven_day_sonnet", "Sonnet",           C["purple"]),
        ]:
            f, cv, pl, rl, _ = self._make_bar(self._bar_frame, label, color)
            self._bars[key] = (f, cv, pl, rl)
            if key == "seven_day_sonnet":
                f.pack_forget()
            else:
                f.pack(fill=tk.X, pady=(0, 5))

        # Footer: status a sinistra, credits a destra
        footer_frame = tk.Frame(outer, bg=C["bg"])
        footer_frame.pack(fill=tk.X)
        self._status_lbl = tk.Label(footer_frame, text="",
                                    font=("Segoe UI", 7),
                                    bg=C["bg"], fg=C["gray"])
        self._status_lbl.pack(side=tk.LEFT)
        link = tk.Label(footer_frame, text="Felter Roberto",
                        font=("Segoe UI", 7), bg=C["bg"],
                        fg=C["accent"], cursor="hand2")
        link.pack(side=tk.RIGHT)
        tk.Label(footer_frame, text="by ",
                 font=("Segoe UI", 7), bg=C["bg"], fg=C["gray"]
                 ).pack(side=tk.RIGHT)
        link.bind("<Button-1>",
                  lambda _: webbrowser.open("https://www.felter.it"))

    def _make_bar(self, parent, label, color):
        frame = tk.Frame(parent, bg=C["bg"])
        row   = tk.Frame(frame, bg=C["bg"])
        row.pack(fill=tk.X)
        title_lbl = tk.Label(row, text=label, font=("Segoe UI", 8, "bold"),
                              bg=C["bg"], fg="#999", anchor="w")
        title_lbl.pack(side=tk.LEFT)
        pct_lbl = tk.Label(row, text="–%",
                            font=("Segoe UI", 9, "bold"),
                            bg=C["bg"], fg="#ddd")
        pct_lbl.pack(side=tk.RIGHT)
        canvas = tk.Canvas(frame, height=5,
                           bg=C["track"], bd=0, highlightthickness=0)
        canvas._def_color = color
        canvas.pack(fill=tk.X, pady=(2, 1))
        reset_lbl = tk.Label(frame, text="",
                              font=("Segoe UI", 7),
                              bg=C["bg"], fg=C["gray"])
        reset_lbl.pack(anchor=tk.W)
        return frame, canvas, pct_lbl, reset_lbl, title_lbl

    def _draw_bar(self, key, pct, resets_at):
        if key not in self._bars:
            return
        _, canvas, pct_lbl, reset_lbl = self._bars[key]
        color = bar_color(pct)
        pct_lbl.config(text=f"{pct:.0f}%", fg=color)
        canvas.update_idletasks()
        w = canvas.winfo_width()
        if w > 1:
            canvas.delete("all")
            fw = int(w * min(pct, 100) / 100)
            canvas.create_rectangle(0, 0, fw, 5, fill=color, outline="")
        reset_lbl.config(text=fmt_reset(resets_at))

    # ── dati ──────────────────────────────────────────────────────────────────

    def apply_data(self, data: dict):
        def update():
            for key in ("five_hour", "seven_day", "seven_day_sonnet"):
                bucket = data.get(key)
                if bucket is None:
                    self._bars[key][0].pack_forget()
                    continue
                pct = float(bucket.get("utilization") or
                            bucket.get("utilization_pct") or 0)
                rst = (bucket.get("resets_at") or
                       bucket.get("reset_at") or "")
                if key == "seven_day_sonnet":
                    self._bars[key][0].pack(fill=tk.X, pady=(0, 5))
                self._draw_bar(key, pct, rst)

            self._dot.config(fg=C["green"])
            self._status_lbl.config(
                text=f"Aggiornato {datetime.now().strftime('%H:%M')}")
            self._position_window()
        self.root.after(0, update)

    def show_error(self, msg: str):
        self.root.after(0, lambda: (
            self._dot.config(fg=C["red"]),
            self._status_lbl.config(text=f"⚠ {msg[:40]}"),
        ))

    # ── refresh context window ────────────────────────────────────────────────

    def _refresh_context(self):
        ctx = fetch_context_window()
        def update():
            bar_f, bar_cv, bar_pl, bar_rl = self._bars["context"]
            if ctx:
                self._ctx_title_lbl.config(
                    text=f"Contesto  ({ctx['model']})" if ctx["model"] else "Contesto")
                bar_f.pack(fill=tk.X, pady=(0, 5),
                           before=self._bars["five_hour"][0])
                self._draw_bar("context", ctx["pct"], "")
                color = (C["red"] if ctx["pct"] > 85
                         else C["yellow"] if ctx["pct"] > 65
                         else C["green"])
                bar_pl.config(text=f"{ctx['pct']:.0f}%", fg=color)
                bar_rl.config(
                    text=f"{ctx['tokens_used']:,} / {ctx['tokens_max']:,} tk"
                         f"  ·  {ctx['age_min']}m fa")
            else:
                bar_f.pack_forget()
            self._position_window()
        self.root.after(0, update)
        self.root.after(CTX_REFRESH_SEC * 1000, self._refresh_context)

    # ── refresh utilizzo API ──────────────────────────────────────────────────

    def _refresh_once(self):
        self.creds = load_credentials()
        if not self.creds:
            self.show_error("Nessuna auth — apri ⚙ per configurare")
            return
        try:
            data = fetch_usage(self.creds)
            self.apply_data(data)
        except Exception as e:
            self.show_error(str(e)[:40])

    def _refresh_loop(self):
        self._refresh_once()
        while True:
            time.sleep(REFRESH_SEC)
            self._refresh_once()

    def _start(self):
        self.creds = load_credentials()
        if not self.creds:
            self.root.after(200, self._show_setup)
        else:
            threading.Thread(target=self._refresh_loop, daemon=True).start()
        self._refresh_context()  # avvia loop autonomo context window (ogni 60s)

    # ── drag ──────────────────────────────────────────────────────────────────

    def _drag_start(self, e):
        self._drag_ox = e.x
        self._drag_oy = e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + e.x - self._drag_ox
        y = self.root.winfo_y() + e.y - self._drag_oy
        self.root.geometry(f"+{x}+{y}")

    # ── menu ──────────────────────────────────────────────────────────────────

    def _ctx_menu(self, e):
        m = tk.Menu(self.root, tearoff=0,
                    bg=C["bg2"], fg=C["fg"],
                    activebackground=C["bg"],
                    activeforeground=C["accent"],
                    bd=0, relief=tk.FLAT)
        m.add_command(label="🔄  Aggiorna ora",
                      command=lambda: threading.Thread(
                          target=self._refresh_once, daemon=True).start())
        m.add_separator()
        m.add_command(label="⚙  Impostazioni", command=self._show_setup)
        m.add_separator()
        m.add_command(label="✕  Chiudi",       command=self.root.destroy)
        m.post(e.x_root, e.y_root)

    # ── setup ─────────────────────────────────────────────────────────────────

    def _show_setup(self):
        cfg = _load_cfg()
        dlg = tk.Toplevel(self.root)
        dlg.title("Impostazioni – Claude Usage Widget")
        dlg.configure(bg=C["bg"])
        dlg.geometry("420x470")
        dlg.attributes("-topmost", True)
        dlg.resizable(False, False)
        dlg.grab_set()

        pad = tk.Frame(dlg, bg=C["bg"], padx=16, pady=14)
        pad.pack(fill=tk.BOTH, expand=True)

        tk.Label(pad, text="⬡  Configurazione autenticazione",
                 font=("Segoe UI", 11, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(anchor="w", pady=(0, 4))

        # ── Metodo A: sessionKey ──────────────────────────────────────────────
        tk.Label(pad, text="Metodo A — sessionKey  (CONSIGLIATO, zero installazioni)",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["green"]).pack(anchor="w", pady=(6, 2))

        steps_a = [
            "1. Apri Edge (o Chrome) → vai su  claude.ai",
            "2. Premi  F12  →  Application  →  Cookies  →  https://claude.ai",
            "3. Copia il valore di  sessionKey  (inizia con sk-ant-sid01-...)",
        ]
        for s in steps_a:
            tk.Label(pad, text=s, bg=C["bg2"], fg="#ccc",
                     font=("Segoe UI", 8), anchor="w",
                     padx=8, pady=4, wraplength=370,
                     justify=tk.LEFT).pack(fill=tk.X, pady=1)

        tk.Label(pad, text="sessionKey:",
                 bg=C["bg"], fg="#aaa",
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))
        sk_var = tk.StringVar(value=cfg.get("session_key", ""))
        sk_ent = tk.Entry(pad, textvariable=sk_var,
                          font=("Courier New", 8),
                          bg=C["bg2"], fg=C["fg"],
                          insertbackground=C["fg"],
                          relief=tk.FLAT, bd=0)
        sk_ent.pack(fill=tk.X, ipady=6, pady=(2, 0))

        sep = tk.Frame(pad, height=1, bg="#333")
        sep.pack(fill=tk.X, pady=10)

        # ── Metodo B: OAuth token ─────────────────────────────────────────────
        tk.Label(pad, text="Metodo B — OAuth token  (da  claude login  o  claude setup-token)",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg="#aaa").pack(anchor="w", pady=(0, 2))

        tk.Label(pad, text="OAuth token (sk-ant-oat01-... oppure qualsiasi altro token):",
                 bg=C["bg"], fg="#aaa",
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))
        ot_var = tk.StringVar(value=cfg.get("oauth_token", ""))
        ot_ent = tk.Entry(pad, textvariable=ot_var,
                          font=("Courier New", 8),
                          bg=C["bg2"], fg=C["fg"],
                          insertbackground=C["fg"],
                          relief=tk.FLAT, bd=0)
        ot_ent.pack(fill=tk.X, ipady=6, pady=(2, 0))

        msg_lbl = tk.Label(pad, text="",
                           bg=C["bg"], fg=C["red"],
                           font=("Segoe UI", 8))
        msg_lbl.pack(anchor="w", pady=(4, 0))

        def save_and_close():
            sk = sk_var.get().strip()
            ot = ot_var.get().strip()
            if not sk and not ot:
                msg_lbl.config(
                    text="Inserisci almeno uno dei due valori",
                    fg=C["red"])
                return
            new_cfg = dict(cfg)
            if sk: new_cfg["session_key"] = sk
            if ot: new_cfg["oauth_token"] = ot
            _save_cfg(new_cfg)
            self.creds = load_credentials()
            dlg.destroy()
            threading.Thread(target=self._refresh_loop, daemon=True).start()

        tk.Button(pad, text="💾  Salva e aggiorna",
                  command=save_and_close,
                  bg=C["accent"], fg="#000",
                  font=("Segoe UI", 10, "bold"),
                  relief=tk.FLAT, cursor="hand2",
                  padx=10, pady=7).pack(fill=tk.X, pady=(10, 2))

        tk.Button(pad, text="✕  Annulla",
                  command=dlg.destroy,
                  bg=C["bg2"], fg="#aaa",
                  font=("Segoe UI", 9),
                  relief=tk.FLAT, cursor="hand2",
                  padx=10, pady=5).pack(fill=tk.X)

    # ── run ───────────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    UsageWidget().run()
