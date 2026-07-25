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

Nota sicurezza: i token sono salvati IN CHIARO in ~/.claude_usage_widget.json,
protetti solo dall'ACL del profilo utente Windows. Non sincronizzare quel file
su cloud/backup condivisi.

Log: errori e warning in ~/.claude_usage_widget.log (rotazione a ~200 KB).
"""

import tkinter as tk
import threading
import json
import logging
import os
import sys
import re
import webbrowser
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── Logging ───────────────────────────────────────────────────────────────────
# Il widget gira con pythonw (niente console): senza log su file ogni errore
# nei thread o nelle callback Tk sarebbe invisibile.
LOG_FILE = os.path.join(os.path.expanduser("~"), ".claude_usage_widget.log")
log = logging.getLogger("claude_usage")
log.setLevel(logging.WARNING)
try:
    _handler = RotatingFileHandler(LOG_FILE, maxBytes=200_000,
                                   backupCount=1, encoding="utf-8")
    _handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(_handler)
except OSError:
    pass  # file di log non scrivibile: si prosegue senza log

try:
    import requests
except ImportError:
    import subprocess
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "requests", "-q"],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        import requests
        log.warning("Libreria 'requests' mancante: installata automaticamente")
    except Exception:
        log.exception("Installazione automatica di 'requests' fallita")
        from tkinter import messagebox
        _tmp = tk.Tk()
        _tmp.withdraw()
        messagebox.showerror(
            "Claude Usage Widget",
            "La libreria 'requests' non è installata e l'installazione\n"
            "automatica è fallita.\n\n"
            "Esegui:  pip install requests\n"
            "oppure avvia il widget con avvia_widget.bat.")
        sys.exit(1)

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

# Versione del widget. 1.0 = versione pre-compatta (mai numerata esplicitamente),
# 1.1 = modalità compatta, 1.2 = hardening (thread unico, logging, fix minori),
# 1.3 = barra Crediti di utilizzo (extra_usage).
APP_VERSION = "1.3"

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

WIN_W     = 264
# Larghezza compatta: "100%" (32px nel font) + 2×5px di padx del compact_frame =
# margini identici di 5px a sinistra/destra. _position_window mantiene fisso il bordo
# destro corrente, quindi riducendo la larghezza si sposta solo il margine sinistro.
COMPACT_W = 42

# ── Auth helpers ──────────────────────────────────────────────────────────────

def _load_cfg() -> dict:
    try:
        with open(CFG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_cfg(data: dict):
    # Scrittura atomica: un crash a metà json.dump non deve troncare il file
    # (perderebbe i token salvati). Temp nella stessa cartella + os.replace.
    tmp = CFG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, CFG_FILE)

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

# Session condivisa: riusa le connessioni TLS (keep-alive) tra i refresh
_http = requests.Session()


def _fetch_with_oauth(token: str) -> dict:
    """Usa l'endpoint OAuth ufficiale."""
    r = _http.get(
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
    r = _http.get(ORGS_URL, cookies=cookies, headers=headers, timeout=12)
    if r.status_code == 401:
        raise RuntimeError("sessionKey non valido o scaduto (401) — ricopialo da Edge")
    r.raise_for_status()

    body = r.json()
    orgs = body if isinstance(body, list) else body.get("organizations", [body])
    if not orgs:
        raise RuntimeError("Nessuna organizzazione trovata")
    org_uuid = orgs[0].get("uuid") if isinstance(orgs[0], dict) else None
    if not org_uuid:
        raise RuntimeError("Risposta organizations inattesa (manca uuid)")

    # Passo 2: endpoint corretto confermato da estensioni open-source
    usage_url = f"https://claude.ai/api/organizations/{org_uuid}/usage"
    r2 = _http.get(usage_url, cookies=cookies, headers=headers, timeout=12)
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


def _read_tail_lines(path: Path, max_bytes: int = 262_144) -> list[str]:
    """
    Legge solo la coda del file (ultimi max_bytes): i transcript .jsonl di
    Claude Code arrivano a decine di MB e l'ultimo messaggio assistant è
    sempre negli ultimi KB. Evita read_text() dell'intero file ogni 60s.
    """
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - max_bytes))
        data = f.read()
    lines = data.decode("utf-8", errors="ignore").splitlines()
    if size > max_bytes and lines:
        lines = lines[1:]  # la prima riga è quasi certamente troncata
    return lines


def _ctx_max_for(model_id: str) -> int:
    """Finestra contesto del modello: 1M per gli ID con suffisso [1m], 200K default."""
    return 1_000_000 if "[1m]" in model_id else CTX_MAX_TOKENS


def fetch_context_window() -> dict | None:
    """
    Legge il .jsonl più recente in ~/.claude/projects/*/
    e restituisce {pct, tokens_used, tokens_max, age_min, model}
    oppure None se nessuna sessione attiva trovata (>4h).
    """
    try:
        jsonl_files = list(CLAUDE_PROJECTS.glob("*/*.jsonl"))
        if not jsonl_files:
            return None

        latest  = max(jsonl_files, key=lambda f: f.stat().st_mtime)
        age_min = (time.time() - latest.stat().st_mtime) / 60
        if age_min > 240:
            return None

        for line in reversed(_read_tail_lines(latest)):
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
                model_id = msg.get("model") or ""
                ctx_max  = _ctx_max_for(model_id)
                return {
                    "pct":         min(tokens / ctx_max * 100, 100),
                    "tokens_used": tokens,
                    "tokens_max":  ctx_max,
                    "age_min":     int(age_min),
                    "model":       _fmt_model(model_id),
                }
        return None
    except Exception:
        log.exception("Lettura context window fallita")
        return None


def _fmt_model(model_id: str) -> str:
    """
    'claude-sonnet-4-6' → 'Sonnet 4.6',  'claude-haiku-4-5-20251001' → 'Haiku 4.5',
    'claude-fable-5' → 'Fable 5'. Il lookahead (?!\\d) evita di catturare come
    minor la data a 8 cifre (es. 'claude-opus-4-20250514' → 'Opus 4').
    """
    m = re.match(r"claude-(\w+?)-(\d+)(?:-(\d{1,2})(?!\d))?", model_id)
    if not m:
        return model_id
    name = f"{m.group(1).capitalize()} {m.group(2)}"
    return f"{name}.{m.group(3)}" if m.group(3) else name

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


def fmt_money(amount_minor, currency="EUR", exponent=2) -> str:
    """
    202, 'EUR', 2 → '€2,02'. Unità minori → maggiori; virgola decimale (IT).
    Difensivo sui dati API (non fidati): valori null/non numerici → 0,
    exponent forzato in 0..4 (evita 10**n assurdi).
    """
    currency = currency or "EUR"
    sym = {"EUR": "€", "USD": "$", "GBP": "£"}.get(currency, f"{currency} ")
    try:
        exp = max(0, min(int(exponent), 4))
    except (TypeError, ValueError):
        exp = 2
    try:
        val = float(amount_minor or 0) / (10 ** exp)
    except (TypeError, ValueError):
        val = 0.0
    return f"{sym}{val:.{exp}f}".replace(".", ",")

# ── Tooltip ────────────────────────────────────────────────────────────────────

class Tooltip:
    """Tooltip minimale: appare al mouse-over, sparisce all'uscita. Zero dipendenze."""

    def __init__(self, widget, text: str):
        self.widget = widget
        self.text   = text
        self._tip   = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _):
        if self._tip or not self.text:
            return
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tip = tk.Toplevel(self.widget)
        self._tip.overrideredirect(True)
        self._tip.attributes("-topmost", True)
        tk.Label(self._tip, text=self.text,
                 bg=C["bg2"], fg=C["fg"],
                 font=("Segoe UI", 8),
                 padx=6, pady=3, bd=0).pack()
        # posiziona con il bordo destro allineato al widget (numeri right-aligned)
        self._tip.update_idletasks()
        tw = self._tip.winfo_reqwidth()
        x = self.widget.winfo_rootx() + self.widget.winfo_width() - tw
        self._tip.geometry(f"+{x}+{y}")

    def _hide(self, _):
        if self._tip:
            self._tip.destroy()
            self._tip = None


# ── Widget ─────────────────────────────────────────────────────────────────────

class UsageWidget:

    # ordine verticale delle voci + descrizione per il tooltip in modalità compatta
    _KEYS = ["context", "five_hour", "seven_day", "seven_day_sonnet", "credits"]
    _DESC = {
        "context":          "Contesto",
        "five_hour":        "Sessione (5h)",
        "seven_day":        "Settimana",
        "seven_day_sonnet": "Sonnet",
        "credits":          "Crediti",
    }

    def __init__(self):
        self.creds         = {}
        self.root          = tk.Tk()
        self._drag_x0      = 0
        self._drag_y0      = 0
        self._win_x0       = 0
        self._win_y0       = 0
        self._dragging     = False
        self._bars         = {}
        self._compact_lbls = {}
        self._values       = {}   # key -> (pct, visible)
        self._wake         = threading.Event()  # sveglia il refresh loop
        self._loop_started = False               # un solo thread di refresh
        # Angolo di ancoraggio tracciato manualmente (coord. schermo del bordo destro/
        # inferiore). Evita di leggere winfo_x/width al toggle, che su alcuni sistemi
        # (DPI/overrideredirect) arrivano sfasati di un ciclo → posizione oscillante.
        self._anchor_right  = None
        self._anchor_bottom = None
        self._cur_h         = 0
        self.compact       = bool(_load_cfg().get("compact"))
        self._setup_window()
        self._build_ui()
        if self.compact:
            self._outer.pack_forget()
            self._compact_frame.pack(fill=tk.BOTH, expand=True)
        self._sync_compact()
        self._position_window(initial=True)
        self._start()

    # ── finestra ──────────────────────────────────────────────────────────────

    def _setup_window(self):
        r = self.root
        r.title("Claude Usage")
        # Con pythonw i traceback delle callback Tk andrebbero persi: logghiamoli
        r.report_callback_exception = \
            lambda exc, val, tb: log.error("Errore in callback Tk",
                                           exc_info=(exc, val, tb))
        r.configure(bg=C["bg"])
        r.attributes("-topmost", True)
        r.attributes("-alpha",   0.94)
        r.overrideredirect(True)
        r.bind("<ButtonPress-1>", self._drag_start)
        r.bind("<B1-Motion>",     self._drag_move)
        r.bind("<Button-3>",      self._ctx_menu)

    def _position_window(self, initial=False):
        """
        initial=True → primo posizionamento in basso-destra (dimensioni schermo),
        memorizza l'angolo di ancoraggio (bordo destro/inferiore).
        Altrimenti → ricalcola x/y dall'angolo ancorato SALVATO (self._anchor_*),
        NON da winfo_x/width: così il ridimensionamento è deterministico e non oscilla
        (bug DPI/overrideredirect dove winfo_* è sfasato di un ciclo). L'ancora cambia
        solo al drag (vedi _drag_move).
        """
        r = self.root
        r.update_idletasks()
        h = r.winfo_reqheight()
        w = COMPACT_W if self.compact else WIN_W
        if initial or self._anchor_right is None:
            sw = r.winfo_screenwidth()
            sh = r.winfo_screenheight()
            x = sw - w - 16
            y = sh - h - 52
            self._anchor_right  = x + w
            self._anchor_bottom = y + h
        else:
            x = self._anchor_right  - w   # bordo destro ancorato
            y = self._anchor_bottom - h   # bordo inferiore ancorato
        self._cur_h = h
        # Windows + overrideredirect: applicare dimensione e posizione in DUE chiamate
        # geometry() separate. In una sola chiamata la posizione può venire ignorata o
        # applicata a coordinate stale → salto in alto-a-sinistra a giri alterni.
        r.geometry(f"{w}x{h}")
        r.update_idletasks()
        r.geometry(f"+{x}+{y}")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── modalità estesa ────────────────────────────────────────────────
        self._outer = tk.Frame(self.root, bg=C["bg"], padx=10, pady=8)
        self._outer.pack(fill=tk.BOTH, expand=True)
        outer = self._outer

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
        collapse = tk.Label(hdr, text="⧉", font=("Segoe UI", 10),
                            bg=C["bg"], fg=C["gray"], cursor="hand2")
        collapse.pack(side=tk.RIGHT, padx=(0, 6))
        collapse.bind("<Button-1>", lambda _: self._toggle_compact())
        Tooltip(collapse, "Riduci")

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

        # Barra Crediti di utilizzo (extra_usage): mostrata solo se attiva sul piano
        f, cv, pl, rl, _ = self._make_bar(self._bar_frame, "Crediti", C["accent"])
        self._bars["credits"] = (f, cv, pl, rl)
        f.pack_forget()

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

        # ── modalità compatta: solo icona espandi + percentuali ────────────
        # Figlio di root (non di outer) con padding proprio → margini 5px indipendenti.
        self._compact_frame = tk.Frame(self.root, bg=C["bg"], padx=5, pady=8)
        expand = tk.Label(self._compact_frame, text="⛶", font=("Segoe UI", 10),
                          bg=C["bg"], fg=C["gray"], cursor="hand2")
        expand.pack(pady=(0, 4))  # centrato orizzontalmente
        expand.bind("<Button-1>", lambda _: self._toggle_compact())
        Tooltip(expand, "Espandi")
        for key in self._KEYS:
            lbl = tk.Label(self._compact_frame, text="–%",
                           font=("Segoe UI", 10, "bold"),
                           bg=C["bg"], fg="#ddd", anchor="e")
            self._compact_lbls[key] = lbl
            Tooltip(lbl, self._DESC[key])

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

    # ── modalità compatta ───────────────────────────────────────────────────────

    def _toggle_compact(self):
        self.compact = not self.compact
        if self.compact:
            self._outer.pack_forget()
            self._compact_frame.pack(fill=tk.BOTH, expand=True)
        else:
            self._compact_frame.pack_forget()
            self._outer.pack(fill=tk.BOTH, expand=True)
        self._save_compact_state()
        self._sync_compact()
        self._position_window()

    def _save_compact_state(self):
        cfg = _load_cfg()
        cfg["compact"] = self.compact
        _save_cfg(cfg)

    def _sync_compact(self):
        """Allinea i label compatti ai valori correnti, stesso ordine del pieno."""
        # nascondi tutti, poi ri-packa i visibili in ordine (dopo l'icona espandi)
        for lbl in self._compact_lbls.values():
            lbl.pack_forget()
        for key in self._KEYS:
            pct, visible = self._values.get(key, (0, False))
            if visible:
                lbl = self._compact_lbls[key]
                lbl.config(text=f"{pct:.0f}%", fg=bar_color(pct))
                lbl.pack(fill=tk.X, pady=1)

    # ── dati ──────────────────────────────────────────────────────────────────

    def apply_data(self, data: dict):
        def update():
            for key in ("five_hour", "seven_day", "seven_day_sonnet"):
                bucket = data.get(key)
                if bucket is None:
                    self._bars[key][0].pack_forget()
                    self._values[key] = (0, False)
                    continue
                pct = float(bucket.get("utilization") or
                            bucket.get("utilization_pct") or 0)
                rst = (bucket.get("resets_at") or
                       bucket.get("reset_at") or "")
                if key == "seven_day_sonnet":
                    self._bars[key][0].pack(fill=tk.X, pady=(0, 5))
                self._draw_bar(key, pct, rst)
                self._values[key] = (pct, True)

            # Crediti di utilizzo (extra_usage): shape diversa dalle barre standard,
            # gestita a parte. reset_lbl riusato per "€usato / €limite" (come Contesto).
            eu = data.get("extra_usage")
            cred_f, _, _, cred_rl = self._bars["credits"]
            # isinstance: shape non-dict (cambio API) non deve far crashare update().
            # "or": molti campi di questa API arrivano come null espliciti, per cui
            # .get(chiave, default) non basta a coprirli.
            if isinstance(eu, dict) and eu.get("is_enabled"):
                pct = float(eu.get("utilization") or 0)
                cur = eu.get("currency") or "EUR"
                dp  = eu.get("decimal_places")  # null gestito da fmt_money
                cred_f.pack(fill=tk.X, pady=(0, 5))
                self._draw_bar("credits", pct, "")
                cred_rl.config(
                    text=f"{fmt_money(eu.get('used_credits'), cur, dp)} / "
                         f"{fmt_money(eu.get('monthly_limit'), cur, dp)}")
                self._values["credits"] = (pct, True)
            else:
                cred_f.pack_forget()
                self._values["credits"] = (0, False)

            self._dot.config(fg=C["green"])
            self._status_lbl.config(
                text=f"Aggiornato {datetime.now().strftime('%H:%M')}")
            self._sync_compact()
            self._position_window()
        self.root.after(0, update)

    def show_error(self, msg: str):
        self.root.after(0, lambda: (
            self._dot.config(fg=C["red"]),
            self._status_lbl.config(text=f"⚠ {msg[:40]}"),
        ))

    # ── refresh context window ────────────────────────────────────────────────

    def _refresh_context(self):
        # I/O su file (glob + lettura .jsonl) fuori dal thread Tk: sul main
        # thread causava micro-freeze della UI a ogni ciclo da 60s.
        def worker():
            ctx = fetch_context_window()
            self.root.after(0, lambda: self._apply_context(ctx))
        threading.Thread(target=worker, daemon=True).start()
        self.root.after(CTX_REFRESH_SEC * 1000, self._refresh_context)

    def _apply_context(self, ctx: dict | None):
        bar_f, _, _, bar_rl = self._bars["context"]
        if ctx:
            self._ctx_title_lbl.config(
                text=f"Contesto  ({ctx['model']})" if ctx["model"] else "Contesto")
            # pack(before=) fallisce se il riferimento non è packato (es. API
            # senza five_hour): ancora alla prima barra visibile, altrimenti
            # pack semplice (il frame contesto resta comunque in _bar_frame).
            anchor = next(
                (self._bars[k][0]
                 for k in ("five_hour", "seven_day", "seven_day_sonnet")
                 if self._bars[k][0].winfo_manager()),
                None)
            if anchor is not None:
                bar_f.pack(fill=tk.X, pady=(0, 5), before=anchor)
            else:
                bar_f.pack(fill=tk.X, pady=(0, 5))
            self._draw_bar("context", ctx["pct"], "")
            bar_rl.config(
                text=f"{ctx['tokens_used']:,} / {ctx['tokens_max']:,} tk"
                     f"  ·  {ctx['age_min']}m fa")
            self._values["context"] = (ctx["pct"], True)
        else:
            bar_f.pack_forget()
            self._values["context"] = (0, False)
        self._sync_compact()
        self._position_window()

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
            log.warning("Refresh utilizzo fallito: %s", e)
            self.show_error(str(e)[:40])

    def _refresh_loop(self):
        while True:
            self._wake.clear()
            self._refresh_once()
            self._wake.wait(REFRESH_SEC)

    def _start_refresh_loop(self):
        """
        Avvia il thread di refresh (una sola volta) o, se già attivo, forza un
        refresh immediato. Evita i thread duplicati che si accumulavano a ogni
        salvataggio dal dialog impostazioni.
        """
        if self._loop_started:
            self._wake.set()
            return
        self._loop_started = True
        threading.Thread(target=self._refresh_loop, daemon=True).start()

    def _start(self):
        self.creds = load_credentials()
        if not self.creds:
            self.root.after(200, self._show_setup)
        else:
            self._start_refresh_loop()
        self._refresh_context()  # avvia loop autonomo context window (ogni 60s)

    # ── drag ──────────────────────────────────────────────────────────────────

    def _drag_start(self, e):
        # Registra il punto di partenza in coordinate schermo (x_root/y_root) e la
        # posizione della finestra ORA, mentre è ferma (winfo_x affidabile). Durante il
        # resize dei toggle winfo_x è stale, quindi non lo leggiamo mai in _drag_move.
        self._drag_x0  = e.x_root
        self._drag_y0  = e.y_root
        self._win_x0   = self.root.winfo_x()
        self._win_y0   = self.root.winfo_y()
        self._dragging = False

    def _drag_move(self, e):
        dx = e.x_root - self._drag_x0
        dy = e.y_root - self._drag_y0
        # Soglia anti-jitter: un clic sull'icona toggle/gear muove il mouse di 1-2px e
        # NON deve essere trattato come drag (altrimenti corrompe l'ancora → la finestra
        # salta a ogni toggle). Solo oltre 5px diventa un vero trascinamento.
        if not self._dragging and abs(dx) < 5 and abs(dy) < 5:
            return
        self._dragging = True
        x = self._win_x0 + dx
        y = self._win_y0 + dy
        self.root.geometry(f"+{x}+{y}")
        # aggiorna l'ancora così i futuri toggle/refresh restano dove l'utente trascina
        w = COMPACT_W if self.compact else WIN_W
        self._anchor_right  = x + w
        self._anchor_bottom = y + self._cur_h

    # ── menu ──────────────────────────────────────────────────────────────────

    def _ctx_menu(self, e):
        m = tk.Menu(self.root, tearoff=0,
                    bg=C["bg2"], fg=C["fg"],
                    activebackground=C["bg"],
                    activeforeground=C["accent"],
                    bd=0, relief=tk.FLAT)
        m.add_command(label="🔄  Aggiorna ora",
                      command=self._start_refresh_loop)
        m.add_separator()
        m.add_command(label="⚙  Impostazioni", command=self._show_setup)
        m.add_separator()
        m.add_command(label="✕  Chiudi",       command=self.root.destroy)
        # tk_popup + grab_release: con overrideredirect m.post può lasciare
        # il grab appeso (menu che non si chiude / widget che non risponde)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    # ── setup ─────────────────────────────────────────────────────────────────

    def _show_setup(self):
        cfg = _load_cfg()
        dlg = tk.Toplevel(self.root)
        dlg.title("Impostazioni – Claude Usage Widget")
        dlg.configure(bg=C["bg"])
        dlg.geometry("420x500")
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

        def secret_entry(var):
            # Campo token mascherato (screen-sharing safe) + occhio per rivelare
            row = tk.Frame(pad, bg=C["bg2"])
            ent = tk.Entry(row, textvariable=var, show="•",
                           font=("Courier New", 8),
                           bg=C["bg2"], fg=C["fg"],
                           insertbackground=C["fg"],
                           relief=tk.FLAT, bd=0)
            ent.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
            eye = tk.Label(row, text="👁", bg=C["bg2"], fg=C["gray"],
                           font=("Segoe UI", 9), cursor="hand2", padx=6)
            eye.pack(side=tk.RIGHT)
            eye.bind("<Button-1>",
                     lambda _: ent.config(show="" if ent.cget("show") else "•"))
            return row

        tk.Label(pad, text="sessionKey:",
                 bg=C["bg"], fg="#aaa",
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))
        sk_var = tk.StringVar(value=cfg.get("session_key", ""))
        secret_entry(sk_var).pack(fill=tk.X, pady=(2, 0))

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
        secret_entry(ot_var).pack(fill=tk.X, pady=(2, 0))

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
            self._start_refresh_loop()

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

        # ── Footer: versione a sinistra, credit a destra (come nel widget) ────
        foot = tk.Frame(pad, bg=C["bg"])
        foot.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))
        tk.Label(foot, text=f"v{APP_VERSION}",
                 font=("Segoe UI", 7), bg=C["bg"], fg=C["gray"]).pack(side=tk.LEFT)
        flink = tk.Label(foot, text="Felter Roberto",
                         font=("Segoe UI", 7), bg=C["bg"],
                         fg=C["accent"], cursor="hand2")
        flink.pack(side=tk.RIGHT)
        tk.Label(foot, text="by ",
                 font=("Segoe UI", 7), bg=C["bg"], fg=C["gray"]).pack(side=tk.RIGHT)
        flink.bind("<Button-1>",
                   lambda _: webbrowser.open("https://www.felter.it"))

    # ── run ───────────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    UsageWidget().run()
