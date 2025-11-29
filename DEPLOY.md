# Gustino SPA - Deployment Guide for Render

## Deploy su Render

### 1. Preparazione Repository
Assicurati che tutti i file siano committati su GitHub:
```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### 2. Configurazione su Render

1. Vai su [render.com](https://render.com) e fai login
2. Clicca su "New +" e seleziona "Web Service"
3. Connetti il tuo repository GitHub `gustinojr/Gustino-SPA`

### 3. Configurazione Web Service

**Build & Deploy:**
- **Name:** `gustino-spa`
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn run:app`

### 4. Environment Variables

Aggiungi le seguenti variabili d'ambiente:

| Key | Value | Note |
|-----|-------|------|
| `SECRET_KEY` | `<genera-stringa-casuale>` | Chiave segreta Flask |
| `TELEGRAM_BOT_TOKEN` | `<tuo-bot-token>` | Token del bot Telegram |
| `TELEGRAM_BOT_USERNAME` | `GustinoSpa_bot` | Username del bot |
| `OWNER_CHAT_ID` | `<tuo-chat-id>` | Il tuo Chat ID Telegram |
| `DATABASE_URL` | Auto-generato | Connessione PostgreSQL |
| `PYTHON_VERSION` | `3.9.0` | Versione Python |

### 5. Database PostgreSQL

1. Nella dashboard Render, vai su "New +" → "PostgreSQL"
2. **Name:** `gustino-spa-db`
3. **Database:** `gustino_spa`
4. **User:** `gustino_spa_user`
5. Copia l'**Internal Database URL** e usala come `DATABASE_URL`

### 6. Deploy

1. Clicca su "Create Web Service"
2. Render farà il deploy automaticamente
3. Il sito sarà disponibile su `https://gustino-spa.onrender.com`

### 7. Post-Deploy

**Configura Webhook Telegram (Opzionale):**
```bash
curl https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://gustino-spa.onrender.com/telegram-webhook
```

**Verifica App:**
- Visita `https://gustino-spa.onrender.com`
- Inserisci codice voucher `20121997`
- Testa il flusso completo di registrazione

### 8. Monitoraggio

- **Logs:** Dashboard Render → Logs tab
- **Database:** Dashboard Render → PostgreSQL → Connect

### Note Importanti

⚠️ **Free tier Render:**
- L'app si "addormenta" dopo 15 minuti di inattività
- Il primo caricamento dopo sleep richiede ~30 secondi
- Per servizio attivo 24/7, upgrade a piano Starter ($7/mese)

✅ **Il bot Telegram polling continua a funzionare** anche quando l'app è attiva.

---

## Struttura File per Deploy

```
Gustino-SPA/
├── render.yaml          # Configurazione Render
├── Procfile            # Comando start per Render
├── requirements.txt    # Dipendenze Python
├── run.py             # Entry point applicazione
├── config.py          # Configurazione app
└── app/
    ├── __init__.py
    ├── models.py
    ├── telegram_polling.py
    ├── telegram_utils.py
    ├── routes/
    │   ├── home.py
    │   ├── register.py
    │   └── booking.py
    ├── templates/
    └── static/
```

## Troubleshooting

**Errore Database:**
- Verifica che `DATABASE_URL` sia impostato correttamente
- Controlla che la connessione PostgreSQL sia attiva

**Bot non risponde:**
- Verifica `TELEGRAM_BOT_TOKEN` nelle variabili d'ambiente
- Controlla i logs per errori del bot

**App lenta al primo caricamento:**
- Normale su free tier, considera upgrade per servizio sempre attivo
