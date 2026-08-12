"""
ZioxAI Mini App - Backend FastAPI
==================================

Sert l'interface de chat (dossier /static) et une API qui relaie les
messages vers Groq, avec la même personnalité "ZioxAI".

La mémoire de conversation est stockée CÔTÉ SERVEUR dans une base SQLite
(un fichier zioxai.db), une conversation par utilisateur Telegram :
- persiste même si l'utilisateur ferme la mini app ou change d'appareil
- personne ne peut lire l'historique de quelqu'un d'autre (identifié via
  l'utilisateur Telegram vérifié, pas par un ID choisi côté client)

Lancement local :
    uvicorn server:app --reload --port 8000

Déploiement :
    uvicorn server:app --host 0.0.0.0 --port $PORT
"""

import os
import hashlib
import hmac
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from urllib.parse import parse_qsl

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  # utilisé pour identifier/vérifier l'utilisateur
GROQ_MODEL = "llama-3.3-70b-versatile"
DB_PATH = os.environ.get("DB_PATH", "zioxai.db")

# Nombre de messages (user + assistant confondus) gardés en mémoire par utilisateur
MAX_HISTORY = 30

if not GROQ_API_KEY:
    raise RuntimeError("La variable d'environnement GROQ_API_KEY est manquante.")

groq_client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = (
    "Tu es ZioxAI, un assistant intelligent et sympathique qui répond "
    "dans une mini application Telegram. Tu es direct, utile, tu réponds "
    "toujours en français sauf si on te parle dans une autre langue, et "
    "tu gardes un ton amical mais efficace. Tu ne dis jamais que tu es un "
    "modèle Llama ou que tu es propulsé par Groq : tu es ZioxAI, un point "
    "c'est tout."
)

app = FastAPI(title="ZioxAI Mini App")


# ----------------------------------------------------------------------
# Base de données (SQLite)
# ----------------------------------------------------------------------

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id)")


init_db()


def get_history(user_id: str, limit: int = MAX_HISTORY) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"role": r, "content": c} for r, c in reversed(rows)]


def append_message(user_id: str, role: str, content: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, content, time.time()),
        )


def clear_history(user_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))


# ----------------------------------------------------------------------
# Identification / vérification de l'utilisateur Telegram
# ----------------------------------------------------------------------

def verify_and_parse_init_data(init_data: str, bot_token: str) -> dict | None:
    """Vérifie la signature d'initData et retourne les données décodées, ou None si invalide."""
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed_hash, received_hash):
            return None
        return parsed
    except Exception:
        return None


def resolve_user_id(init_data: str | None, anon_id: str | None) -> str:
    """
    Détermine l'identifiant unique de l'utilisateur pour la base de données.

    - Si TELEGRAM_BOT_TOKEN est configuré : initData DOIT être présent et valide.
      L'ID Telegram de l'utilisateur (vérifié, infalsifiable) est utilisé.
    - Sinon (mode dev / test hors Telegram) : on retombe sur un identifiant
      anonyme envoyé par le navigateur (moins sûr, pratique uniquement en local).
    """
    if TELEGRAM_BOT_TOKEN:
        if not init_data:
            raise HTTPException(status_code=401, detail="initData Telegram manquant")
        parsed = verify_and_parse_init_data(init_data, TELEGRAM_BOT_TOKEN)
        if not parsed:
            raise HTTPException(status_code=401, detail="initData Telegram invalide")
        try:
            user = json.loads(parsed.get("user", "{}"))
            telegram_id = user.get("id")
        except (json.JSONDecodeError, AttributeError):
            telegram_id = None
        if not telegram_id:
            raise HTTPException(status_code=401, detail="Impossible d'identifier l'utilisateur Telegram")
        return f"tg:{telegram_id}"

    # Mode dev sans TELEGRAM_BOT_TOKEN : identifiant anonyme fourni par le client
    if not anon_id:
        raise HTTPException(status_code=400, detail="anon_id manquant (mode dev)")
    return f"anon:{anon_id}"


# ----------------------------------------------------------------------
# Schémas
# ----------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    init_data: str | None = None
    anon_id: str | None = None  # utilisé uniquement si TELEGRAM_BOT_TOKEN n'est pas défini


class HistoryRequest(BaseModel):
    init_data: str | None = None
    anon_id: str | None = None


class ResetRequest(BaseModel):
    init_data: str | None = None
    anon_id: str | None = None


# ----------------------------------------------------------------------
# Routes API
# ----------------------------------------------------------------------

@app.post("/api/history")
async def history(req: HistoryRequest):
    """Renvoie l'historique de conversation déjà stocké pour cet utilisateur."""
    user_id = resolve_user_id(req.init_data, req.anon_id)
    return {"messages": get_history(user_id)}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    user_id = resolve_user_id(req.init_data, req.anon_id)
    text = req.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message vide")

    # Charge l'historique existant, ajoute le nouveau message utilisateur
    past = get_history(user_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + past + [{"role": "user", "content": text}]

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Groq : {e}")

    # Persiste les deux messages (utilisateur + réponse) côté serveur
    append_message(user_id, "user", text)
    append_message(user_id, "assistant", reply)

    return {"reply": reply}


@app.post("/api/reset")
async def reset(req: ResetRequest):
    user_id = resolve_user_id(req.init_data, req.anon_id)
    clear_history(user_id)
    return {"ok": True}


@app.get("/api/anon-id")
async def anon_id():
    """Génère un identifiant anonyme (mode dev uniquement, hors Telegram)."""
    return {"anon_id": str(uuid.uuid4())}


# Sert les fichiers statiques (index.html, css, js) à la racine "/"
app.mount("/", StaticFiles(directory="static", html=True), name="static")
