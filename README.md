# 🤖 ZioxAI — Bot Telegram gratuit (propulsé par Groq)

Un bot Telegram qui répond en tant que **ZioxAI**, gratuit, en utilisant l'API
Groq (modèle Llama 3.3 70B).

## 1. Créer ton bot Telegram

1. Ouvre Telegram et cherche **@BotFather**.
2. Envoie-lui la commande `/newbot`.
3. Donne un nom à ton bot (ex: `ZioxAI`) puis un identifiant se terminant par
   `bot` (ex: `ZioxAI_bot`).
4. BotFather te donne un **token** (une longue chaîne comme
   `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`). Garde-le, tu en auras
   besoin.

## 2. Obtenir une clé API Groq (gratuite)

1. Va sur https://console.groq.com
2. Crée un compte gratuit.
3. Va dans **API Keys** → **Create API Key**.
4. Copie la clé générée.

## 3. Installer le projet

Assure-toi d'avoir **Python 3.10+** installé, puis dans le dossier du projet :

```bash
pip install -r requirements.txt
```

## 4. Configurer les clés

Copie le fichier `.env.example` en `.env` :

```bash
cp .env.example .env
```

Ouvre `.env` et remplace les valeurs par tes vraies clés :

```
TELEGRAM_BOT_TOKEN=123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 5. Lancer le bot

```bash
python bot.py
```

Si tout est bon, tu verras dans le terminal :
```
ZioxAI est en ligne 🚀
```

Va sur Telegram, ouvre une conversation avec ton bot, et envoie `/start` !

## 6. Personnaliser ZioxAI

Tout se passe dans `bot.py` :

- **`SYSTEM_PROMPT`** : change la personnalité, le ton, les règles de
  comportement du bot.
- **`GROQ_MODEL`** : change le modèle IA utilisé (liste des modèles
  disponibles sur https://console.groq.com/docs/models).
- **`MAX_HISTORY`** : nombre de messages gardés en mémoire par utilisateur.

## 7. Garder le bot en ligne 24/7 (optionnel)

Sur ta machine, le bot s'arrête si tu fermes le terminal. Pour un
fonctionnement continu et gratuit, tu peux héberger le script sur :

- **Railway** (offre gratuite avec limite mensuelle)
- **Render** (offre gratuite, "Background Worker")
- Un Raspberry Pi ou vieux PC chez toi, allumé en permanence

Le fichier **`Procfile`** est déjà inclus dans le projet — il indique à ces
plateformes comment démarrer le bot :
```
worker: python bot.py
```
⚠️ Sur Railway/Render, choisis bien un service de type **Worker** (pas
**Web**) : le bot n'écoute pas sur un port HTTP, il fonctionne en "polling"
(il interroge Telegram en continu). Pense aussi à ajouter tes variables
`TELEGRAM_BOT_TOKEN` et `GROQ_API_KEY` dans les paramètres d'environnement
de la plateforme (pas besoin du fichier `.env` dans ce cas).

Dis-moi si tu veux de l'aide pour le déployer sur l'une de ces plateformes.

## ⚠️ Notes importantes

- Ne partage **jamais** ton fichier `.env` ni tes clés API (ne les mets pas
  sur GitHub en public).
- L'offre gratuite de Groq a des limites de requêtes par minute/jour —
  largement suffisantes pour un usage perso, mais à savoir si tu as beaucoup
  d'utilisateurs.
- La mémoire de conversation est stockée en RAM : si tu redémarres le bot,
  l'historique de chaque utilisateur est perdu (tape `/reset` pour l'effacer
  manuellement à tout moment).
