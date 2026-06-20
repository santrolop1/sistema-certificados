<div align="center">

# Certificate Generation System
### Sistema de Generación de Certificados

**🇬🇧 English** | **🇪🇸 [Español](#sistema-de-generación-de-certificados-1)**

A production-ready backend system for automating the generation of used cooking oil collection certificates, operated entirely through a Telegram bot with a guided conversational interface.

</div>

---

## Features

- **Telegram Bot interface** — 8-step guided wizard with inline validation at every step
- **Document generation** — Produces `.docx` and `.pdf` certificates from configurable Word templates
- **Full audit trail** — Every create, update, delete and restore action is logged with before/after snapshots
- **Soft delete** — Records are never permanently removed; they can be restored at any time
- **Search & history** — Query by restaurant name, NIT, city, date range, or collection type
- **Automated backups** — Scheduled ZIP backups of the database and generated documents
- **Multi-template support** — Multiple certificate templates selectable per generation
- **Access control** — Whitelist of authorized Telegram user IDs via environment variable
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
│   │       ├── certificate.py      # Certificate creation wizard + /verificar
│   │       ├── search.py           # Search and listing handlers
│   │       ├── admin.py            # Admin commands (edit, delete, restore)
│   │       ├── backup.py           # Manual backup trigger
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
│   │   ├── certificate.py          # CertificateCreate / Update / Search
│   │   └── user.py                 # User schemas
│   ├── services/
│   │   ├── certificate_service.py  # Business logic: CRUD + audit logging
│   │   ├── document_service.py     # DOCX/PDF generation from templates
│   │   └── backup_service.py       # ZIP backup creation and scheduling
│   ├── templates/                  # Word (.docx) certificate templates
│   └── utils/
│       ├── code_generator.py       # Sequential code generator (CERT-YYYY-NNNNNN)
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

```bash
cp .env.example .env
```

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
AUTHORIZED_USERS=123456789,987654321
DATABASE_URL=sqlite+aiosqlite:///./app/database/certificados.db
DOCUMENTS_DIR=documentos
BACKUPS_DIR=backups
TEMPLATES_DIR=app/templates
APP_ENV=development
LOG_LEVEL=INFO
```

### Templates

Place `.docx` template files in `app/templates/`:

```
app/templates/certificado_template.docx     → Template 1
app/templates/certificado_template_2.docx   → Template 2
```

### Run

```bash
python main.py
```

Send `/start` on Telegram to open the main menu.

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

Format: `CERT-YYYY-NNNNNN` — year of collection + zero-padded sequential number that resets each year. Generated at runtime from the database with up to 5 collision-retry attempts.

---

## Audit Log

Every mutation writes a `HistorialCambio` record with:

- Entity type and ID
- Action (`CREAR`, `ACTUALIZAR`, `ELIMINAR`, `RESTAURAR`)
- Telegram user ID of the actor
- Full before/after JSON snapshots

---

## License

MIT

---
---

<div align="center">

# Sistema de Generación de Certificados

**🇪🇸 Español** | **🇬🇧 [English](#certificate-generation-system)**

Sistema backend listo para producción que automatiza la generación de certificados de recolección de aceite usado. Funciona completamente a través de un bot de Telegram con una interfaz conversacional guiada.

</div>

---

## Funcionalidades

- **Interfaz via bot de Telegram** — Asistente de 8 pasos con validación inline en cada campo
- **Generación de documentos** — Crea certificados `.docx` y `.pdf` desde plantillas Word configurables
- **Auditoría completa** — Cada creación, edición, eliminación y restauración queda registrada con snapshots antes/después
- **Soft delete** — Los registros nunca se borran permanentemente; pueden restaurarse en cualquier momento
- **Búsqueda e historial** — Consultas por nombre, NIT, ciudad, rango de fechas o tipo de recolección
- **Backups automáticos** — Respaldos ZIP programados de la base de datos y documentos generados
- **Múltiples plantillas** — Se puede seleccionar la plantilla por cada certificado generado
- **Control de acceso** — Lista blanca de usuarios de Telegram autorizados via variable de entorno
- **Instancia única** — Archivo PID que evita ejecutar el bot dos veces simultáneamente

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.14 |
| Bot | python-telegram-bot 21.7 |
| API | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x (async) |
| Base de datos | SQLite via aiosqlite |
| Validación | Pydantic v2 + pydantic-settings |
| Generación de docs | python-docx |
| I/O asíncrono | asyncio + aiofiles |

---

## Inicio rápido

### Requisitos previos

- Python 3.12+
- Token de bot de Telegram desde [@BotFather](https://t.me/BotFather)
- Tu ID de Telegram (usa [@userinfobot](https://t.me/userinfobot))

### Instalación

```bash
git clone https://github.com/santrolop1/sistema-certificados.git
cd sistema-certificados

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Configuración

```bash
cp .env.example .env
```

```env
TELEGRAM_BOT_TOKEN=tu_token_aqui
AUTHORIZED_USERS=123456789,987654321
DATABASE_URL=sqlite+aiosqlite:///./app/database/certificados.db
DOCUMENTS_DIR=documentos
BACKUPS_DIR=backups
TEMPLATES_DIR=app/templates
APP_ENV=development
LOG_LEVEL=INFO
```

### Plantillas

Coloca los archivos `.docx` en `app/templates/`:

```
app/templates/certificado_template.docx     → Plantilla 1
app/templates/certificado_template_2.docx   → Plantilla 2
```

### Ejecutar

```bash
python main.py
```

Envía `/start` en Telegram para abrir el menú principal.

---

## Comandos del bot

| Comando | Descripción |
|---|---|
| `/start` | Menú principal |
| `/nuevo` | Iniciar el asistente de creación |
| `/buscar` | Buscar certificados |
| `/verificar CERT-AAAA-NNNNNN` | Consultar un certificado por código |
| `/cancelar` | Cancelar la operación actual |

---

## Códigos de certificado

Formato: `CERT-AAAA-NNNNNN` — año de recolección + número secuencial con ceros que se reinicia cada año. Se genera en tiempo de ejecución desde la base de datos con hasta 5 reintentos ante colisiones.

---

## Registro de auditoría

Cada mutación escribe un registro `HistorialCambio` con:

- Tipo e ID de entidad
- Acción (`CREAR`, `ACTUALIZAR`, `ELIMINAR`, `RESTAURAR`)
- ID de Telegram del usuario que realizó la acción
- Snapshots JSON completos del estado antes y después

---

## Licencia

MIT
