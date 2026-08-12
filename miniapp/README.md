# 💬 ZioxAI Mini App

Interface de chat qui s'ouvre **dans Telegram**, via le bouton menu du bot.

## Structure

```
miniapp/
├── server.py          # Backend FastAPI (API /api/chat -> Groq)
├── static/
│   └── index.html     # Interface de chat (HTML/CSS/JS, thème Telegram)
├── requirements.txt
├── Procfile
└── .env.example
```

## 1. Installer et tester en local

```bash
cd miniapp
pip install -r requirements.txt
cp .env.example .env
# remplis GROQ_API_KEY dans .env
uvicorn server:app --reload --port 8000
```

Ouvre http://localhost:8000 dans un navigateur pour voir le rendu (le thème
Telegram ne s'applique qu'une fois ouvert dans l'app Telegram, en local tu
verras les couleurs par défaut).

## 2. Déployer la mini app (HTTPS obligatoire)

Telegram exige une URL en **HTTPS**. Le plus simple : héberger ce dossier
`miniapp/` comme un service séparé sur **Railway** ou **Render**.

Sur Railway par exemple :
1. Crée un nouveau service à partir de ce dossier `miniapp/`.
2. Ajoute la variable d'environnement `GROQ_API_KEY` (et `TELEGRAM_BOT_TOKEN`
   si tu veux activer la vérification de sécurité).
3. Railway détecte le `Procfile` et lance `uvicorn server:app --host 0.0.0.0 --port $PORT`.
4. Une fois déployé, tu obtiens une URL du type
   `https://ziox-miniapp.up.railway.app`.

## 3. Brancher la mini app sur ton bot

Dans le projet du **bot** (pas la mini app), ajoute cette variable
d'environnement :

```
WEBAPP_URL=https://ziox-miniapp.up.railway.app
```

Redéploie/relance le bot. Il configure automatiquement un bouton
**"Ouvrir ZioxAI"** à côté du champ de saisie, dans la conversation Telegram.

## 4. Sécurité (recommandé)

Si tu définis `TELEGRAM_BOT_TOKEN` dans les variables d'env de la **mini
app** (même token que le bot), le backend vérifie que chaque requête
`/api/chat` vient bien de Telegram (via `initData`), et refuse les appels
extérieurs. Sans cette variable, l'API est ouverte à quiconque connaît
l'URL — pratique pour tester, à éviter en production si tu veux limiter
l'usage à tes utilisateurs Telegram.

## 5. Personnaliser

- **Couleurs / identité visuelle** : dans `static/index.html`, section
  `<style>`, variables `--zx-accent-a` / `--zx-accent-b`. Le reste (fond,
  texte, bulles) suit automatiquement le thème clair/sombre de Telegram.
- **Personnalité du bot** : `SYSTEM_PROMPT` dans `server.py` (garde-le
  identique à celui de `bot.py` pour une expérience cohérente entre le chat
  classique et la mini app).
- **Mémoire de conversation** : actuellement stockée uniquement dans la
  page (perdue si on ferme la mini app). Dis-moi si tu veux qu'elle soit
  sauvegardée côté serveur par utilisateur, comme dans le bot.
