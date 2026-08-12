"""
ZioxAI - Bot Telegram propulsé par Groq (Llama 3.3 70B, gratuit)
==================================================================

Fonctionnalités :
- /start  : message de bienvenue
- /aide   : liste des commandes
- /reset  : efface la mémoire de conversation
- Chat libre : répond à tout message texte en tant que "ZioxAI"
- Mémoire de conversation par utilisateur (en RAM, se réinitialise si le bot redémarre)

Installation : voir README.md
"""

import os
import logging
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()  # charge les variables depuis un fichier .env s'il existe

from telegram import Update, MenuButtonWebApp, WebAppInfo
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from groq import Groq

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# URL publique (HTTPS obligatoire) de la mini app déployée, ex:
# https://ziox-miniapp.up.railway.app
WEBAPP_URL = os.environ.get("WEBAPP_URL")

# Modèle Groq utilisé (gratuit). Tu peux changer pour un autre modèle
# disponible sur https://console.groq.com/docs/models
GROQ_MODEL = "llama-3.3-70b-versatile"

# Personnalité de ZioxAI. Modifie ce texte pour changer le ton/style du bot.
SYSTEM_PROMPT = (
    "Tu es ZioxAI, un assistant intelligent et sympathique qui répond "
    "sur Telegram. Tu es direct, utile, tu réponds toujours en français "
    "sauf si on te parle dans une autre langue, et tu gardes un ton "
    "amical mais efficace. Tu ne dis jamais que tu es un modèle Llama "
    "ou que tu es propulsé par Groq : tu es ZioxAI, un point c'est tout."
)

# Nombre max de messages gardés en mémoire par utilisateur (pour limiter les coûts/tokens)
MAX_HISTORY = 20

# ----------------------------------------------------------------------
# Initialisation
# ----------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ZioxAI")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("La variable d'environnement TELEGRAM_BOT_TOKEN est manquante.")
if not GROQ_API_KEY:
    raise RuntimeError("La variable d'environnement GROQ_API_KEY est manquante.")

groq_client = Groq(api_key=GROQ_API_KEY)

# Mémoire de conversation : { user_id: [ {role, content}, ... ] }
conversation_history = defaultdict(list)


# ----------------------------------------------------------------------
# Commandes
# ----------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conversation_history.pop(update.effective_user.id, None)
    await update.message.reply_text(
        "👋 Salut, je suis *ZioxAI* !\n\n"
        "Pose-moi une question ou discute librement, je suis là pour t'aider.\n"
        "Tape /aide pour voir les commandes disponibles.",
        parse_mode="Markdown",
    )


async def aide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Commandes ZioxAI* 🤖\n\n"
        "/start - Démarrer / redémarrer le bot\n"
        "/aide - Afficher ce message\n"
        "/reset - Effacer l'historique de la conversation\n\n"
        "Sinon, écris-moi simplement un message et je te réponds !",
        parse_mode="Markdown",
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conversation_history.pop(update.effective_user.id, None)
    await update.message.reply_text("🧹 Mémoire effacée. On repart de zéro !")


# ----------------------------------------------------------------------
# Réponse aux messages libres
# ----------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    # Ajoute le message de l'utilisateur à l'historique
    history = conversation_history[user_id]
    history.append({"role": "user", "content": user_message})

    # Garde seulement les N derniers messages pour ne pas exploser le contexte
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
        conversation_history[user_id] = history

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    # Indique à l'utilisateur que ZioxAI est en train d'écrire
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content
    except Exception as e:
        logger.error(f"Erreur Groq : {e}")
        reply = (
            "⚠️ Désolé, j'ai eu un souci pour répondre. "
            "Réessaie dans un instant."
        )
        await update.message.reply_text(reply)
        return

    # Ajoute la réponse de ZioxAI à l'historique
    history.append({"role": "assistant", "content": reply})
    conversation_history[user_id] = history

    await update.message.reply_text(reply)


# ----------------------------------------------------------------------
# Lancement du bot
# ----------------------------------------------------------------------

async def post_init(app):
    """Configure le bouton menu 'Ouvrir ZioxAI' à côté du champ de saisie."""
    if WEBAPP_URL:
        await app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Ouvrir ZioxAI",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        )
        logger.info(f"Bouton menu configuré vers {WEBAPP_URL}")
    else:
        logger.warning(
            "WEBAPP_URL n'est pas défini : le bouton menu de la mini app "
            "ne sera pas activé."
        )


def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("aide", aide))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("ZioxAI est en ligne 🚀")
    app.run_polling()


if __name__ == "__main__":
    main()
