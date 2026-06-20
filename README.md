# Certificate Generation System

A production-ready backend system for automating the generation of used cooking oil collection certificates. Operates entirely through a Telegram bot with a guided conversational interface, storing records in SQLite and producing DOCX/PDF documents on demand.

---

## Features

- **Telegram Bot interface** — 8-step guided wizard to collect certificate data with inline validation at every step
- **Document generation** — Produces `.docx` and `.pdf` certificates from configurable Word templates
- **Full audit trail** — Every create, update, delete, and restore action is logged with before/after snapshots
- **Soft delete** — Records are never permanently removed; they can be restored at any time
- **Search & history** — Query certificates by restaurant name, NIT, city, date range, or collection type
- **Automated backups** — Scheduled ZIP backups of the database and generated documents
- **Multi-template support** — Multiple certificate templates selectable per generation
- **Access control** — Whitelist of authorized Telegram user IDs configured via environment variable
- **Single-instance guard** — PID file prevents duplicate bot processes

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.14 |
| Bot framework | python-telegram-bot 21.7 |
| API framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x (async) |
| Database | SQLite via aiosqlite |
| Validation | Pydantic v2 + pydantic-settings |
| Document generation | python-docx |
| Async I/O | asyncio + aiofiles |

---

## Project Structure

```
├── main.py                         # Entry point — starts the bot
├── app/
│   ├── config.py                   # Settings loaded from .env (Pydantic)
│   ├── bot/
│   │   ├── bot.py                  # Bot application builder
│   │   ├── states.py               # ConversationHandler state constants
│   │   ├── pagination.py           # Paginated inline keyboard utility
│   │   ├── keyboards/buttons.py    # Reusable reply/inline keyboards
│   │   └── handlers/
│   │       ├── certificate.py      # Full certificate creation wizard + /verificar
│   │       ├── search.py           # Search and listing handlers
│   │       ├── admin.py            # Admin commands (edit, delete, restore)
│   │       ├── backup.py           # Manual backup trigger handler
│   │       └── start.py            # /start and main menu
│   ├── database/
│   │   ├── base.py                 # Async engine and session factory
│   │   └── init_db.py              # Schema creation on startup
│   ├── models/
│   │   ├── certificate.py          # Certificate model + TipoCertificado enum
│   │   ├── history.py              # Audit log model
│   │   ├── user.py                 # Authorized user model
│   │   └── mixins.py               # Shared timestamp columns
│   ├── schemas/
│   │   ├── certificate.py          # CertificateCreate / Update / Search schemas
│   │   └── user.py                 # User schemas
│   ├── services/
│   │   ├── certificate_service.py  # Business logic: CRUD + audit logging
│   │   ├── document_service.py     # DOCX/PDF generation from templates
│   │   └── backup_service.py       # ZIP backup creation and scheduling
│   ├── templates/                  # Word (.docx) certificate templates
│   └── utils/
│       ├── code_generator.py       # Sequential certificate code generator (CERT-YYYY-NNNNNN)
│       ├── file_utils.py           # Path helpers
│       └── logger.py               # Structured logger setup
└── requirements.txt
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Your Telegram user ID (use [@userinfobot](https://t.me/userinfobot))

### Installation

```bash
git clone https://github.com/santrolop1/sistema-certificados.git
cd sistema-certificados

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
AUTHORIZED_USERS=123456789,987654321   # comma-separated Telegram user IDs
DATABASE_URL=sqlite+aiosqlite:///./app/database/certificados.db
DOCUMENTS_DIR=documentos
BACKUPS_DIR=backups
TEMPLATES_DIR=app/templates
APP_ENV=development
LOG_LEVEL=INFO
```

### Adding certificate templates

Place your `.docx` template files in `app/templates/`:

```
app/templates/certificado_template.docx    → Template 1
app/templates/certificado_template_2.docx  → Template 2
```

Templates use placeholder text that the document service replaces at generation time.

### Run

```bash
python main.py
```

The bot starts polling. Send `/start` on Telegram to open the main menu.

---

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Main menu |
| `/nuevo` | Start the certificate creation wizard |
| `/buscar` | Search certificates |
| `/verificar CERT-YYYY-NNNNNN` | Look up a certificate by code |
| `/cancelar` | Cancel the current operation |

---

## Certificate Codes

Codes follow the format `CERT-YYYY-NNNNNN` where `YYYY` is the collection year and `NNNNNN` is a zero-padded sequential number that resets each year. The sequence is derived from the database at runtime, with up to 5 collision-retry attempts on concurrent writes.

---

## Audit Log

Every mutation (create, update, delete, restore) writes a `HistorialCambio` record containing:

- Entity type and ID
- Action type (`CREAR`, `ACTUALIZAR`, `ELIMINAR`, `RESTAURAR`)
- Telegram user ID of the actor
- Full before/after JSON snapshots of the certificate

---

## License

MIT
