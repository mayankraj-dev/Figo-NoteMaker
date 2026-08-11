"""
FIGO — personal Telegram knowledge vault bot.

Upgrades:
1. /remind <id> <when>
2. Soft delete + /trash + /restore <id> (30-day trash)
3. /tldr <id> (optional Gemini API — free tier; falls back to a local
   extractive summary)
4. OCR for photos — sending a photo directly now runs OCR automatically
   (needs pytesseract + Pillow + the tesseract binary; falls back to
   caption-only saving if unavailable)
5. Full-page scraping for links
6. Duplicate/similarity warning
7. Automatic daily/weekly digest scheduling
8. /streak
9. Inline search mode
10. /export txt|md|json
11. /mcq <id> [count] — auto-generated multiple-choice quiz from a saved
    item (optional Gemini API; falls back to a local keyword-blank quiz)
12. /play <song name> — search YouTube and send back an audio file
    (needs yt-dlp + ffmpeg); each download is deleted right after it's
    sent, so it never accumulates on disk
13. /chat on|off — human-like conversational mode (needs GEMINI_API_KEY,
    free at aistudio.google.com/apikey). While on, plain text gets a
    chat reply instead of being auto-saved; /note <text> still saves
    explicitly either way
14. Off-device storage — set FIGO_STORAGE_CHAT_ID to a private group's
    ID and PDFs/photos are archived there instead of kept on disk;
    /view fetches them back on demand via Telegram's own servers.
    /chatid helps find a group's ID.

Run:
    python bot.py

Environment:
    BOT_TOKEN=...
Optional:
    GEMINI_API_KEY=...                    # free at aistudio.google.com/apikey
    FIGO_BOT_USERNAME=your_bot_username   # without @, for inline help/links
    FIGO_OCR=1                            # enable OCR when pytesseract is installed
    FIGO_STORAGE_CHAT_ID=...              # private group ID for off-device file storage
    FIGO_ANNOUNCE_CHAT_ID=...             # channel ID — posts a changelog card here on every update

Recommended dependencies:
    python-telegram-bot
    requests
    pypdf
    beautifulsoup4
    pytesseract
    Pillow
    yt-dlp
"""

# ---------------------------------------------------------------------------
# Changelog — one entry per shipped update. Add a new entry to the END of
# this list whenever bot.py changes. On startup, the bot compares len(CHANGELOG)
# against the last-announced count stored in the database (bot_meta table)
# and posts any new entries to FIGO_ANNOUNCE_CHAT_ID as a photo+caption card
# with the bot's own profile picture, each numbered "Update #N". This is what
# powers the announcement channel — the list below is the single source of
# truth for what gets posted, so keep entries short, factual, and user-facing
# (what changed + how to use it), not implementation detail.
# ---------------------------------------------------------------------------

CHANGELOG = [
    {
        "title": "Group activity log",
        "summary": (
            "The bot now posts a live status line to its storage group for "
            "every important moment: startup, a new user starting the bot, "
            "a note/photo/PDF being saved, a song being downloaded, and a "
            "file being sent. Previously the group stayed silent even when "
            "everything was working correctly."
        ),
        "usage": (
            "Set FIGO_STORAGE_CHAT_ID to your group's ID (use /chatid inside "
            "the group to find it) and make sure the bot is a member there. "
            "You'll then see a confirmation for everything the bot does."
        ),
    },
    {
        "title": "Cyberpunk text styling",
        "summary": (
            "Status messages like \"Downloading…\", \"Searching…\" and "
            "\"Sending…\" now render in a bold monospace Unicode style for a "
            "more distinctive, cyberpunk look, matching the existing "
            "bold-small-caps style already used for headers."
        ),
        "usage": (
            "Nothing to configure — this applies automatically to the bot's "
            "own status and progress messages."
        ),
    },
    {
        "title": "Announcement channel",
        "summary": (
            "Every future update to this bot will now post itself here: a "
            "short card with the bot's profile picture, a numbered update "
            "count, what changed, and how to use it — so you always know "
            "what version is running and what's new."
        ),
        "usage": (
            "Set FIGO_ANNOUNCE_CHAT_ID to a channel's ID and add the bot "
            "there as an admin (channels require admin rights to post). "
            "Use /chatid inside the channel to find its ID."
        ),
    },
    {
        "title": "More file types",
        "summary": (
            "Saved files aren't limited to PDFs anymore — Word (.docx), "
            "PowerPoint (.pptx), HTML pages, and code/text files (.py, .md, "
            ".txt, .json, .csv, and more) now have their text extracted and "
            "indexed automatically, just like PDFs, so /search, /tldr and "
            "/mcq all work on them too."
        ),
        "usage": (
            "Nothing to configure — just send the file. Unrecognized "
            "extensions are still stored, they just won't have searchable text."
        ),
    },
    {
        "title": "Bot cloning",
        "summary": (
            "Anyone can now spin up their own completely independent copy "
            "of this bot — separate vault, separate storage group, separate "
            "everything — using their own bot token from @BotFather."
        ),
        "usage": (
            "Send /clone <bot_token> in a private chat with the bot (never "
            "in a group, to keep your token safe). Check status with "
            "/myclone, or remove it with /unclone. Every clone credits "
            "@figonotebot and @tg4mayank on its /start message."
        ),
    },
    {
        "title": "Admin controls & topic help",
        "summary": (
            "FIGO now supports a real admin mode: a designated admin can pause "
            "or resume the bot for everyone, manage clones centrally, and use "
            "a cleaner help center split into topic-based commands instead of "
            "one long wall of text."
        ),
        "usage": (
            "Use /help for the help hub, then open focused sections like "
            "/hfind or /horganize. The admin user can use /admin to see "
            "maintenance, clone-management, and announcement commands."
        ),
    },
    {
        "title": "Priorities, collections, auto-tags, related notes & AI study tools",
        "summary": (
            "Vault organization got a lot more powerful: set a priority "
            "(low/medium/high/critical) on any item, group items into named "
            "collections, and get a few topic tags detected automatically on "
            "save — no setup needed for any of that. /view now also shows "
            "related items from your own vault. Three new study commands: "
            "/ask a question about a specific item, /rewrite a messy note "
            "into a clean structured one, and /explain something in plain "
            "language. Search also got sharper at catching close word "
            "variants (e.g. a search for \"strength\" now also finds "
            "\"strengths\"). As always, nothing here ever crosses between "
            "users — every feature stays scoped to your own vault."
        ),
        "usage": (
            "/priority <id> <level> and /priorities, /collection create|add|"
            "remove|view|list|delete <name>, /ask <id> <question>, /rewrite "
            "<id>, /explain <id>. Full details under /horganize and /hstudy. "
            "/ask needs GEMINI_API_KEY (free); /rewrite and /explain work "
            "without it too, just with a simpler local result."
        ),
    },
    {
        "title": "Smoother replies, uptime & ownership",
        "summary": (
            "Removed the typing/reveal text animation on replies — it was "
            "causing issues, so messages now just send directly and "
            "instantly. Added /uptime to check how long the bot's been "
            "running, and /owner to see who created and maintains it. The "
            "welcome message is friendlier and walks through a few things "
            "to try. The AI chat feature now correctly answers that Mayank "
            "created it if you ask. The announcement channel also gets a "
            "quick \"I'm live\" ping every time the bot restarts."
        ),
        "usage": (
            "/uptime and /owner work immediately, no setup. Nothing else to "
            "configure — replies are just faster and steadier now."
        ),
    },
]

import os
import re
import sys
import json
import time
import random
import shutil
import sqlite3
import asyncio
import logging
import difflib
import zipfile
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html import escape as html_escape

import requests
from pypdf import PdfReader
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CommandHandler,
    MessageHandler,
    InlineQueryHandler,
    ContextTypes,
    TypeHandler,
    filters,
)

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("FIGO_DB_PATH") or os.path.join(BASE_DIR, "figo.db")
FILES_DIR = os.environ.get("FIGO_FILES_DIR") or os.path.join(BASE_DIR, "files")
TRASH_DAYS = 30
OCR_AVAILABLE = Image is not None and pytesseract is not None
OCR_ENABLED = os.environ.get(
    "FIGO_OCR", "1" if OCR_AVAILABLE else "0"
).lower() in ("1", "true", "yes")
MCQ_DEFAULT_COUNT = 5
MCQ_MAX_COUNT = 10
BOT_USERNAME = os.environ.get("FIGO_BOT_USERNAME", "").lstrip("@")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)
DIGEST_DEFAULT_HOUR = 8
MAX_PAGE_TEXT = 30000

MUSIC_TMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_music")
MUSIC_AVAILABLE = yt_dlp is not None and shutil.which("ffmpeg") is not None
MUSIC_RESULT_COUNT = 5
MUSIC_PICK_TIMEOUT = 120          # seconds the numbered picker stays valid
MAX_SONG_SECONDS = 20 * 60        # refuse anything longer than this
TELEGRAM_FILE_LIMIT_BYTES = 50 * 1024 * 1024  # Telegram bot upload cap
CHAT_HISTORY_TURNS = 12           # messages kept per user for /chat mode

_storage_chat_id_raw = os.environ.get("FIGO_STORAGE_CHAT_ID", "").strip()
STORAGE_CHAT_ID = int(_storage_chat_id_raw) if _storage_chat_id_raw else None

_announce_chat_id_raw = os.environ.get("FIGO_ANNOUNCE_CHAT_ID", "").strip()
ANNOUNCE_CHAT_ID = int(_announce_chat_id_raw) if _announce_chat_id_raw else None

# Clone identity — set on the process env when this script is running as
# someone's personal clone (see the Cloning section below). When set, the
# clone credits the original bot + developer on its /start message.
ORIGIN_BOT_USERNAME = "figonotebot"
CLONE_DEVELOPER = "tg4mayank"
IS_CLONE = os.environ.get("FIGO_IS_CLONE", "").lower() in ("1", "true", "yes")
CLONES_DIR = os.environ.get("FIGO_CLONES_DIR") or os.path.join(BASE_DIR, "clones")

ADMIN_USER_IDS = {8552325369}

# Bot ownership/creator — shown by /owner and known by the AI chat feature.
BOT_OWNER_NAME = "Mayank"
BOT_OWNER_USERNAME = CLONE_DEVELOPER  # "tg4mayank"

# Process start — used by /uptime. Set once, at import time, so it reflects
# when this specific process (this bot or this clone) actually came up.
PROCESS_START_MONO = time.monotonic()
PROCESS_START_DT = datetime.now(timezone.utc)

os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(MUSIC_TMP_DIR, exist_ok=True)
if not IS_CLONE:
    os.makedirs(CLONES_DIR, exist_ok=True)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("figo")

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_meta(key, default=None):
    conn = get_db()
    row = conn.execute("SELECT value FROM bot_meta WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_meta(key, value):
    conn = get_db()
    conn.execute(
        "INSERT INTO bot_meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            title TEXT,
            content TEXT,
            file_path TEXT,
            created_at TEXT NOT NULL,
            pinned INTEGER DEFAULT 0,
            tags TEXT DEFAULT '',
            deleted_at TEXT DEFAULT NULL,
            priority TEXT DEFAULT 'none',
            auto_tags TEXT DEFAULT ''
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
            title, content, content='items', content_rowid='id'
        );

        CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
            INSERT INTO items_fts(rowid, title, content)
            VALUES (new.id, new.title, new.content);
        END;

        CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
            INSERT INTO items_fts(items_fts, rowid, title, content)
            VALUES ('delete', old.id, old.title, old.content);
        END;

        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            remind_at TEXT NOT NULL,
            sent INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER PRIMARY KEY,
            digest_enabled INTEGER DEFAULT 0,
            digest_mode TEXT DEFAULT 'daily',
            digest_hour INTEGER DEFAULT 8,
            digest_minute INTEGER DEFAULT 0,
            chat_enabled INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS bot_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS clones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL UNIQUE,
            owner_username TEXT,
            bot_token TEXT NOT NULL,
            bot_username TEXT NOT NULL,
            db_path TEXT NOT NULL,
            files_dir TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, name)
        );

        CREATE TABLE IF NOT EXISTS collection_items (
            collection_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            added_at TEXT NOT NULL,
            PRIMARY KEY (collection_id, item_id)
        );
    """)

    # Safe migrations for databases made by older FIGO versions.
    for col_def in (
        "pinned INTEGER DEFAULT 0",
        "tags TEXT DEFAULT ''",
        "deleted_at TEXT DEFAULT NULL",
        "priority TEXT DEFAULT 'none'",
        "auto_tags TEXT DEFAULT ''",
    ):
        try:
            conn.execute(f"ALTER TABLE items ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass

    try:
        conn.execute("ALTER TABLE settings ADD COLUMN chat_enabled INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def is_admin_user(user_id):
    try:
        return int(user_id) in ADMIN_USER_IDS
    except (TypeError, ValueError):
        return False


def is_bot_enabled():
    return str(get_meta("bot_enabled", "1")).strip() != "0"


def set_bot_enabled(enabled):
    set_meta("bot_enabled", "1" if enabled else "0")


def maintenance_notice_text():
    return (
        "⚠️ FIGO is temporarily paused by the admin.\n"
        "Please try again later."
    )


async def require_admin(update, context):
    user = update.effective_user
    if user and is_admin_user(user.id):
        return True
    if update.effective_message:
        await update.effective_message.reply_text("⛔ Admin only.")
    return False


async def maintenance_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or is_admin_user(user.id) or is_bot_enabled():
        return

    if getattr(update, "inline_query", None):
        try:
            await update.inline_query.answer(
                [],
                cache_time=0,
                is_personal=True,
                switch_pm_text="FIGO is temporarily paused",
                switch_pm_parameter="paused",
            )
        except Exception:
            pass
    elif update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=maintenance_notice_text(),
            )
        except Exception:
            pass

    raise ApplicationHandlerStop


def utcnow():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def save_item(user_id, kind, title, content, file_path=None):
    auto_tags = ",".join(compute_auto_tags(f"{title}\n{content}"))
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO items
           (user_id, kind, title, content, file_path, created_at, auto_tags)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, kind, title, content, file_path, iso(utcnow()), auto_tags),
    )
    conn.commit()
    item_id = cur.lastrowid
    conn.close()
    return item_id


def get_item_by_id(user_id, item_id, include_deleted=False):
    conn = get_db()
    query = """SELECT id, user_id, kind, title, content, file_path,
                      created_at, pinned, tags, deleted_at
               FROM items WHERE id = ? AND user_id = ?"""
    params = (item_id, user_id)
    if not include_deleted:
        query += " AND deleted_at IS NULL"
    row = conn.execute(query, params).fetchone()
    conn.close()
    return row


def search_items(user_id, query, limit=15):
    conn = get_db()
    terms, expanded = expand_query_terms(query)
    if not terms:
        conn.close()
        return []

    # FTS gets both the literal words and their variants (so "strengths"
    # still matches a query for "strength"), OR'd together; the app-level
    # re-rank in search_cmd then favors rows containing more of them.
    fts_query = " OR ".join(f'"{t}"' for t in expanded)
    rows = conn.execute(
        """SELECT items.id, items.kind, items.title, items.content,
                  items.created_at
           FROM items_fts
           JOIN items ON items.id = items_fts.rowid
           WHERE items_fts MATCH ?
             AND items.user_id = ?
             AND items.deleted_at IS NULL
           ORDER BY rank
           LIMIT ?""",
        (fts_query, user_id, max(limit, 40)),
    ).fetchall()
    conn.close()
    return smart_rerank(rows, expanded)[:limit]


def list_recent(user_id, limit=10):
    conn = get_db()
    rows = conn.execute(
        """SELECT id, kind, title, created_at
           FROM items
           WHERE user_id = ? AND deleted_at IS NULL
           ORDER BY id DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return rows


def get_random_item(user_id):
    conn = get_db()
    row = conn.execute(
        """SELECT id, kind, title, content, created_at
           FROM items
           WHERE user_id = ? AND deleted_at IS NULL
           ORDER BY RANDOM() LIMIT 1""",
        (user_id,),
    ).fetchone()
    conn.close()
    return row


def get_pinned(user_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT id, kind, title, created_at
           FROM items
           WHERE user_id = ? AND pinned = 1 AND deleted_at IS NULL
           ORDER BY id DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def get_by_tag(user_id, tag):
    conn = get_db()
    rows = conn.execute(
        """SELECT id, kind, title, created_at
           FROM items
           WHERE user_id = ? AND tags = ? AND deleted_at IS NULL
           ORDER BY id DESC""",
        (user_id, tag.lower().strip()),
    ).fetchall()
    conn.close()
    return rows


def stats(user_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT kind, COUNT(*) AS c FROM items
           WHERE user_id = ? AND deleted_at IS NULL GROUP BY kind""",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def soft_delete_items(user_id, ids):
    if not ids:
        return 0
    conn = get_db()
    placeholders = ",".join("?" for _ in ids)
    cur = conn.execute(
        f"""UPDATE items SET deleted_at = ?
            WHERE user_id = ? AND id IN ({placeholders})
              AND deleted_at IS NULL""",
        (iso(utcnow()), user_id, *ids),
    )
    conn.commit()
    count = cur.rowcount
    conn.close()
    return count


def restore_item(user_id, item_id):
    conn = get_db()
    cur = conn.execute(
        """UPDATE items SET deleted_at = NULL
           WHERE id = ? AND user_id = ? AND deleted_at IS NOT NULL""",
        (item_id, user_id),
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def trash_items(user_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT id, kind, title, deleted_at
           FROM items
           WHERE user_id = ? AND deleted_at IS NOT NULL
           ORDER BY deleted_at DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def get_oldest_active(user_id, n):
    conn = get_db()
    rows = conn.execute(
        """SELECT id, file_path FROM items
           WHERE user_id = ? AND deleted_at IS NULL
           ORDER BY id ASC LIMIT ?""",
        (user_id, n),
    ).fetchall()
    conn.close()
    return rows


def get_all_active(user_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT id, kind, title, content, file_path, tags, created_at
           FROM items
           WHERE user_id = ? AND deleted_at IS NULL
           ORDER BY id ASC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def get_recent_days(user_id, days):
    cutoff = iso(utcnow() - timedelta(days=days))
    conn = get_db()
    rows = conn.execute(
        """SELECT id, kind, title, created_at
           FROM items
           WHERE user_id = ? AND created_at >= ? AND deleted_at IS NULL
           ORDER BY id DESC""",
        (user_id, cutoff),
    ).fetchall()
    conn.close()
    return rows


def toggle_pin(user_id, item_id):
    conn = get_db()
    row = conn.execute(
        "SELECT pinned FROM items WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
        (item_id, user_id),
    ).fetchone()
    if row is None:
        conn.close()
        return None
    state = 0 if row["pinned"] else 1
    conn.execute(
        "UPDATE items SET pinned = ? WHERE id = ? AND user_id = ?",
        (state, item_id, user_id),
    )
    conn.commit()
    conn.close()
    return bool(state)


def set_tag(user_id, item_id, tag):
    conn = get_db()
    cur = conn.execute(
        """UPDATE items SET tags = ?
           WHERE id = ? AND user_id = ? AND deleted_at IS NULL""",
        (tag.lower().strip(), item_id, user_id),
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------

PRIORITY_LEVELS = ("low", "medium", "high", "critical")
PRIORITY_ICON = {"low": "🔵", "medium": "🟡", "high": "🟠", "critical": "🔴", "none": "⚪"}


def set_priority(user_id, item_id, level):
    conn = get_db()
    cur = conn.execute(
        """UPDATE items SET priority = ?
           WHERE id = ? AND user_id = ? AND deleted_at IS NULL""",
        (level, item_id, user_id),
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def get_by_priority(user_id, levels):
    conn = get_db()
    placeholders = ",".join("?" for _ in levels)
    rows = conn.execute(
        f"""SELECT id, kind, title, priority, created_at
            FROM items
            WHERE user_id = ? AND deleted_at IS NULL AND priority IN ({placeholders})
            ORDER BY CASE priority
                WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END,
                id DESC""",
        (user_id, *levels),
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Smart auto-tags — lightweight local keyword matching against a small,
# curated vocabulary. No AI call, so this always runs on every save.
# ---------------------------------------------------------------------------

AUTO_TAG_KEYWORDS = {
    "civil": ("concrete", "beam", "structural", "cement", "construction", "surveying", "geotechnical"),
    "programming": ("function", "variable", "algorithm", "python", "javascript", "compiler", "debug", "code", "api"),
    "cybersecurity": ("encryption", "vulnerability", "exploit", "firewall", "malware", "phishing", "penetration"),
    "exam": ("exam", "syllabus", "question paper", "marks", "viva", "semester"),
    "finance": ("invoice", "budget", "expense", "revenue", "tax", "salary", "investment"),
    "medical": ("diagnosis", "symptom", "treatment", "dosage", "patient", "anatomy"),
    "math": ("theorem", "equation", "integral", "derivative", "matrix", "probability"),
    "important": ("urgent", "important", "deadline", "asap", "critical", "must remember"),
}


def compute_auto_tags(text, limit=3):
    text_l = (text or "").lower()
    if not text_l:
        return []
    hits = []
    for tag, keywords in AUTO_TAG_KEYWORDS.items():
        if any(kw in text_l for kw in keywords):
            hits.append(tag)
    return hits[:limit]


# ---------------------------------------------------------------------------
# Collections — user-isolated folders grouping saved items.
# ---------------------------------------------------------------------------

def get_collection(user_id, name):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM collections WHERE user_id = ? AND name = ?",
        (user_id, name.strip().lower()),
    ).fetchone()
    conn.close()
    return row


def create_collection(user_id, name):
    name = name.strip().lower()
    if not name:
        return None, "Collection name can't be empty."
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO collections(user_id, name, created_at) VALUES (?, ?, ?)",
            (user_id, name, iso(utcnow())),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return None, f"You already have a collection named '{name}'."
    row = conn.execute(
        "SELECT * FROM collections WHERE user_id = ? AND name = ?", (user_id, name)
    ).fetchone()
    conn.close()
    return row, None


def list_collections(user_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT c.id, c.name, c.created_at, COUNT(ci.item_id) AS item_count
           FROM collections c
           LEFT JOIN collection_items ci ON ci.collection_id = c.id
           WHERE c.user_id = ?
           GROUP BY c.id
           ORDER BY c.name""",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def add_to_collection(user_id, name, item_id):
    collection = get_collection(user_id, name)
    if not collection:
        return False, f"No collection named '{name}'. Create it first: /collection create {name}"
    item = get_item_by_id(user_id, item_id)
    if not item:
        return False, "No active item with that id."
    conn = get_db()
    conn.execute(
        """INSERT OR IGNORE INTO collection_items(collection_id, item_id, added_at)
           VALUES (?, ?, ?)""",
        (collection["id"], item_id, iso(utcnow())),
    )
    conn.commit()
    conn.close()
    return True, None


def remove_from_collection(user_id, name, item_id):
    collection = get_collection(user_id, name)
    if not collection:
        return False, f"No collection named '{name}'."
    conn = get_db()
    cur = conn.execute(
        "DELETE FROM collection_items WHERE collection_id = ? AND item_id = ?",
        (collection["id"], item_id),
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok, None if ok else "That item wasn't in that collection."


def view_collection(user_id, name):
    collection = get_collection(user_id, name)
    if not collection:
        return None, f"No collection named '{name}'."
    conn = get_db()
    rows = conn.execute(
        """SELECT i.id, i.kind, i.title, i.created_at
           FROM collection_items ci
           JOIN items i ON i.id = ci.item_id
           WHERE ci.collection_id = ? AND i.user_id = ? AND i.deleted_at IS NULL
           ORDER BY ci.added_at DESC""",
        (collection["id"], user_id),
    ).fetchall()
    conn.close()
    return rows, None


def delete_collection(user_id, name):
    collection = get_collection(user_id, name)
    if not collection:
        return False, f"No collection named '{name}'."
    conn = get_db()
    conn.execute("DELETE FROM collection_items WHERE collection_id = ?", (collection["id"],))
    conn.execute("DELETE FROM collections WHERE id = ?", (collection["id"],))
    conn.commit()
    conn.close()
    return True, None


# ---------------------------------------------------------------------------
# Reminders / digest / streak database helpers
# ---------------------------------------------------------------------------

def add_reminder(user_id, item_id, remind_at):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO reminders (user_id, item_id, remind_at, sent)
           VALUES (?, ?, ?, 0)""",
        (user_id, item_id, iso(remind_at)),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def due_reminders():
    conn = get_db()
    rows = conn.execute(
        """SELECT r.id AS reminder_id, r.user_id, r.item_id,
                  r.remind_at, i.kind, i.title, i.content
           FROM reminders r
           JOIN items i ON i.id = r.item_id
           WHERE r.sent = 0 AND r.remind_at <= ?
             AND i.deleted_at IS NULL""",
        (iso(utcnow()),),
    ).fetchall()
    conn.close()
    return rows


def mark_reminder_sent(reminder_id):
    conn = get_db()
    conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()


def get_settings(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM settings WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row


def set_digest(user_id, enabled, mode="daily", hour=8, minute=0):
    conn = get_db()
    conn.execute(
        """INSERT INTO settings(user_id, digest_enabled, digest_mode,
                                digest_hour, digest_minute)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             digest_enabled=excluded.digest_enabled,
             digest_mode=excluded.digest_mode,
             digest_hour=excluded.digest_hour,
             digest_minute=excluded.digest_minute""",
        (user_id, int(enabled), mode, hour, minute),
    )
    conn.commit()
    conn.close()


def digest_users():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM settings WHERE digest_enabled = 1"
    ).fetchall()
    conn.close()
    return rows


def is_chat_enabled(user_id):
    row = get_settings(user_id)
    return bool(row["chat_enabled"]) if row else False


def set_chat_mode(user_id, enabled):
    conn = get_db()
    conn.execute(
        """INSERT INTO settings(user_id, chat_enabled)
           VALUES (?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             chat_enabled=excluded.chat_enabled""",
        (user_id, int(enabled)),
    )
    conn.commit()
    conn.close()


def save_activity(user_id, when=None):
    # Activity is derived from created_at, so no separate streak table is needed.
    return


def current_streak(user_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT DISTINCT substr(created_at, 1, 10) AS d
           FROM items
           WHERE user_id = ? AND deleted_at IS NULL
           ORDER BY d DESC""",
        (user_id,),
    ).fetchall()
    conn.close()

    if not rows:
        return 0

    dates = {r["d"] for r in rows}
    today = utcnow().date()
    if today.isoformat() not in dates:
        today -= timedelta(days=1)

    streak = 0
    while today.isoformat() in dates:
        streak += 1
        today -= timedelta(days=1)
    return streak


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

async def purge_expired_trash(bot=None):
    cutoff = iso(utcnow() - timedelta(days=TRASH_DAYS))
    conn = get_db()
    rows = conn.execute(
        """SELECT id, file_path FROM items
           WHERE deleted_at IS NOT NULL AND deleted_at < ?""",
        (cutoff,),
    ).fetchall()

    for row in rows:
        ref = parse_storage_ref(row["file_path"])
        if ref and bot:
            file_id, message_id = ref
            try:
                await bot.delete_message(chat_id=STORAGE_CHAT_ID, message_id=message_id)
            except Exception as e:
                log.warning("Could not delete archived message %s: %s", message_id, e)
        elif row["file_path"] and not ref and os.path.exists(row["file_path"]):
            try:
                os.remove(row["file_path"])
            except OSError:
                pass

    if rows:
        ids = [r["id"] for r in rows]
        placeholders = ",".join("?" for _ in ids)
        conn.execute(
            f"DELETE FROM items WHERE id IN ({placeholders})", ids
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def snippet(text, length=140):
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    return text[:length] + ("…" if len(text) > length else "")


def safe_filename(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


# ---------------------------------------------------------------------------
# Cyberpunk text styling — converts plain ASCII letters/digits into Unicode
# "fonts" so headers and status lines stand out in Telegram (no real bold/
# monospace markup needed — these are just different Unicode codepoints).
# ---------------------------------------------------------------------------

_BOLD_CAP = {chr(65 + i): chr(0x1D400 + i) for i in range(26)}          # A-Z -> 𝐀-𝐙
_SMALLCAPS = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ꜰ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
}
_MONO_UPPER = {chr(65 + i): chr(0x1D670 + i) for i in range(26)}         # A-Z -> 𝙰-𝚉
_MONO_LOWER = {chr(97 + i): chr(0x1D68A + i) for i in range(26)}         # a-z -> 𝚊-𝚣
_MONO_DIGIT = {chr(48 + i): chr(0x1D7F6 + i) for i in range(10)}         # 0-9 -> 𝟶-𝟿


def to_bold_smallcaps(text):
    """'Make me good boy' -> '𝐌ᴀᴋᴇ 𝐌ᴇ 𝐆ᴏᴏᴅ 𝐁ᴏʏ'. Used for headers/titles:
    first letter of each word goes bold-capital, the rest go small-caps.
    """
    words = text.split(" ")
    out = []
    for w in words:
        if not w:
            out.append(w)
            continue
        first, rest = w[0], w[1:]
        styled_first = _BOLD_CAP.get(first.upper(), first) if first.isalpha() else first
        styled_rest = "".join(
            _SMALLCAPS.get(c.lower(), c) if c.isalpha() else c for c in rest
        )
        out.append(styled_first + styled_rest)
    return " ".join(out)


def to_cyber_mono(text):
    """'Pinging...' -> '𝙿𝚒𝚗𝚐𝚒𝚗𝚐...'. Used for status/progress lines —
    converts letters and digits to bold monospace, leaves everything else
    (emoji, punctuation, ellipses, non-Latin text) untouched.
    """
    out = []
    for c in text:
        out.append(_MONO_UPPER.get(c) or _MONO_LOWER.get(c) or _MONO_DIGIT.get(c) or c)
    return "".join(out)


def parse_when(text):
    """
    Supports:
      2026-08-08 21:30
      2026-08-08T21:30
      tomorrow 9am
      tomorrow 21:30
      today 18:00
      in 30m / in 2h / in 1d
    Naive times are interpreted in IST because the bot is intended for India.
    """
    raw = text.strip().lower()
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)

    m = re.fullmatch(r"in\s+(\d+)\s*([mhd])", raw)
    if m:
        value = int(m.group(1))
        unit = m.group(2)
        delta = {"m": timedelta(minutes=value),
                 "h": timedelta(hours=value),
                 "d": timedelta(days=value)}[unit]
        return now + delta

    raw2 = raw.replace(" at ", " ").replace("  ", " ").strip()

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %I:%M%p",
                "%Y-%m-%d %I%p", "%Y-%m-%d %H"):
        try:
            return datetime.strptime(raw2, fmt).replace(tzinfo=ist)
        except ValueError:
            pass

    day_offset = None
    if raw2.startswith("tomorrow"):
        day_offset = 1
        time_part = raw2[len("tomorrow"):].strip()
    elif raw2.startswith("today"):
        day_offset = 0
        time_part = raw2[len("today"):].strip()
    else:
        time_part = raw2

    if day_offset is not None:
        if not time_part:
            hour, minute = 9, 0
        else:
            t = time_part.replace(" ", "")
            parsed = None
            for fmt in ("%I:%M%p", "%I%p", "%H:%M", "%H"):
                try:
                    parsed = datetime.strptime(t, fmt)
                    break
                except ValueError:
                    pass
            if parsed is None:
                return None
            hour, minute = parsed.hour, parsed.minute
        return (now + timedelta(days=day_offset)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )

    return None


def fetch_page(url):
    """Fetch readable page title + text for link indexing."""
    try:
        resp = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; FigoBot/1.0)"},
        )
        resp.raise_for_status()
        html = resp.text

        if BeautifulSoup:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript", "svg"]):
                tag.decompose()
            title = soup.title.get_text(" ", strip=True) if soup.title else url
            text = soup.get_text(" ", strip=True)
            text = re.sub(r"\s+", " ", text)
        else:
            m = re.search(r"<title[^>]*>(.*?)</title>", html,
                          re.I | re.S)
            title = re.sub(r"\s+", " ", m.group(1)).strip() if m else url
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text)

        return title[:200], text[:MAX_PAGE_TEXT]
    except Exception as e:
        log.info("Page scraping failed for %s: %s", url, e)
        return url, ""


def extract_pdf_text(path, max_chars=30000):
    parts = []
    try:
        reader = PdfReader(path)
        total = 0
        for page in reader.pages:
            text = page.extract_text() or ""
            parts.append(text)
            total += len(text)
            if total >= max_chars:
                break
    except Exception as e:
        log.warning("PDF extraction failed for %s: %s", path, e)
    return "\n".join(parts)[:max_chars]


def extract_docx_text(path, max_chars=30000):
    """Word documents are a zip of XML — no extra dependency needed."""
    try:
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        with zipfile.ZipFile(path) as z:
            xml_bytes = z.read("word/document.xml")
        root = ET.fromstring(xml_bytes)
        parts = []
        for para in root.iter(f"{ns}p"):
            texts = [node.text for node in para.iter(f"{ns}t") if node.text]
            if texts:
                parts.append("".join(texts))
        return "\n".join(parts)[:max_chars]
    except Exception as e:
        log.warning("DOCX extraction failed for %s: %s", path, e)
        return ""


def extract_pptx_text(path, max_chars=30000):
    """PowerPoint files are also a zip of per-slide XML."""
    try:
        ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        parts = []
        with zipfile.ZipFile(path) as z:
            slide_names = sorted(
                (n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                key=lambda n: int(re.search(r"\d+", n).group()),
            )
            for name in slide_names:
                root = ET.fromstring(z.read(name))
                texts = [node.text for node in root.iter(f"{ns}t") if node.text]
                if texts:
                    parts.append(" ".join(texts))
        return "\n".join(parts)[:max_chars]
    except Exception as e:
        log.warning("PPTX extraction failed for %s: %s", path, e)
        return ""


def extract_html_text(path, max_chars=30000):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        if BeautifulSoup:
            text = BeautifulSoup(html, "html.parser").get_text("\n")
        else:
            text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text[:max_chars]
    except Exception as e:
        log.warning("HTML extraction failed for %s: %s", path, e)
        return ""


def extract_plain_text(path, max_chars=30000):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()[:max_chars]
    except Exception as e:
        log.warning("Plain-text extraction failed for %s: %s", path, e)
        return ""


# Extensions read directly as text/code — content is extracted and indexed
# the same way a PDF's text is, so /search, /tldr and /mcq all work on them.
PLAIN_TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".cs", ".go", ".rs",
    ".rb", ".php", ".sh", ".bash", ".sql", ".json", ".yaml", ".yml", ".xml",
    ".csv", ".tsv", ".md", ".txt", ".log", ".ini", ".cfg", ".toml", ".css",
}


def extract_document_text(path, filename, mime_type=None, max_chars=30000):
    """Dispatch text extraction by file extension, so saved files other
    than PDFs are still readable, searchable, and summarizable. Unknown
    extensions still get stored as a file — they just won't have
    extracted/indexed text."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf" or mime_type == "application/pdf":
        return extract_pdf_text(path, max_chars)
    if ext == ".docx":
        return extract_docx_text(path, max_chars)
    if ext == ".pptx":
        return extract_pptx_text(path, max_chars)
    if ext in (".html", ".htm"):
        return extract_html_text(path, max_chars)
    if ext in PLAIN_TEXT_EXTENSIONS:
        return extract_plain_text(path, max_chars)
    return ""


def ocr_image(path):
    if not OCR_ENABLED or Image is None or pytesseract is None:
        return ""
    try:
        return pytesseract.image_to_string(Image.open(path)).strip()[:30000]
    except Exception as e:
        log.warning("OCR failed for %s: %s", path, e)
        return ""


# ---------------------------------------------------------------------------
# Off-device storage: archive files to a Telegram group/channel instead of
# keeping them on disk. Enabled by setting FIGO_STORAGE_CHAT_ID.
# ---------------------------------------------------------------------------

def make_storage_ref(file_id, message_id):
    return f"tg:{file_id}:{message_id}"


def parse_storage_ref(file_path):
    """Return (file_id, message_id) if file_path is a storage-channel
    reference, else None. Refs look like 'tg:<file_id>:<message_id>'."""
    if not file_path or not file_path.startswith("tg:"):
        return None
    rest, _, message_id = file_path.rpartition(":")
    file_id = rest[len("tg:"):]
    if not file_id or not message_id.isdigit():
        return None
    return file_id, int(message_id)


async def archive_to_storage(context, source_message):
    """Forward a message (with a photo/document) to the storage channel and
    return a 'tg:<file_id>:<message_id>' reference, or None if storage isn't
    configured or the forward fails.
    """
    if not STORAGE_CHAT_ID:
        return None
    try:
        forwarded = await context.bot.forward_message(
            chat_id=STORAGE_CHAT_ID,
            from_chat_id=source_message.chat_id,
            message_id=source_message.message_id,
        )
        if forwarded.document:
            file_id = forwarded.document.file_id
        elif forwarded.photo:
            file_id = forwarded.photo[-1].file_id
        else:
            return None
        return make_storage_ref(file_id, forwarded.message_id)
    except Exception as e:
        log.warning("Could not archive to storage channel: %s", e)
        return None


# ---------------------------------------------------------------------------
# Music search / download (YouTube via yt-dlp)
# ---------------------------------------------------------------------------

def fmt_duration(seconds):
    if not seconds:
        return "?:??"
    seconds = int(seconds)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def search_youtube(query, limit=MUSIC_RESULT_COUNT):
    """Search YouTube without downloading anything. Returns a list of dicts."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)

    results = []
    for entry in (info or {}).get("entries") or []:
        if not entry or not entry.get("id"):
            continue
        results.append({
            "id": entry["id"],
            "title": entry.get("title") or "Untitled",
            "uploader": entry.get("uploader") or entry.get("channel") or "",
            "duration": entry.get("duration"),
        })
    return results


def download_audio(video_id, out_dir):
    """Download a single video's audio as mp3. Blocking — run via to_thread."""
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(out_dir, "%(id)s.%(epoch)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": TELEGRAM_FILE_LIMIT_BYTES,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            f"https://www.youtube.com/watch?v={video_id}", download=True
        )
        raw_path = ydl.prepare_filename(info)

    mp3_path = os.path.splitext(raw_path)[0] + ".mp3"
    if not os.path.exists(mp3_path):
        raise FileNotFoundError("Audio conversion did not produce an mp3 file")
    return mp3_path, info


def purge_music_tmp():
    """Remove any leftover downloads (e.g. from a crash mid-send) on startup."""
    if not os.path.isdir(MUSIC_TMP_DIR):
        return
    for name in os.listdir(MUSIC_TMP_DIR):
        path = os.path.join(MUSIC_TMP_DIR, name)
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError as e:
            log.warning("Could not remove stray music file %s: %s", path, e)


def similarity(a, b):
    a = re.sub(r"\s+", " ", (a or "").lower()).strip()
    b = re.sub(r"\s+", " ", (b or "").lower()).strip()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if len(a) > 5000:
        a = a[:5000]
    if len(b) > 5000:
        b = b[:5000]
    return difflib.SequenceMatcher(None, a, b).ratio()


def find_duplicate(user_id, title, content):
    """Warn at >= 90% similarity, without blocking the save."""
    conn = get_db()
    rows = conn.execute(
        """SELECT id, kind, title, content
           FROM items
           WHERE user_id = ? AND deleted_at IS NULL
           ORDER BY id DESC LIMIT 100""",
        (user_id,),
    ).fetchall()
    conn.close()

    best = None
    best_score = 0.0
    candidate = f"{title}\n{content}"
    for row in rows:
        score = similarity(candidate, f"{row['title']}\n{row['content']}")
        if score > best_score:
            best_score = score
            best = row
    return best, best_score


def get_related_items(user_id, item_id, title, content, limit=3, min_score=0.28):
    """Find other active items in the same user's vault that resemble this
    one — used by /view's 'Related' section. Never crosses user_id, so it
    can't leak another user's content."""
    conn = get_db()
    rows = conn.execute(
        """SELECT id, kind, title, content
           FROM items
           WHERE user_id = ? AND deleted_at IS NULL AND id != ?
           ORDER BY id DESC LIMIT 200""",
        (user_id, item_id),
    ).fetchall()
    conn.close()

    candidate = f"{title}\n{content}"
    scored = []
    for row in rows:
        score = similarity(candidate, f"{row['title']}\n{row['content']}")
        if score >= min_score:
            scored.append((score, row))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [row for _, row in scored[:limit]]


# ---------------------------------------------------------------------------
# Lightweight "smart" search — FTS5 keyword search doesn't catch a query
# like "concrete strength" matching content that says "compressive strength
# of concrete" (different word order / phrasing, same meaning). There's no
# embeddings model available here, so this expands the query into likely
# word variants (plurals, common suffixes) and re-ranks FTS results by how
# much of the (expanded) query vocabulary actually appears nearby in the
# text, rather than relying purely on FTS5's own ranking. It's a heuristic,
# not true semantic search, but it noticeably improves near-miss phrasing.
# ---------------------------------------------------------------------------

_SUFFIXES = ("ing", "ed", "es", "s", "ive", "ion", "ions", "al", "ally")


def _word_variants(word):
    variants = {word}
    for suf in _SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            variants.add(word[: -len(suf)])
    if len(word) >= 3:
        variants.add(word + "s")
    return variants


def expand_query_terms(query):
    terms = re.findall(r"\w+", query.lower())
    expanded = set()
    for t in terms:
        expanded |= _word_variants(t)
    return terms, expanded


def smart_rerank(rows, expanded_terms):
    """Re-score already-matched FTS rows by how many expanded query terms
    (including near-variants) actually appear in each row's text, so a item
    using different phrasing of the same words ranks appropriately."""
    scored = []
    for row in rows:
        text_l = f"{row['title']}\n{row['content']}".lower()
        hits = sum(1 for t in expanded_terms if t in text_l)
        scored.append((hits, row))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [row for _, row in scored]


def local_summary(text, max_sentences=4):
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return "There is no text available to summarize."

    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    # Lightweight extractive summary: prioritize longer information-rich sentences.
    scored = []
    words = re.findall(r"\b\w+\b", text.lower())
    freq = {}
    for w in words:
        if len(w) > 3:
            freq[w] = freq.get(w, 0) + 1

    for idx, sentence in enumerate(sentences):
        sw = re.findall(r"\b\w+\b", sentence.lower())
        score = sum(freq.get(w, 0) for w in sw if len(w) > 3)
        score /= max(1, len(sw))
        scored.append((score, idx, sentence))

    chosen = sorted(scored, reverse=True)[:max_sentences]
    chosen.sort(key=lambda x: x[1])
    return " ".join(x[2] for x in chosen)


def call_gemini(prompt_or_history, system=None, json_mode=False):
    """Call Gemini's free-tier REST API. Blocking — always run via
    asyncio.to_thread. `prompt_or_history` is either a plain string
    (single-turn) or a list of {"role": "user"|"assistant", "content": str}
    dicts (multi-turn chat).
    """
    if isinstance(prompt_or_history, str):
        contents = [{"role": "user", "parts": [{"text": prompt_or_history}]}]
    else:
        contents = [
            {
                "role": "model" if turn["role"] == "assistant" else "user",
                "parts": [{"text": turn["content"]}],
            }
            for turn in prompt_or_history
        ]

    payload = {"contents": contents}
    if system:
        payload["system_instruction"] = {"parts": [{"text": system}]}
    if json_mode:
        payload["generationConfig"] = {"response_mime_type": "application/json"}

    resp = requests.post(
        GEMINI_URL,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def ai_summary(text):
    if not GEMINI_API_KEY:
        return local_summary(text)

    try:
        return call_gemini(
            "Summarize the following note in 4 concise bullet points. "
            "Keep important facts and do not invent information.\n\n" + text[:50000]
        )
    except Exception as e:
        log.warning("AI summary failed; using local summary: %s", e)
        return local_summary(text)


def local_mcq(text, n):
    """Heuristic MCQ generator used when no Gemini key is configured.

    Picks information-rich sentences, blanks out a distinctive keyword, and
    builds distractor options from other keywords found in the same text.
    """
    text = re.sub(r"\s+", " ", text or "").strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    sentences = [s for s in sentences if len(s.split()) >= 6]
    if not sentences:
        return []

    words = re.findall(r"\b[A-Za-z]{4,}\b", text)
    stop = {
        "this", "that", "with", "from", "have", "were", "been", "they",
        "their", "which", "about", "would", "could", "should", "there",
        "these", "those", "when", "where", "into", "your", "also", "than",
    }
    freq = {}
    for w in words:
        lw = w.lower()
        if lw not in stop:
            freq[lw] = freq.get(lw, 0) + 1

    vocab = [w for w, c in freq.items() if c >= 1]
    if len(vocab) < 4:
        return []

    used_sentences = set()
    questions = []
    for sentence in sorted(sentences, key=lambda s: -len(s)):
        if len(questions) >= n or sentence in used_sentences:
            continue
        sw = re.findall(r"\b[A-Za-z]{4,}\b", sentence)
        candidates = [w for w in sw if w.lower() in freq and w.lower() not in stop]
        if not candidates:
            continue
        answer = max(candidates, key=lambda w: freq[w.lower()])

        blanked = re.sub(rf"\b{re.escape(answer)}\b", "_____", sentence, count=1)
        if blanked == sentence:
            continue

        distractor_pool = [
            w for w in vocab
            if w != answer.lower() and abs(len(w) - len(answer)) <= 4
        ]
        if len(distractor_pool) < 3:
            distractor_pool = [w for w in vocab if w != answer.lower()]
        if len(distractor_pool) < 3:
            continue

        distractors = list(dict.fromkeys(distractor_pool))
        random.shuffle(distractors)
        distractors = distractors[:3]

        options = distractors + [answer.lower()]
        random.shuffle(options)
        correct_index = options.index(answer.lower())

        questions.append({
            "question": blanked,
            "options": [o.capitalize() for o in options],
            "correct_index": correct_index,
        })
        used_sentences.add(sentence)

    return questions


def ai_mcq(text, n):
    if not GEMINI_API_KEY:
        return local_mcq(text, n)

    try:
        raw = call_gemini(
            f"Create exactly {n} multiple-choice questions testing "
            "understanding of the following note. Each question must have "
            "4 options with exactly one correct answer. Do not invent facts "
            "not present in the text.\n\n"
            "Respond ONLY with JSON, no preamble or markdown fences, matching "
            'this shape: {"questions": [{"question": str, "options": '
            '[str, str, str, str], "correct_index": int}]}\n\n'
            "Note:\n" + text[:50000],
            json_mode=True,
        )
        raw = re.sub(r"^```json|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        data = json.loads(raw)
        questions = data.get("questions", [])
        cleaned = []
        for q in questions[:n]:
            opts = q.get("options") or []
            idx = q.get("correct_index")
            if q.get("question") and len(opts) == 4 and isinstance(idx, int) and 0 <= idx < 4:
                cleaned.append({
                    "question": q["question"],
                    "options": opts,
                    "correct_index": idx,
                })
        return cleaned or local_mcq(text, n)
    except Exception as e:
        log.warning("AI MCQ generation failed; using local generator: %s", e)
        return local_mcq(text, n)


def format_mcq(questions):
    letters = ["A", "B", "C", "D"]
    lines = []
    for i, q in enumerate(questions, start=1):
        lines.append(f"{i}. {q['question']}")
        for letter, opt in zip(letters, q["options"]):
            lines.append(f"   {letter}) {opt}")
        lines.append("")

    lines.append("🔑 Answers")
    lines.append(
        ", ".join(
            f"{i}-{letters[q['correct_index']]}"
            for i, q in enumerate(questions, start=1)
        )
    )
    return "\n".join(lines)


CHAT_SYSTEM_PROMPT = (
    "You are FIGO, a warm, casual, human-sounding assistant chatting "
    "with your owner inside their personal Telegram knowledge-vault bot. "
    "Keep replies natural and conversational — usually just a few "
    "sentences, not a wall of text. If they mention wanting to save or "
    "remember something, remind them to use /note <text>. If asked who "
    "made you, who your creator/developer/owner is, or who built this bot, "
    "answer that Mayank created you — that's the true, correct answer, and "
    "there's no need to hedge or guess about it."
)


async def handle_chat_message(update, context, text):
    history = context.user_data.setdefault("chat_history", [])
    history.append({"role": "user", "content": text})
    del history[:-CHAT_HISTORY_TURNS]

    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )
        reply = await asyncio.to_thread(
            call_gemini, history, system=CHAT_SYSTEM_PROMPT
        )
    except Exception as e:
        log.warning("AI chat reply failed: %s", e)
        reply = "Hmm, I couldn't come up with a reply just now — try again in a bit."

    history.append({"role": "assistant", "content": reply})
    del history[:-CHAT_HISTORY_TURNS]
    await areply(update, context, reply)


async def areply(update, context, text):
    """Drop-in replacement for `update.message.reply_text` that chunks text
    over Telegram's 4096-char limit. Returns the last Message object sent,
    like reply_text does.
    """
    text = text or ""
    if not text:
        return None

    chat_id = update.effective_chat.id
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)] or [text]

    last_sent = None
    for chunk in chunks:
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        except Exception:
            pass
        last_sent = await update.message.reply_text(chunk)
    return last_sent


async def asend(bot, chat_id, text):
    """Same as areply, for background jobs that only have a Bot + chat_id
    (reminders, digests) rather than an Update to reply to.
    """
    text = text or ""
    if not text:
        return None
    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass
    return await bot.send_message(chat_id=chat_id, text=text[:4000])


async def send_long_text(update, context, text):
    await areply(update, context, text)


# ---------------------------------------------------------------------------
# Activity log — posts a status line to the storage/log group for every
# major event (startup, new user, saves, downloads, sends) so you can watch
# the bot working from inside Telegram. Uses the same FIGO_STORAGE_CHAT_ID
# group as off-device file storage. No-ops silently if it isn't set.
# ---------------------------------------------------------------------------

async def alog_bot(bot, text):
    if not STORAGE_CHAT_ID:
        return
    try:
        await bot.send_message(chat_id=STORAGE_CHAT_ID, text=text)
    except Exception as e:
        log.warning("Could not send log message to storage group (%s): %s",
                    STORAGE_CHAT_ID, e)


async def alog(context, text):
    await alog_bot(context.bot, text)


async def get_bot_avatar_file_id(context):
    """Fetch (and cache) the bot's own profile photo, set via BotFather."""
    cached = context.bot_data.get("avatar_file_id")
    if cached:
        return cached
    try:
        photos = await context.bot.get_user_profile_photos(context.bot.id, limit=1)
        if photos.total_count > 0:
            file_id = photos.photos[0][-1].file_id  # highest-resolution size
            context.bot_data["avatar_file_id"] = file_id
            return file_id
    except Exception as e:
        log.warning("Could not fetch bot avatar: %s", e)
    return None


async def send_branded(update, context, text):
    """Send `text` as the bot's reply with its profile photo attached.
    Falls back to a plain text reply if the bot has no profile photo set.
    """
    avatar = await get_bot_avatar_file_id(context)
    if not avatar:
        await areply(update, context, text)
        return

    try:
        if len(text) <= 1024:
            await update.message.reply_photo(photo=avatar, caption=text)
            return
        await update.message.reply_photo(photo=avatar)
        await areply(update, context, text)
    except Exception as e:
        log.warning("Could not send branded reply: %s", e)
        await areply(update, context, text)


def icons():
    return {"note": "📝", "link": "🔗", "pdf": "📄", "doc": "📑", "photo": "🖼️"}


# ---------------------------------------------------------------------------
# Cloning — lets anyone spin up their own fully independent FIGO bot by
# giving /clone their own bot token from @BotFather. Each clone runs as a
# separate OS process with its own token, database, and files directory, so
# vaults never mix between different clone owners or with this hub bot.
# Registered clones live in the `clones` table and are respawned on startup
# if their process isn't already running (e.g. after a device reboot).
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(r"^\d{6,}:[A-Za-z0-9_-]{30,}$")
_clone_processes = {}   # clone db id -> subprocess.Popen, this-process-only cache


def _clone_pid_file(clone_id):
    return os.path.join(CLONES_DIR, f"{clone_id}.pid")


def _pid_is_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def spawn_clone_process(clone_row):
    """Launch clone_row as an independent bot.py process with its own
    token, database, and files directory. clone_row needs: id, bot_token,
    bot_username, db_path, files_dir."""
    env = os.environ.copy()
    env["BOT_TOKEN"] = clone_row["bot_token"]
    env["FIGO_DB_PATH"] = clone_row["db_path"]
    env["FIGO_FILES_DIR"] = clone_row["files_dir"]
    env["FIGO_BOT_USERNAME"] = clone_row["bot_username"]
    env["FIGO_IS_CLONE"] = "1"
    # Clone owners configure their own storage/announcement chats from
    # inside their own clone (with /chatid) — don't inherit the hub's.
    env.pop("FIGO_STORAGE_CHAT_ID", None)
    env.pop("FIGO_ANNOUNCE_CHAT_ID", None)

    os.makedirs(clone_row["files_dir"], exist_ok=True)
    log_path = os.path.join(CLONES_DIR, f"{clone_row['bot_username']}.log")
    log_file = open(log_path, "a")
    proc = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__)],
        env=env, stdout=log_file, stderr=subprocess.STDOUT, cwd=BASE_DIR,
    )
    log_file.close()  # child holds its own duplicated fd; parent doesn't need this open
    with open(_clone_pid_file(clone_row["id"]), "w") as f:
        f.write(str(proc.pid))
    _clone_processes[clone_row["id"]] = proc
    return proc


def stop_clone_process(clone_row):
    proc = _clone_processes.pop(clone_row["id"], None)
    if proc and proc.poll() is None:
        proc.terminate()
    pid_file = _clone_pid_file(clone_row["id"])
    if not proc and os.path.exists(pid_file):
        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, 15)
        except (OSError, ValueError) as e:
            log.warning("Could not stop clone process for @%s: %s", clone_row["bot_username"], e)
    if os.path.exists(pid_file):
        try:
            os.remove(pid_file)
        except OSError:
            pass


async def resume_clones():
    """Called on hub startup — respawns any registered active clone whose
    process isn't already running."""
    if IS_CLONE:
        return  # clones never manage sub-clones
    conn = get_db()
    rows = conn.execute("SELECT * FROM clones WHERE status = 'active'").fetchall()
    conn.close()
    for row in rows:
        pid_file = _clone_pid_file(row["id"])
        alive = False
        if os.path.exists(pid_file):
            try:
                with open(pid_file) as f:
                    alive = _pid_is_alive(int(f.read().strip()))
            except (OSError, ValueError):
                alive = False
        if not alive:
            try:
                spawn_clone_process(row)
                log.info("Resumed clone @%s", row["bot_username"])
            except Exception as e:
                log.warning("Could not resume clone @%s: %s", row["bot_username"], e)


def clone_runtime_state(row):
    proc = _clone_processes.get(row["id"])
    if proc and proc.poll() is None:
        return "running"

    pid_file = _clone_pid_file(row["id"])
    if os.path.exists(pid_file):
        try:
            with open(pid_file) as f:
                if _pid_is_alive(int(f.read().strip())):
                    return "running"
        except (OSError, ValueError):
            pass

    return "stopped" if row["status"] != "active" else "down"


def get_clone_admin_rows():
    conn = get_db()
    rows = conn.execute("SELECT * FROM clones ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows


def get_clone_admin(identifier):
    ident = (identifier or "").strip().lstrip("@")
    if not ident:
        return None

    conn = get_db()
    row = None
    if ident.isdigit():
        row = conn.execute("SELECT * FROM clones WHERE id = ?", (int(ident),)).fetchone()
        if not row:
            row = conn.execute(
                "SELECT * FROM clones WHERE owner_user_id = ?",
                (int(ident),),
            ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM clones WHERE lower(bot_username) = ?",
            (ident.lower(),),
        ).fetchone()
    conn.close()
    return row


def delete_clone_artifacts(row):
    clone_root = os.path.abspath(os.path.dirname(row["db_path"]))
    if os.path.isdir(clone_root):
        shutil.rmtree(clone_root, ignore_errors=True)
    else:
        try:
            if os.path.isfile(row["db_path"]):
                os.remove(row["db_path"])
        except OSError:
            pass
        try:
            if os.path.isdir(row["files_dir"]):
                shutil.rmtree(row["files_dir"], ignore_errors=True)
        except OSError:
            pass

    for extra in (
        os.path.join(CLONES_DIR, f"{row['bot_username']}.log"),
        _clone_pid_file(row["id"]),
    ):
        try:
            if os.path.exists(extra):
                os.remove(extra)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first_name = (user.first_name or "there").strip()
    welcome = (
        "𝐅ɪɢᴏ 𝐁ᴏᴛ 📖\n\n"
        f"Hey {first_name}, welcome! 👋\n\n"
        "I'm your personal knowledge vault — send me notes, links, files "
        "(PDF/DOCX/PPTX/HTML/code) or photos and I'll save, organize, and "
        "make them searchable, no setup needed.\n\n"
        "A few things to try:\n"
        "• Just send anything — it's saved automatically\n"
        "• /search <words> — find something in your vault\n"
        "• /tldr <id> — get an instant summary\n"
        "• /remind <id> <when> — never forget an item\n\n"
        "Use /help to browse everything, or /owner to see who built me."
    )
    if IS_CLONE:
        welcome += f"\n\n🄲 This is a clone of @{ORIGIN_BOT_USERNAME}."
    else:
        welcome += "\n\nWant your own private copy? /clone <bot_token>"
    await send_branded(update, context, welcome)
    await alog(
        context,
        f"👤 New session: {user.full_name} "
        f"(@{user.username or '—'}, id {user.id}) started the bot."
    )


async def group_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.bot.id
    for member in update.message.new_chat_members:
        if member.id == bot_id:
            await areply(
                update, context,
                "𝐅ɪɢᴏ 𝐁ᴏᴛ 📖\n\n"
                "Thanks for adding me! Send links/files/photos here to save "
                "them. Use /note <text> for intentional text saves.\n"
                "Your vault stays private to your Telegram account.\n\n"
                "/help for everything I can do, /owner for who built me."
            )
            break


async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    started = time.monotonic()
    sent = await update.message.reply_text(to_cyber_mono("🏓 Pinging…"))
    api_ms = int((time.monotonic() - started) * 1000)

    bot_latency_ms = None
    if update.message.date:
        delta = datetime.now(timezone.utc) - update.message.date.astimezone(timezone.utc)
        bot_latency_ms = int(delta.total_seconds() * 1000)

    text = f"🏓 Pong! {api_ms}ms"
    if bot_latency_ms is not None:
        text += f"\n📡 Message → bot: {bot_latency_ms}ms"
    await sent.edit_text(text)


def format_duration(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


async def uptime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    elapsed = time.monotonic() - PROCESS_START_MONO
    since = PROCESS_START_DT.strftime("%Y-%m-%d %H:%M UTC")
    text = f"⏱️ Up for {format_duration(elapsed)}\nRunning since {since}"
    if IS_CLONE:
        text += f"\n🄲 This is a clone of @{ORIGIN_BOT_USERNAME}."
    await areply(update, context, text)


async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"👑 This bot was created and is maintained by {BOT_OWNER_NAME} "
        f"(@{BOT_OWNER_USERNAME}).\n\n"
        "Reach out there for questions, feedback, or issues."
    )
    if IS_CLONE:
        text += (
            f"\n\nThis particular clone was set up by its own owner using "
            f"/clone — the original bot is @{ORIGIN_BOT_USERNAME}."
        )
    await areply(update, context, text)


async def chatid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    text = f"🆔 This chat's ID: `{chat.id}`\nType: {chat.type}"
    if chat.type in ("group", "supergroup"):
        text += (
            "\n\nTo use this as your storage/log group, set on the server:\n"
            f"export FIGO_STORAGE_CHAT_ID=\"{chat.id}\""
        )
    elif chat.type == "channel":
        text += (
            "\n\nTo use this as your announcement channel, set on the server:\n"
            f"export FIGO_ANNOUNCE_CHAT_ID=\"{chat.id}\"\n"
            "(the bot must be an admin here to post)"
        )
    await update.effective_message.reply_text(text, parse_mode="Markdown")


async def clone_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if IS_CLONE:
        await areply(
            update, context,
            f"This is already a clone — clone the original @{ORIGIN_BOT_USERNAME} instead."
        )
        return
    if update.effective_chat.type != "private":
        await areply(
            update, context,
            "For your token's safety, send /clone in a private chat with me, not a group."
        )
        return

    token = " ".join(context.args).strip()
    if not token or not TOKEN_RE.match(token):
        await areply(
            update, context,
            "Usage: /clone <bot_token>\n\n"
            "Get a token from @BotFather on Telegram (send it /newbot), then "
            "send that token here. I'll spin up your own private copy of this "
            "bot — your own vault, your own storage group, everything "
            "completely separate from mine."
        )
        return

    user = update.effective_user
    conn = get_db()
    dup = conn.execute(
        "SELECT id FROM clones WHERE bot_token = ? AND owner_user_id != ?",
        (token, user.id),
    ).fetchone()
    if dup:
        conn.close()
        await areply(update, context, "That token is already registered to a clone here.")
        return

    status = await areply(update, context, to_cyber_mono("🔍 Verifying token…"))
    try:
        resp = await asyncio.to_thread(
            requests.get, f"https://api.telegram.org/bot{token}/getMe", timeout=15
        )
        data = resp.json()
    except Exception as e:
        conn.close()
        await status.edit_text(f"Couldn't reach Telegram to verify that token: {e}")
        return

    if not data.get("ok"):
        conn.close()
        await status.edit_text(
            "That doesn't look like a valid bot token. Double-check it "
            "against @BotFather and try again."
        )
        return

    bot_username = data["result"]["username"]
    clone_dir = os.path.join(CLONES_DIR, f"{user.id}_{bot_username}")
    db_path = os.path.join(clone_dir, "figo.db")
    files_dir = os.path.join(clone_dir, "files")
    os.makedirs(clone_dir, exist_ok=True)

    existing = conn.execute(
        "SELECT * FROM clones WHERE owner_user_id = ?", (user.id,)
    ).fetchone()
    now = datetime.now(timezone.utc).isoformat()
    if existing:
        stop_clone_process(existing)
        conn.execute(
            "UPDATE clones SET bot_token=?, bot_username=?, db_path=?, "
            "files_dir=?, status='active', owner_username=? WHERE id=?",
            (token, bot_username, db_path, files_dir, user.username, existing["id"]),
        )
        clone_id = existing["id"]
    else:
        cur = conn.execute(
            "INSERT INTO clones (owner_user_id, owner_username, bot_token, "
            "bot_username, db_path, files_dir, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'active', ?)",
            (user.id, user.username, token, bot_username, db_path, files_dir, now),
        )
        clone_id = cur.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM clones WHERE id = ?", (clone_id,)).fetchone()
    conn.close()

    try:
        spawn_clone_process(row)
    except Exception as e:
        await status.edit_text(f"Registered @{bot_username}, but couldn't start it: {e}")
        return

    await status.edit_text(
        f"✅ @{bot_username} is now live — your own personal FIGO clone.\n\n"
        f"Open it, send /start, and it'll have its own vault, completely "
        f"separate from this bot. Use /chatid inside your own group/channel "
        f"there to set up its storage and announcements.\n\n"
        f"🄲 Cloned by @{ORIGIN_BOT_USERNAME} and @{CLONE_DEVELOPER}."
    )
    await alog(context, f"🧬 Clone spawned by user {user.id}: @{bot_username}")


async def myclone_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM clones WHERE owner_user_id = ?", (update.effective_user.id,)
    ).fetchone()
    conn.close()
    if not row:
        await areply(update, context, "You don't have a clone yet. Use /clone <bot_token> to create one.")
        return

    running = row["id"] in _clone_processes and _clone_processes[row["id"]].poll() is None
    if not running:
        pid_file = _clone_pid_file(row["id"])
        if os.path.exists(pid_file):
            try:
                with open(pid_file) as f:
                    running = _pid_is_alive(int(f.read().strip()))
            except (OSError, ValueError):
                running = False
    state = "🟢 running" if (running and row["status"] == "active") else "🔴 stopped"
    await areply(
        update, context,
        f"Your clone: @{row['bot_username']}\n"
        f"Status: {state}\n"
        f"Created: {row['created_at'][:10]}\n\n"
        f"🄲 Cloned by @{ORIGIN_BOT_USERNAME} and @{CLONE_DEVELOPER}."
    )


async def unclone_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM clones WHERE owner_user_id = ?", (update.effective_user.id,)
    ).fetchone()
    if not row:
        conn.close()
        await areply(update, context, "You don't have a clone to remove.")
        return
    stop_clone_process(row)
    conn.execute("UPDATE clones SET status = 'stopped' WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    await areply(
        update, context,
        f"Stopped your clone @{row['bot_username']}. Its vault stays on disk — "
        f"send /clone with the same token again to bring it back."
    )


def normalize_help_topic(raw):
    topic = (raw or "").strip().lower().lstrip("/")
    aliases = {
        "save": "save",
        "hsave": "save",
        "find": "find",
        "hfind": "find",
        "organize": "organize",
        "horganize": "organize",
        "study": "study",
        "hstudy": "study",
        "remind": "remind",
        "hremind": "remind",
        "safety": "safety",
        "hsafety": "safety",
        "trash": "safety",
        "htrash": "safety",
        "export": "export",
        "hexport": "export",
        "chat": "chat",
        "hchat": "chat",
        "system": "system",
        "hsystem": "system",
        "clone": "clone",
        "hclone": "clone",
        "admin": "admin",
        "hadmin": "admin",
    }
    return aliases.get(topic)


def build_help_overview(user_id):
    lines = [
        "📖 FIGO HELP CENTER",
        "",
        "Use a focused help command instead of a long mixed list:",
        "",
        "📥 /hsave — saving notes, links, files, and photos",
        "🔎 /hfind — search, view, list, random, and stats",
        "🏷️ /horganize — tags and pins",
        "🧠 /hstudy — summaries and MCQs",
        "⏰ /hremind — reminders, digests, and streaks",
        "🗑️ /hsafety — trash, clear, restore",
        "📦 /hexport — export your vault",
        "💬 /hchat — chat mode",
        "🛠️ /hsystem — bot utility commands",
    ]
    if not IS_CLONE:
        lines.append("🧬 /hclone — personal clone features")
    if is_admin_user(user_id):
        lines.append("👑 /hadmin — admin-only controls")
    lines.extend([
        "",
        "Tip: you can also open a section with /help <topic>, for example /help find.",
    ])
    return "\n".join(lines)


def build_help_topic_text(topic, user_id):
    ocr_note = (
        "OCR is on — text is auto-extracted from photos"
        if OCR_ENABLED else
        "OCR is off — install pytesseract + Pillow + tesseract to enable photo text extraction"
    )

    texts = {
        "save": (
            "📥 SAVE\n\n"
            "Just send text, a link, a file, or a photo in private chat and FIGO saves it.\n\n"
            "/note <text> — save a note explicitly\n"
            "Reply with /note — save a replied text/file/photo intentionally\n"
            "Links sent alone — full page is scraped and indexed\n"
            "Files — PDF, DOCX, PPTX, HTML, PY, MD, TXT, JSON, CSV and similar text/code files are indexed\n"
            f"Photos — {ocr_note}"
        ),
        "find": (
            "🔎 FIND\n\n"
            "/search <keywords> — full-text search your vault (also catches "
            "close word variants, e.g. \"strength\" matches \"strengths\")\n"
            "/view <id> — open a saved item (shows 🔗 related items too)\n"
            "/list — latest saved items\n"
            "/random — pull one random saved item\n"
            "/stats — item counts by type"
        ),
        "organize": (
            "🏷️ ORGANIZE\n\n"
            "/tag <id> <label> — assign a label\n"
            "/tagged <label> — list items with a label\n"
            "/pin <id> — pin or unpin an item\n"
            "/pinned — list pinned items\n"
            "Auto-tags — a few topic tags (civil, programming, exam, etc.) "
            "are detected automatically on save; shown in /view\n\n"
            f"/priority <id> <{'/'.join(PRIORITY_LEVELS)}> — set priority\n"
            "/priorities [level] — list items at a priority (default: high+critical)\n\n"
            "/collection create <name>\n"
            "/collection add <id> <name>\n"
            "/collection remove <id> <name>\n"
            "/collection view <name>\n"
            "/collection list\n"
            "/collection delete <name>"
        ),
        "study": (
            "🧠 STUDY\n\n"
            "/tldr <id> — generate a short summary\n"
            f"/mcq <id> [count] — build a quiz from an item (default {MCQ_DEFAULT_COUNT}, max {MCQ_MAX_COUNT})\n"
            "/ask <id> <question> — ask a question about one saved item\n"
            "/rewrite <id> — restructure a messy note into a clean one\n"
            "/explain <id> — explain the content in simple language\n\n"
            "/ask, /rewrite, and /explain need GEMINI_API_KEY (free) — "
            "/rewrite and /explain still give a basic local result without it"
        ),
        "remind": (
            "⏰ REMINDERS & DIGESTS\n\n"
            "/remind <id> <when> — remind yourself about an item\n"
            "/digest — items from the last 7 days\n"
            "/digest daily 08:00 — enable daily digest\n"
            "/digest weekly 08:00 — enable weekly digest\n"
            "/digest off — disable automatic digest\n"
            "/streak — check your saving streak"
        ),
        "safety": (
            "🗑️ SAFETY & TRASH\n\n"
            "/clear <n> — move the oldest n active items to trash\n"
            "/clearall confirm — move everything active to trash\n"
            "/trash — list trashed items\n"
            "/restore <id> — restore a trashed item within the recovery window"
        ),
        "export": (
            "📦 EXPORT\n\n"
            "/export txt — export as plain text\n"
            "/export md — export as Markdown\n"
            "/export json — export as JSON"
        ),
        "chat": (
            "💬 CHAT MODE\n\n"
            "/chat on — switch to chatbot-style conversation\n"
            "/chat off — return to plain-text auto-saving mode\n\n"
            "When chat mode is on, use /note if you still want to save text as a note."
        ),
        "system": (
            "🛠️ SYSTEM\n\n"
            "/ping — measure bot response latency\n"
            "/uptime — how long the bot has been running\n"
            "/owner — who created and maintains this bot\n"
            "/chatid — show the current chat ID for storage or announcement setup\n"
            "/help — open the help hub again"
        ),
        "clone": (
            "🧬 CLONING\n\n"
            "/clone <bot_token> — launch your own separate FIGO bot\n"
            "/myclone — check your clone status\n"
            "/unclone — stop your personal clone without deleting its data"
            if not IS_CLONE else
            "🧬 CLONING\n\nClone management is only available from the main FIGO bot, not from inside a clone."
        ),
        "admin": (
            "👑 ADMIN\n\n"
            "/admin — admin dashboard\n"
            "/status — runtime and maintenance status\n"
            "/users — user/item/reminder totals\n"
            "/on — enable the bot for everyone\n"
            "/off — pause the bot for everyone except admin\n"
            "/clones — list registered clones\n"
            "/startclone <id|owner_id|bot_username> — start or resume a clone\n"
            "/stopclone <id|owner_id|bot_username> — stop a clone\n"
            "/delclone <id|owner_id|bot_username> — delete a clone and its local data\n"
            "/announce <message> — post to the configured announcement channel"
        ),
    }
    return texts[topic]


async def send_help_topic(update, context, topic):
    if topic == "admin" and not await require_admin(update, context):
        return
    await send_branded(update, context, build_help_topic_text(topic, update.effective_user.id))


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = normalize_help_topic(" ".join(context.args)) if context.args else None
    if topic:
        await send_help_topic(update, context, topic)
        return
    await send_branded(update, context, build_help_overview(update.effective_user.id))


async def hsave_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_help_topic(update, context, "save")


async def hfind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_help_topic(update, context, "find")


async def horganize_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_help_topic(update, context, "organize")


async def hstudy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_help_topic(update, context, "study")


async def hremind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_help_topic(update, context, "remind")


async def hsafety_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_help_topic(update, context, "safety")


async def hexport_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_help_topic(update, context, "export")


async def hchat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_help_topic(update, context, "chat")


async def hsystem_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_help_topic(update, context, "system")


async def hclone_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_help_topic(update, context, "clone")


async def hadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_help_topic(update, context, "admin")


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    await send_branded(
        update,
        context,
        "👑 FIGO ADMIN PANEL\n\n"
        "Use /status for runtime details, /users for totals, /clones for clone inventory, "
        "and /hadmin for the full admin command reference.\n\n"
        "Quick controls: /on, /off, /announce <message>"
    )


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    conn = get_db()
    total_clones = conn.execute("SELECT COUNT(*) FROM clones").fetchone()[0]
    active_clones = conn.execute("SELECT COUNT(*) FROM clones WHERE status = 'active'").fetchone()[0]
    conn.close()

    lines = [
        "📡 FIGO STATUS",
        "",
        f"Public access: {'ON' if is_bot_enabled() else 'OFF'}",
        f"Admin IDs: {', '.join(str(x) for x in sorted(ADMIN_USER_IDS))}",
        f"Storage channel: {'set' if STORAGE_CHAT_ID else 'not set'}",
        f"Announcement channel: {'set' if ANNOUNCE_CHAT_ID else 'not set'}",
        f"OCR: {'enabled' if OCR_ENABLED else 'disabled'}",
        f"Music: {'enabled' if MUSIC_AVAILABLE else 'disabled'}",
        f"Clone registry: {total_clones} total / {active_clones} marked active",
    ]
    if IS_CLONE:
        lines.append("Mode: running inside a clone")
    else:
        lines.append("Mode: main bot instance")
    await send_branded(update, context, "\n".join(lines))


async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    conn = get_db()
    user_ids = set()
    for table, column in (("items", "user_id"), ("settings", "user_id"), ("reminders", "user_id")):
        for row in conn.execute(f"SELECT DISTINCT {column} FROM {table}"):
            if row[0] is not None:
                user_ids.add(int(row[0]))
    total_items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    active_items = conn.execute("SELECT COUNT(*) FROM items WHERE deleted_at IS NULL").fetchone()[0]
    trashed_items = conn.execute("SELECT COUNT(*) FROM items WHERE deleted_at IS NOT NULL").fetchone()[0]
    pending_reminders = conn.execute("SELECT COUNT(*) FROM reminders WHERE sent = 0").fetchone()[0]
    sent_reminders = conn.execute("SELECT COUNT(*) FROM reminders WHERE sent = 1").fetchone()[0]
    total_clones = conn.execute("SELECT COUNT(*) FROM clones").fetchone()[0]
    conn.close()

    await send_branded(
        update,
        context,
        "👥 FIGO TOTALS\n\n"
        f"Users seen: {len(user_ids)}\n"
        f"Items: {total_items} total\n"
        f"Active items: {active_items}\n"
        f"Trashed items: {trashed_items}\n"
        f"Pending reminders: {pending_reminders}\n"
        f"Sent reminders: {sent_reminders}\n"
        f"Registered clones: {total_clones}"
    )


async def on_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    set_bot_enabled(True)
    await send_branded(update, context, "✅ FIGO is now ON for everyone.")


async def off_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    set_bot_enabled(False)
    await send_branded(
        update,
        context,
        "⏸️ FIGO is now OFF for everyone except the admin.\n"
        "User commands and normal saves are paused until /on is used."
    )


async def clones_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if IS_CLONE:
        await areply(update, context, "Clone management is only available on the main FIGO bot.")
        return

    rows = get_clone_admin_rows()
    if not rows:
        await areply(update, context, "No registered clones.")
        return

    lines = ["🧬 REGISTERED CLONES", ""]
    for row in rows:
        lines.append(
            f"#{row['id']} @{row['bot_username']} — owner {row['owner_user_id']} — "
            f"db status {row['status']} / runtime {clone_runtime_state(row)}"
        )
    await send_long_text(update, context, "\n".join(lines))


async def startclone_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if IS_CLONE:
        await areply(update, context, "Clone management is only available on the main FIGO bot.")
        return

    ident = " ".join(context.args).strip()
    if not ident:
        await areply(update, context, "Usage: /startclone <id|owner_id|bot_username>")
        return

    row = get_clone_admin(ident)
    if not row:
        await areply(update, context, "Clone not found.")
        return

    if clone_runtime_state(row) == "running":
        conn = get_db()
        conn.execute("UPDATE clones SET status = 'active' WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        await areply(update, context, f"@{row['bot_username']} is already running.")
        return

    conn = get_db()
    conn.execute("UPDATE clones SET status = 'active' WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    try:
        spawn_clone_process(row)
    except Exception as e:
        await areply(update, context, f"Couldn't start @{row['bot_username']}: {e}")
        return
    await areply(update, context, f"✅ Started clone @{row['bot_username']}.")


async def stopclone_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if IS_CLONE:
        await areply(update, context, "Clone management is only available on the main FIGO bot.")
        return

    ident = " ".join(context.args).strip()
    if not ident:
        await areply(update, context, "Usage: /stopclone <id|owner_id|bot_username>")
        return

    row = get_clone_admin(ident)
    if not row:
        await areply(update, context, "Clone not found.")
        return

    stop_clone_process(row)
    conn = get_db()
    conn.execute("UPDATE clones SET status = 'stopped' WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    await areply(update, context, f"🛑 Stopped clone @{row['bot_username']}.")


async def delclone_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if IS_CLONE:
        await areply(update, context, "Clone management is only available on the main FIGO bot.")
        return

    ident = " ".join(context.args).strip()
    if not ident:
        await areply(update, context, "Usage: /delclone <id|owner_id|bot_username>")
        return

    row = get_clone_admin(ident)
    if not row:
        await areply(update, context, "Clone not found.")
        return

    stop_clone_process(row)
    conn = get_db()
    conn.execute("DELETE FROM clones WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    delete_clone_artifacts(row)
    await areply(
        update,
        context,
        f"🗑️ Deleted clone @{row['bot_username']} and removed its local files."
    )


async def announce_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    message = " ".join(context.args).strip()
    if not message:
        await areply(update, context, "Usage: /announce <message>")
        return
    if not ANNOUNCE_CHAT_ID:
        await areply(update, context, "FIGO_ANNOUNCE_CHAT_ID is not configured.")
        return

    try:
        await context.bot.send_message(chat_id=ANNOUNCE_CHAT_ID, text=message)
    except Exception as e:
        await areply(update, context, f"Couldn't send announcement: {e}")
        return
    await areply(update, context, "📣 Announcement sent.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        return

    pending = context.user_data.get("music_search")
    if pending and text.isdigit():
        if time.monotonic() > pending["expires"]:
            context.user_data.pop("music_search", None)
            await areply(update, context, "That song picker expired — run /play again.")
            return
        idx = int(text)
        if not (1 <= idx <= len(pending["results"])):
            await areply(
                update, context,
                f"Pick a number between 1 and {len(pending['results'])}."
            )
            return
        context.user_data.pop("music_search", None)
        await send_song(update, context, pending["results"][idx - 1])
        return

    user_id = update.effective_user.id
    is_group = update.effective_chat.type in ("group", "supergroup")

    # CRITICAL group-privacy rule: FIGO must never auto-save anything from a
    # group — not plain text, not links, not files, not photos. Only an
    # explicit /note (typed or as a reply) may save group content. This
    # check must run before any auto-save branch below, including links.
    if is_group:
        return

    if URL_RE.fullmatch(text):
        url = text
        title, page_text = fetch_page(url)
        duplicate, score = find_duplicate(user_id, title, url + "\n" + page_text)
        item_id = save_item(user_id, "link", title, url + "\n\n" + page_text)

        msg = f"🔗 Saved link #{item_id}: {title}"
        if duplicate and score >= 0.90:
            msg += f"\n⚠️ Similar to #{duplicate['id']} ({score:.0%} match)."
        await areply(update, context, msg)
        return

    if is_chat_enabled(user_id):
        await handle_chat_message(update, context, text)
        return

    duplicate, score = find_duplicate(user_id, snippet(text, 60), text)
    item_id = save_item(user_id, "note", snippet(text, 60), text)

    msg = f"📝 Saved note #{item_id}"
    if duplicate and score >= 0.90:
        msg += f"\n⚠️ Similar to #{duplicate['id']} ({score:.0%} match)."
    await areply(update, context, msg)


async def note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target = update.message.reply_to_message

    if target:
        sent = await areply(update, context, to_cyber_mono("✍️ Grabbing that message…"))
        await save_from_message(update, context, target, user_id, sent)
        return

    text = " ".join(context.args).strip()
    if not text:
        await areply(update, context, 
            "Usage: /note <text>\n"
            "Or reply to a text, file or photo with /note."
        )
        return

    duplicate, score = find_duplicate(user_id, snippet(text, 60), text)
    item_id = save_item(user_id, "note", snippet(text, 60), text)
    msg = f"📝 Saved note #{item_id}"
    if duplicate and score >= 0.90:
        msg += f"\n⚠️ Similar to #{duplicate['id']} ({score:.0%} match)."
    await areply(update, context, msg)
    await alog(
        context,
        f"📝 Note #{item_id} stored for user {user_id}: {snippet(text, 120)}"
    )


async def save_from_message(update, context, target, user_id, status_msg=None):
    if target.document:
        if status_msg:
            await status_msg.edit_text(to_cyber_mono("📄 Downloading file…"))
        await save_document(update, context, target.document, user_id,
                            caption=target.caption, status_msg=status_msg,
                            source_message=target)
        return

    if target.photo:
        await save_photo(update, context, target.photo[-1], user_id,
                          caption=target.caption, status_msg=status_msg,
                          source_message=target)
        return

    text = target.text or target.caption
    if text:
        duplicate, score = find_duplicate(user_id, snippet(text, 60), text)
        item_id = save_item(user_id, "note", snippet(text, 60), text)
        msg = f"📝 Saved note #{item_id}"
        if duplicate and score >= 0.90:
            msg += f"\n⚠️ Similar to #{duplicate['id']} ({score:.0%} match)."
        if status_msg:
            await status_msg.edit_text(msg)
        await alog(
            context,
            f"📝 Note #{item_id} stored for user {user_id}: {snippet(text, 120)}"
        )
        return

    msg = "I can save text, files (PDF/DOCX/PPTX/HTML/code) and photos."
    if status_msg:
        await status_msg.edit_text(msg)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ("group", "supergroup"):
        return
    await save_document(
        update, context, update.message.document,
        update.effective_user.id, update.message.caption
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ("group", "supergroup"):
        return
    await save_photo(
        update, context, update.message.photo[-1],
        update.effective_user.id, caption=update.message.caption
    )


async def save_photo(update, context, photo, user_id, caption=None, status_msg=None, source_message=None):
    source_message = source_message or update.message
    if status_msg:
        await status_msg.edit_text(to_cyber_mono("🖼️ Downloading photo…"))
    else:
        status_msg = await areply(update, context, to_cyber_mono("🖼️ Downloading photo…"))

    tg_file = await photo.get_file()
    local_path = os.path.join(
        FILES_DIR, f"{user_id}_{photo.file_unique_id}.jpg"
    )
    await tg_file.download_to_drive(local_path)
    await alog(context, f"⬇️ Downloading photo for user {user_id}…")

    ocr = ""
    if OCR_ENABLED:
        await status_msg.edit_text(to_cyber_mono("🖼️ Reading text from photo (OCR)…"))
        ocr = await asyncio.to_thread(ocr_image, local_path)

    caption = caption or ""
    content = caption
    if ocr:
        content += ("\n\n[OCR]\n" if content else "[OCR]\n") + ocr

    stored_path = local_path
    archived = False
    if STORAGE_CHAT_ID:
        await status_msg.edit_text(to_cyber_mono("☁️ Archiving to storage channel…"))
        ref = await archive_to_storage(context, source_message)
        if ref:
            stored_path = ref
            archived = True
            try:
                os.remove(local_path)
            except OSError as e:
                log.warning("Could not remove local copy after archiving: %s", e)

    duplicate, score = find_duplicate(user_id, caption or ocr or "Photo", content)
    item_id = save_item(
        user_id, "photo", snippet(caption or ocr or "Photo", 60),
        content, stored_path
    )

    msg = f"🖼️ Saved photo #{item_id}"
    if ocr:
        msg += " — OCR text indexed"
    elif OCR_ENABLED:
        msg += " (no text detected)"
    elif not OCR_AVAILABLE:
        msg += "\nℹ️ OCR isn't installed — install `pytesseract` + `Pillow` and the tesseract binary to extract text from photos."
    if archived:
        msg += "\n☁️ Stored in the storage channel — not kept on this device."
    elif STORAGE_CHAT_ID:
        msg += "\n⚠️ Couldn't reach the storage channel — kept locally instead."
    if duplicate and score >= 0.90:
        msg += f"\n⚠️ Similar to #{duplicate['id']} ({score:.0%} match)."

    await status_msg.edit_text(msg)
    await alog(
        context,
        f"🖼️ Photo #{item_id} stored for user {user_id}"
        + (" (archived to this group)" if archived else " (kept on device)")
    )


async def save_document(update, context, doc, user_id, caption=None, status_msg=None, source_message=None):
    source_message = source_message or update.message
    filename = doc.file_name or "file"
    tg_file = await doc.get_file()
    local_path = os.path.join(
        FILES_DIR, f"{user_id}_{doc.file_unique_id}_{safe_filename(filename)}"
    )
    await tg_file.download_to_drive(local_path)
    await alog(context, f"⬇️ Downloading file for user {user_id}: {filename}")

    ext = os.path.splitext(filename)[1].lower()
    content = extract_document_text(local_path, filename, doc.mime_type)
    is_pdf = ext == ".pdf" or doc.mime_type == "application/pdf"
    kind = "pdf" if is_pdf else "doc"

    if caption:
        content = (caption + "\n\n" + content).strip()

    stored_path = local_path
    archived = False
    if STORAGE_CHAT_ID:
        if status_msg:
            await status_msg.edit_text(to_cyber_mono("☁️ Archiving to storage channel…"))
        ref = await archive_to_storage(context, source_message)
        if ref:
            stored_path = ref
            archived = True
            try:
                os.remove(local_path)
            except OSError as e:
                log.warning("Could not remove local copy after archiving: %s", e)

    duplicate, score = find_duplicate(user_id, filename, content)
    item_id = save_item(user_id, kind, filename, content, stored_path)

    icon = "📄" if is_pdf else "📑"
    label = "PDF" if is_pdf else (ext.lstrip(".").upper() or "file")
    msg = f"{icon} Saved {label} #{item_id}: {filename}"
    msg += " (text indexed)" if content else " (file stored; no text extracted)"
    if archived:
        msg += "\n☁️ Stored in the storage channel — not kept on this device."
    elif STORAGE_CHAT_ID:
        msg += "\n⚠️ Couldn't reach the storage channel — kept locally instead."
    if duplicate and score >= 0.90:
        msg += f"\n⚠️ Similar to #{duplicate['id']} ({score:.0%} match)."

    if status_msg:
        await status_msg.edit_text(msg)
    else:
        await areply(update, context, msg)
    await alog(
        context,
        f"{icon} {label} #{item_id} stored for user {user_id}: {filename}"
        + (" (archived to this group)" if archived else " (kept on device)")
    )


async def search_cmd(update, context):
    query = " ".join(context.args).strip()
    if not query:
        await areply(update, context, "Usage: /search <keywords>")
        return

    rows = search_items(update.effective_user.id, query)
    if not rows:
        await areply(update, context, "No matches found.")
        return

    ic = icons()
    lines = [
        f"{ic.get(r['kind'], '📌')} #{r['id']} {r['title'] or snippet(r['content'])}"
        for r in rows
    ]
    await areply(update, context, 
        "\n".join(lines) + "\n\nSend /view <id> for the full content."
    )


async def send_related_notes(update, context, item):
    related = get_related_items(
        update.effective_user.id, item["id"], item["title"] or "", item["content"] or ""
    )
    if not related:
        return
    ic = icons()
    lines = ["🔗 Related"] + [f"{ic.get(r['kind'],'📌')} #{r['id']} {r['title']}" for r in related]
    await areply(update, context, "\n".join(lines))


async def view_cmd(update, context):
    if not context.args or not context.args[0].isdigit():
        await areply(update, context, "Usage: /view <id>")
        return

    item = get_item_by_id(update.effective_user.id, int(context.args[0]))
    if not item:
        await areply(update, context, "No item with that id in your vault.")
        return

    icon = icons().get(item["kind"], "📌")
    header = f"{icon} #{item['id']} {item['title'] or ''}\n\n"

    if item["kind"] == "link":
        await send_long_text(update, context, header + item["content"])
        await send_related_notes(update, context, item)
        return

    if item["kind"] in ("pdf", "doc", "photo") and item["file_path"]:
        ref = parse_storage_ref(item["file_path"])
        if ref:
            file_id, _ = ref
            if item["kind"] in ("pdf", "doc"):
                await send_long_text(update, context, header + (item["content"] or "(no extractable text)"))
                await update.message.reply_document(file_id, filename=item["title"])
            else:
                caption = header + snippet(item["content"], 900)
                await update.message.reply_photo(file_id, caption=caption[:1024])
            await send_related_notes(update, context, item)
            return

        if os.path.exists(item["file_path"]):
            if item["kind"] in ("pdf", "doc"):
                await send_long_text(update, context, header + (item["content"] or "(no extractable text)"))
                with open(item["file_path"], "rb") as f:
                    await update.message.reply_document(f, filename=item["title"])
            else:
                caption = header + snippet(item["content"], 900)
                with open(item["file_path"], "rb") as f:
                    await update.message.reply_photo(f, caption=caption[:1024])
            await send_related_notes(update, context, item)
            return

    await send_long_text(update, context, header + (item["content"] or ""))
    await send_related_notes(update, context, item)


async def list_cmd(update, context):
    rows = list_recent(update.effective_user.id)
    if not rows:
        await areply(update, context, "Your vault is empty.")
        return
    ic = icons()
    await areply(update, context, 
        "\n".join(f"{ic.get(r['kind'],'📌')} #{r['id']} {r['title']}" for r in rows)
    )


async def stats_cmd(update, context):
    rows = stats(update.effective_user.id)
    if not rows:
        await areply(update, context, "Nothing saved yet.")
        return
    await areply(update, context, "\n".join(f"{r['kind']}: {r['c']}" for r in rows))


async def clear_cmd(update, context):
    if not context.args or not context.args[0].isdigit() or int(context.args[0]) < 1:
        await areply(update, context, "Usage: /clear <n>")
        return
    n = int(context.args[0])
    rows = get_oldest_active(update.effective_user.id, n)
    if not rows:
        await areply(update, context, "Nothing to clear.")
        return
    count = soft_delete_items(update.effective_user.id, [r["id"] for r in rows])
    await areply(update, context, 
        f"🗑️ Moved {count} item(s) to trash. They can be restored for {TRASH_DAYS} days."
    )


async def clearall_cmd(update, context):
    user_id = update.effective_user.id
    if not context.args or context.args[0].lower() != "confirm":
        rows = get_all_active(user_id)
        await areply(update, context, 
            f"⚠️ This will move all {len(rows)} active item(s) to trash.\n"
            "Send /clearall confirm to continue."
        )
        return
    rows = get_all_active(user_id)
    count = soft_delete_items(user_id, [r["id"] for r in rows])
    await areply(update, context, 
        f"🗑️ Moved {count} item(s) to trash. Use /trash or /restore <id>."
    )


async def trash_cmd(update, context):
    rows = trash_items(update.effective_user.id)
    if not rows:
        await areply(update, context, "🗑️ Trash is empty.")
        return
    lines = []
    for r in rows:
        try:
            deleted = datetime.fromisoformat(r["deleted_at"])
            expires = deleted + timedelta(days=TRASH_DAYS)
            exp_text = expires.strftime("%Y-%m-%d")
        except Exception:
            exp_text = "unknown"
        lines.append(
            f"{icons().get(r['kind'],'📌')} #{r['id']} {r['title']} — expires {exp_text}"
        )
    await areply(update, context, "🗑️ Trash\n\n" + "\n".join(lines))


async def restore_cmd(update, context):
    if not context.args or not context.args[0].isdigit():
        await areply(update, context, "Usage: /restore <id>")
        return
    item_id = int(context.args[0])
    if restore_item(update.effective_user.id, item_id):
        await areply(update, context, f"♻️ Restored #{item_id}.")
    else:
        await areply(update, context, "That item is not in your trash.")


async def random_cmd(update, context):
    item = get_random_item(update.effective_user.id)
    if not item:
        await areply(update, context, "Your vault is empty.")
        return
    icon = icons().get(item["kind"], "📌")
    await areply(update, context, 
        f"🎲 Random flashback\n\n{icon} #{item['id']} {item['title']}\n\n"
        f"{snippet(item['content'], 500)}\n\n/view {item['id']}"
    )


async def pin_cmd(update, context):
    if not context.args or not context.args[0].isdigit():
        await areply(update, context, "Usage: /pin <id>")
        return
    state = toggle_pin(update.effective_user.id, int(context.args[0]))
    if state is None:
        await areply(update, context, "No active item with that id.")
    else:
        await areply(update, context, 
            f"📌 {'Pinned' if state else 'Unpinned'} #{context.args[0]}."
        )


async def pinned_cmd(update, context):
    rows = get_pinned(update.effective_user.id)
    if not rows:
        await areply(update, context, "Nothing pinned yet.")
        return
    ic = icons()
    await areply(update, context, 
        "\n".join(f"{ic.get(r['kind'],'📌')} #{r['id']} {r['title']}" for r in rows)
    )


async def tag_cmd(update, context):
    if len(context.args) < 2 or not context.args[0].isdigit():
        await areply(update, context, "Usage: /tag <id> <label>")
        return
    item_id = int(context.args[0])
    tag = " ".join(context.args[1:]).strip()
    if set_tag(update.effective_user.id, item_id, tag):
        await areply(update, context, f"🏷️ Tagged #{item_id} as {tag.lower()}.")
    else:
        await areply(update, context, "No active item with that id.")


async def tagged_cmd(update, context):
    if not context.args:
        await areply(update, context, "Usage: /tagged <label>")
        return
    tag = " ".join(context.args)
    rows = get_by_tag(update.effective_user.id, tag)
    if not rows:
        await areply(update, context, "Nothing found under that tag.")
        return
    ic = icons()
    await areply(update, context, 
        "\n".join(f"{ic.get(r['kind'],'📌')} #{r['id']} {r['title']}" for r in rows)
    )


async def priority_cmd(update, context):
    if len(context.args) < 2 or not context.args[0].isdigit():
        await areply(
            update, context,
            "Usage: /priority <id> <low|medium|high|critical>"
        )
        return
    item_id = int(context.args[0])
    level = context.args[1].strip().lower()
    if level not in PRIORITY_LEVELS:
        await areply(
            update, context,
            f"Priority must be one of: {', '.join(PRIORITY_LEVELS)}"
        )
        return
    if set_priority(update.effective_user.id, item_id, level):
        await areply(
            update, context,
            f"{PRIORITY_ICON[level]} #{item_id} set to {level} priority."
        )
    else:
        await areply(update, context, "No active item with that id.")


async def priorities_cmd(update, context):
    levels = [a.lower() for a in context.args if a.lower() in PRIORITY_LEVELS]
    levels = levels or ["critical", "high"]
    rows = get_by_priority(update.effective_user.id, levels)
    if not rows:
        await areply(update, context, f"Nothing at {'/'.join(levels)} priority.")
        return
    ic = icons()
    lines = [f"{PRIORITY_ICON[r['priority']]} {ic.get(r['kind'],'📌')} #{r['id']} {r['title']}" for r in rows]
    await areply(update, context, "\n".join(lines))


async def ask_cmd(update, context):
    if len(context.args) < 2 or not context.args[0].isdigit():
        await areply(update, context, "Usage: /ask <id> <question>")
        return
    item_id = int(context.args[0])
    question = " ".join(context.args[1:]).strip()
    item = get_item_by_id(update.effective_user.id, item_id)
    if not item:
        await areply(update, context, "No active item with that id.")
        return
    if not item["content"]:
        await areply(update, context, "That item has no extractable text to ask about.")
        return
    if not GEMINI_API_KEY:
        await areply(
            update, context,
            "🔒 /ask needs GEMINI_API_KEY set (free — see /hsystem for how)."
        )
        return

    status = await areply(update, context, to_cyber_mono("🤔 Thinking…"))
    try:
        answer = await asyncio.to_thread(
            call_gemini,
            f"Answer the question using ONLY the information in the note "
            f"below. If the note doesn't contain the answer, say so plainly "
            f"— do not invent information.\n\n"
            f"Note:\n{item['content'][:50000]}\n\n"
            f"Question: {question}"
        )
    except Exception as e:
        log.warning("/ask failed: %s", e)
        answer = "Couldn't get an answer just now — try again in a bit."
    await status.edit_text(f"❓ {question}\n\n{answer}")


async def rewrite_cmd(update, context):
    if not context.args or not context.args[0].isdigit():
        await areply(update, context, "Usage: /rewrite <id>")
        return
    item_id = int(context.args[0])
    item = get_item_by_id(update.effective_user.id, item_id)
    if not item:
        await areply(update, context, "No active item with that id.")
        return
    if not item["content"]:
        await areply(update, context, "That item has no extractable text to rewrite.")
        return

    status = await areply(update, context, to_cyber_mono("🧹 Rewriting…"))
    if GEMINI_API_KEY:
        try:
            result = await asyncio.to_thread(
                call_gemini,
                "Rewrite the following messy note into a clean, structured "
                "note using ONLY information present in it — do not invent "
                "facts. Use this structure with headers: Title, Key "
                "Concepts, Important Points, Definitions, Examples, "
                "Summary. Skip a header if the note has nothing for it.\n\n"
                + item["content"][:50000]
            )
        except Exception as e:
            log.warning("/rewrite failed: %s", e)
            result = None
    else:
        result = None

    if not result:
        # Local fallback: no AI restructuring, just a readable bullet split.
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", item["content"]) if s.strip()]
        result = "Key Points\n" + "\n".join(f"• {s}" for s in sentences[:15])
        if not GEMINI_API_KEY:
            result += "\n\n(Set GEMINI_API_KEY for a properly restructured rewrite.)"

    await status.edit_text(f"🧹 Rewrite of #{item_id}\n\n{result}")


async def explain_cmd(update, context):
    if not context.args or not context.args[0].isdigit():
        await areply(update, context, "Usage: /explain <id>")
        return
    item_id = int(context.args[0])
    item = get_item_by_id(update.effective_user.id, item_id)
    if not item:
        await areply(update, context, "No active item with that id.")
        return
    if not item["content"]:
        await areply(update, context, "That item has no extractable text to explain.")
        return

    status = await areply(update, context, to_cyber_mono("📖 Explaining…"))
    if GEMINI_API_KEY:
        try:
            result = await asyncio.to_thread(
                call_gemini,
                "Explain the following content in simple, plain language "
                "for someone unfamiliar with it. Include: a simple "
                "explanation, important terms defined, a short example if "
                "the content supports one, and a quick recap. Use ONLY "
                "information present in the content — do not invent "
                "facts.\n\n" + item["content"][:50000]
            )
        except Exception as e:
            log.warning("/explain failed: %s", e)
            result = None
    else:
        result = None

    if not result:
        result = local_summary(item["content"])
        if not GEMINI_API_KEY:
            result += "\n\n(Set GEMINI_API_KEY for a fuller, plain-language explanation.)"

    await status.edit_text(f"📖 Explaining #{item_id}\n\n{result}")


async def collection_cmd(update, context):
    if not context.args:
        await areply(
            update, context,
            "Usage:\n"
            "/collection create <name>\n"
            "/collection add <id> <name>\n"
            "/collection remove <id> <name>\n"
            "/collection view <name>\n"
            "/collection list\n"
            "/collection delete <name>"
        )
        return

    user_id = update.effective_user.id
    sub = context.args[0].lower()
    rest = context.args[1:]

    if sub == "list":
        rows = list_collections(user_id)
        if not rows:
            await areply(update, context, "No collections yet. /collection create <name>")
            return
        lines = [f"📁 {r['name']} ({r['item_count']} items)" for r in rows]
        await areply(update, context, "\n".join(lines))
        return

    if sub == "create":
        name = " ".join(rest).strip()
        row, err = create_collection(user_id, name)
        await areply(update, context, err or f"📁 Created collection '{row['name']}'.")
        return

    if sub == "delete":
        name = " ".join(rest).strip()
        ok, err = delete_collection(user_id, name)
        await areply(update, context, err or f"🗑️ Deleted collection '{name}'.")
        return

    if sub == "view":
        name = " ".join(rest).strip()
        rows, err = view_collection(user_id, name)
        if err:
            await areply(update, context, err)
            return
        if not rows:
            await areply(update, context, f"📁 '{name}' is empty.")
            return
        ic = icons()
        lines = [f"📁 {name}\n"] + [f"{ic.get(r['kind'],'📌')} #{r['id']} {r['title']}" for r in rows]
        await areply(update, context, "\n".join(lines))
        return

    if sub in ("add", "remove"):
        if len(rest) < 2 or not rest[0].isdigit():
            await areply(update, context, f"Usage: /collection {sub} <id> <name>")
            return
        item_id = int(rest[0])
        name = " ".join(rest[1:]).strip()
        if sub == "add":
            ok, err = add_to_collection(user_id, name, item_id)
            await areply(update, context, err or f"📁 Added #{item_id} to '{name}'.")
        else:
            ok, err = remove_from_collection(user_id, name, item_id)
            await areply(update, context, err or f"📁 Removed #{item_id} from '{name}'.")
        return

    await areply(update, context, f"Unknown /collection subcommand: {sub}")


async def remind_cmd(update, context):
    if len(context.args) < 2 or not context.args[0].isdigit():
        await areply(update, context, 
            "Usage: /remind <id> <when>\n"
            "Examples: /remind 12 tomorrow 9am\n"
            "          /remind 12 in 2h"
        )
        return

    item_id = int(context.args[0])
    when_text = " ".join(context.args[1:])
    item = get_item_by_id(update.effective_user.id, item_id)
    if not item:
        await areply(update, context, "No active item with that id.")
        return

    when = parse_when(when_text)
    if not when or when <= datetime.now(when.tzinfo):
        await areply(update, context, 
            "I couldn't understand that time. Try `tomorrow 9am`, `today 18:00`, or `in 2h`."
        )
        return

    rid = add_reminder(update.effective_user.id, item_id, when)
    await areply(update, context, 
        f"🔔 Reminder #{rid} set for #{item_id} at {when.strftime('%Y-%m-%d %H:%M %Z')}."
    )


async def tldr_cmd(update, context):
    if not context.args or not context.args[0].isdigit():
        await areply(update, context, "Usage: /tldr <id>")
        return
    item = get_item_by_id(update.effective_user.id, int(context.args[0]))
    if not item:
        await areply(update, context, "No active item with that id.")
        return

    text = item["content"] or ""
    if len(text) < 250:
        await areply(update, context, "🧠 It's already short:\n\n" + text)
        return

    await areply(update, context, to_cyber_mono("🧠 Summarizing…"))
    summary = await asyncio.to_thread(ai_summary, text)
    await areply(update, context, 
        f"🧠 TL;DR — #{item['id']}\n\n{summary}"
    )


async def mcq_cmd(update, context):
    if not context.args or not context.args[0].isdigit():
        await areply(update, context, 
            "Usage: /mcq <id> [count]\n"
            f"count is optional, 1-{MCQ_MAX_COUNT} (default {MCQ_DEFAULT_COUNT})."
        )
        return

    item_id = int(context.args[0])
    n = MCQ_DEFAULT_COUNT
    if len(context.args) > 1 and context.args[1].isdigit():
        n = max(1, min(MCQ_MAX_COUNT, int(context.args[1])))

    item = get_item_by_id(update.effective_user.id, item_id)
    if not item:
        await areply(update, context, "No active item with that id.")
        return

    text = item["content"] or ""
    if len(text.split()) < 20:
        await areply(update, context, 
            "That item is too short to build quiz questions from."
        )
        return

    await areply(update, context, to_cyber_mono("🧩 Building your quiz…"))
    questions = await asyncio.to_thread(ai_mcq, text, n)
    if not questions:
        await areply(update, context, 
            "I couldn't generate questions from that item — try a longer, "
            "more detailed note."
        )
        return

    header = f"🧩 MCQ — #{item['id']} {item['title'] or ''}\n\n"
    await send_long_text(update, context, header + format_mcq(questions))


async def digest_cmd(update, context):
    user_id = update.effective_user.id

    if not context.args:
        rows = get_recent_days(user_id, 7)
        if not rows:
            await areply(update, context, "Nothing saved in the last 7 days.")
            return
        ic = icons()
        await areply(update, context, 
            f"🗞️ Last 7 days ({len(rows)} item(s)):\n\n" +
            "\n".join(f"{ic.get(r['kind'],'📌')} #{r['id']} {r['title']}" for r in rows)
        )
        return

    if context.args[0].lower() == "off":
        set_digest(user_id, False)
        await areply(update, context, "🔕 Automatic digest disabled.")
        return

    mode = context.args[0].lower()
    if mode not in ("daily", "weekly") or len(context.args) < 2:
        await areply(update, context, 
            "Usage: /digest daily 08:00\n"
            "/digest weekly 08:00\n"
            "/digest off"
        )
        return

    try:
        hour, minute = map(int, context.args[1].split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        await areply(update, context, "Time must look like 08:00.")
        return

    set_digest(user_id, True, mode, hour, minute)
    await areply(update, context, 
        f"🔔 {mode.title()} digest enabled for {hour:02d}:{minute:02d} UTC.\n"
        "Note: this scheduler uses UTC."
    )


async def streak_cmd(update, context):
    streak = current_streak(update.effective_user.id)
    if streak == 0:
        await areply(update, context, 
            "🔥 Streak: 0 days\nSave something today to start your streak!"
        )
    else:
        await areply(update, context, 
            f"🔥 Current FIGO streak: {streak} day{'s' if streak != 1 else ''}!"
        )


async def chat_cmd(update, context):
    user_id = update.effective_user.id
    arg = context.args[0].lower() if context.args else ""

    if arg not in ("on", "off"):
        state = "on" if is_chat_enabled(user_id) else "off"
        await areply(
            update, context,
            f"💬 Chat mode is currently {state}.\n\n"
            "/chat on — talk to me like a normal chatbot; use /note <text> "
            "whenever you want to save something instead\n"
            "/chat off — back to plain text being auto-saved as notes"
        )
        return

    if arg == "on" and not GEMINI_API_KEY:
        await areply(
            update, context,
            "💬 Chat mode needs a GEMINI_API_KEY set on the server — "
            "without it I can't hold a real conversation.\n"
            "It's free: grab one at aistudio.google.com/apikey and set "
            "GEMINI_API_KEY before starting the bot.\n"
            "/tldr and /mcq still work fine without it, though."
        )
        return

    set_chat_mode(user_id, arg == "on")
    context.user_data.pop("chat_history", None)

    if arg == "on":
        await areply(
            update, context,
            "💬 Chat mode is on — talk to me like normal.\n"
            "Use /note <text> whenever you want to save something instead."
        )
    else:
        await areply(
            update, context,
            "💬 Chat mode is off — plain text goes back to being saved as notes."
        )


async def play_cmd(update, context):
    if not MUSIC_AVAILABLE:
        await areply(
            update, context,
            "🎵 Music search isn't set up on this server.\n"
            "Install `yt-dlp` (`pip install yt-dlp`) and `ffmpeg` "
            "(`pkg install ffmpeg` on Termux), then restart the bot."
        )
        return

    query = " ".join(context.args).strip()
    if not query:
        await areply(update, context, "Usage: /play <song name>")
        return

    status = await areply(update, context, to_cyber_mono(f"🔎 Searching YouTube for “{query}”…"))
    try:
        results = await asyncio.to_thread(search_youtube, query)
    except Exception as e:
        log.warning("YouTube search failed: %s", e)
        results = None

    if not results:
        await status.edit_text("Couldn't find anything for that search — try different words.")
        return

    context.user_data["music_search"] = {
        "results": results,
        "expires": time.monotonic() + MUSIC_PICK_TIMEOUT,
    }

    lines = [f"🎵 Results for “{query}” — reply with a number to play (expires in 2 min):", ""]
    for i, r in enumerate(results, start=1):
        lines.append(f"{i}. {r['title']} — {r['uploader']} ({fmt_duration(r['duration'])})")
    await status.edit_text("\n".join(lines))


async def send_song(update, context, result):
    if result.get("duration") and result["duration"] > MAX_SONG_SECONDS:
        await areply(
            update, context,
            f"⏭️ “{result['title']}” is longer than "
            f"{MAX_SONG_SECONDS // 60} minutes — pick a shorter track."
        )
        return

    status = await areply(update, context, to_cyber_mono(f"⬇️ Downloading “{result['title']}”…"))
    user_id = update.effective_user.id
    await alog(
        context,
        f"🎵 Downloading music for user {user_id}: “{result['title']}” — {result.get('uploader', '?')}"
    )
    mp3_path = None
    try:
        mp3_path, info = await asyncio.to_thread(
            download_audio, result["id"], MUSIC_TMP_DIR
        )

        if os.path.getsize(mp3_path) > TELEGRAM_FILE_LIMIT_BYTES:
            await status.edit_text(
                "That track came out larger than Telegram's 50MB upload limit "
                "— try a shorter one."
            )
            return

        await status.edit_text(to_cyber_mono("📤 Sending…"))
        with open(mp3_path, "rb") as f:
            await update.message.reply_audio(
                f,
                title=info.get("title") or result["title"],
                performer=info.get("uploader") or result.get("uploader") or None,
                duration=int(info.get("duration") or result.get("duration") or 0) or None,
            )
        try:
            await status.delete()
        except Exception:
            pass
        await alog(
            context,
            f"📤 Sent audio to user {user_id}: “{info.get('title') or result['title']}”"
        )
    except Exception as e:
        log.warning("Song download/send failed for %s: %s", result.get("id"), e)
        await status.edit_text("Couldn't fetch that track — try another one.")
        await alog(
            context,
            f"⚠️ Failed to download/send “{result['title']}” for user {user_id}: {e}"
        )
    finally:
        # Always clean up, success or failure — nothing from /play should
        # linger on disk.
        if mp3_path and os.path.exists(mp3_path):
            try:
                os.remove(mp3_path)
            except OSError as e:
                log.warning("Could not delete temp audio %s: %s", mp3_path, e)


def build_export(rows, fmt):
    if fmt == "json":
        return json.dumps(
            [
                {
                    "id": r["id"],
                    "kind": r["kind"],
                    "title": r["title"],
                    "content": r["content"],
                    "tags": r["tags"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ],
            ensure_ascii=False,
            indent=2,
        ), "figo-vault.json"

    if fmt == "md":
        parts = ["# FIGO Vault Export", ""]
        for r in rows:
            parts += [
                f"## #{r['id']} — {r['title'] or ''}",
                f"- Type: `{r['kind']}`",
                f"- Saved: `{r['created_at']}`",
                f"- Tags: `{r['tags'] or ''}`",
                "",
                r["content"] or "",
                "",
                "---",
                "",
            ]
        return "\n".join(parts), "figo-vault.md"

    parts = [f"FIGO vault export — {len(rows)} item(s)", ""]
    for r in rows:
        parts += [
            "=" * 50,
            f"#{r['id']} [{r['kind']}] {r['title'] or ''}",
            f"saved: {r['created_at']}",
            f"tags: {r['tags'] or ''}",
            "",
            r["content"] or "",
            "",
        ]
    return "\n".join(parts), "figo-vault.txt"


async def export_cmd(update, context):
    fmt = (context.args[0].lower() if context.args else "txt")
    if fmt not in ("txt", "md", "json"):
        await areply(update, context, "Usage: /export txt|md|json")
        return

    rows = get_all_active(update.effective_user.id)
    if not rows:
        await areply(update, context, "Your vault is empty.")
        return

    content, filename = build_export(rows, fmt)
    path = os.path.join(FILES_DIR, f"_export_{update.effective_user.id}_{filename}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    try:
        with open(path, "rb") as f:
            await update.message.reply_document(f, filename=filename)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Background jobs
# ---------------------------------------------------------------------------

async def reminder_worker(app):
    while True:
        try:
            await purge_expired_trash(app.bot)
            for r in due_reminders():
                try:
                    await asend(
                        app.bot,
                        r["user_id"],
                        f"🔔 FIGO reminder\n\n"
                        f"#{r['item_id']} — {r['title'] or 'Untitled'}\n\n"
                        f"{snippet(r['content'], 700)}\n\n"
                        f"Use /view {r['item_id']} to open it.",
                    )
                    mark_reminder_sent(r["reminder_id"])
                except Exception as e:
                    log.warning("Reminder delivery failed: %s", e)
        except Exception as e:
            log.exception("Reminder worker error: %s", e)
        await asyncio.sleep(30)


async def digest_worker(app):
    sent_keys = set()

    while True:
        try:
            now = utcnow()
            for s in digest_users():
                key = f"{s['user_id']}:{now.strftime('%Y-%m-%d-%H-%M')}"
                if key in sent_keys:
                    continue
                if now.hour != s["digest_hour"] or now.minute != s["digest_minute"]:
                    continue

                if s["digest_mode"] == "weekly" and now.weekday() != 0:
                    continue

                days = 7 if s["digest_mode"] == "weekly" else 1
                rows = get_recent_days(s["user_id"], days)
                if rows:
                    ic = icons()
                    body = (
                        f"🗞️ FIGO {'weekly' if days == 7 else 'daily'} digest\n\n" +
                        "\n".join(
                            f"{ic.get(r['kind'],'📌')} #{r['id']} {r['title']}"
                            for r in rows
                        )
                    )
                else:
                    body = "🗞️ FIGO digest\n\nNothing new was saved in this period."

                try:
                    await asend(app.bot, s["user_id"], body)
                    sent_keys.add(key)
                except Exception as e:
                    log.warning("Digest delivery failed: %s", e)

            # Prevent unbounded memory growth.
            if len(sent_keys) > 10000:
                sent_keys.clear()

        except Exception as e:
            log.exception("Digest worker error: %s", e)

        await asyncio.sleep(30)


# ---------------------------------------------------------------------------
# Inline mode
# ---------------------------------------------------------------------------

async def inline_query(update, context):
    query = (update.inline_query.query or "").strip()
    if not query:
        return

    rows = search_items(update.effective_user.id, query, limit=20)
    results = []

    for r in rows:
        title = r["title"] or f"#{r['id']}"
        body = (
            f"{icons().get(r['kind'], '📌')} #{r['id']} {title}\n\n"
            f"{snippet(r['content'], 1200)}"
        )
        results.append(
            InlineQueryResultArticle(
                id=str(r["id"]),
                title=title[:64],
                description=snippet(r["content"], 120),
                input_message_content=InputTextMessageContent(body),
            )
        )

    await update.inline_query.answer(
        results,
        cache_time=0,
        is_personal=True,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def post_init(app):
    app.create_task(reminder_worker(app))
    app.create_task(digest_worker(app))
    if not IS_CLONE:
        await resume_clones()

    if STORAGE_CHAT_ID:
        try:
            me = await app.bot.get_me()
            await alog_bot(
                app.bot,
                f"✅ FIGO bot is now running (@{me.username}).\n"
                f"This group is set as the storage/log channel."
            )
        except Exception as e:
            log.warning(
                "Startup message to storage group (%s) failed — check that "
                "the bot is a member/admin there and the ID is correct: %s",
                STORAGE_CHAT_ID, e,
            )
    else:
        log.info(
            "FIGO_STORAGE_CHAT_ID is not set — group storage/logging is "
            "disabled. Use /chatid inside the target group to get its ID."
        )

    # Announcement channel — a short "I'm live" ping on every restart, plus
    # a changelog card for any CHANGELOG entries that haven't been announced
    # yet (tracked in bot_meta so restarts on an unchanged version don't
    # re-post the same changelog entry).
    if ANNOUNCE_CHAT_ID:
        try:
            me = await app.bot.get_me()
            await app.bot.send_message(
                chat_id=ANNOUNCE_CHAT_ID,
                text=f"🟢 @{me.username} is live now.\nUse /uptime anytime to check how long I've been running.",
            )
        except Exception as e:
            log.warning(
                "Live-startup ping to announcement channel (%s) failed — "
                "check the bot is an admin there: %s", ANNOUNCE_CHAT_ID, e,
            )

        try:
            last_announced = int(get_meta("last_announced_change", "0"))
        except (TypeError, ValueError):
            last_announced = 0

        if len(CHANGELOG) > last_announced:
            avatar = await get_bot_avatar_file_id(app)
            posted = 0
            for i in range(last_announced, len(CHANGELOG)):
                entry = CHANGELOG[i]
                update_no = i + 1
                caption = (
                    f"🛰️ Update #{update_no} — {entry['title']}\n\n"
                    f"{entry['summary']}\n\n"
                    f"How to use: {entry['usage']}"
                )
                try:
                    if avatar:
                        await app.bot.send_photo(
                            chat_id=ANNOUNCE_CHAT_ID, photo=avatar, caption=caption
                        )
                    else:
                        await app.bot.send_message(chat_id=ANNOUNCE_CHAT_ID, text=caption)
                    posted += 1
                except Exception as e:
                    log.warning(
                        "Could not post changelog #%s to announcement channel "
                        "(%s) — check the bot is an admin there: %s",
                        update_no, ANNOUNCE_CHAT_ID, e,
                    )
                    break
            if posted:
                set_meta("last_announced_change", last_announced + posted)
    else:
        log.info(
            "FIGO_ANNOUNCE_CHAT_ID is not set — the changelog announcement "
            "channel is disabled. Use /chatid inside the target channel to "
            "get its ID."
        )


def main():
    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN environment variable not set. "
            "Set it before running the bot."
        )

    init_db()
    purge_music_tmp()

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .get_updates_read_timeout(40)
        .post_init(post_init)
        .build()
    )

    application.add_handler(TypeHandler(Update, maintenance_gate), group=-100)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("hsave", hsave_cmd))
    application.add_handler(CommandHandler("hfind", hfind_cmd))
    application.add_handler(CommandHandler("horganize", horganize_cmd))
    application.add_handler(CommandHandler("hstudy", hstudy_cmd))
    application.add_handler(CommandHandler("hremind", hremind_cmd))
    application.add_handler(CommandHandler("hsafety", hsafety_cmd))
    application.add_handler(CommandHandler("hexport", hexport_cmd))
    application.add_handler(CommandHandler("hchat", hchat_cmd))
    application.add_handler(CommandHandler("hsystem", hsystem_cmd))
    application.add_handler(CommandHandler("hclone", hclone_cmd))
    application.add_handler(CommandHandler("hadmin", hadmin_cmd))
    application.add_handler(CommandHandler("admin", admin_cmd))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(CommandHandler("users", users_cmd))
    application.add_handler(CommandHandler("on", on_cmd))
    application.add_handler(CommandHandler("off", off_cmd))
    application.add_handler(CommandHandler("clones", clones_cmd))
    application.add_handler(CommandHandler("startclone", startclone_cmd))
    application.add_handler(CommandHandler("stopclone", stopclone_cmd))
    application.add_handler(CommandHandler("delclone", delclone_cmd))
    application.add_handler(CommandHandler("announce", announce_cmd))
    application.add_handler(CommandHandler("note", note_cmd))
    application.add_handler(CommandHandler("search", search_cmd))
    application.add_handler(CommandHandler("view", view_cmd))
    application.add_handler(CommandHandler("list", list_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("clear", clear_cmd))
    application.add_handler(CommandHandler("clearall", clearall_cmd))
    application.add_handler(CommandHandler("trash", trash_cmd))
    application.add_handler(CommandHandler("restore", restore_cmd))
    application.add_handler(CommandHandler("random", random_cmd))
    application.add_handler(CommandHandler("pin", pin_cmd))
    application.add_handler(CommandHandler("pinned", pinned_cmd))
    application.add_handler(CommandHandler("tag", tag_cmd))
    application.add_handler(CommandHandler("tagged", tagged_cmd))
    application.add_handler(CommandHandler("priority", priority_cmd))
    application.add_handler(CommandHandler("priorities", priorities_cmd))
    application.add_handler(CommandHandler("ask", ask_cmd))
    application.add_handler(CommandHandler("rewrite", rewrite_cmd))
    application.add_handler(CommandHandler("explain", explain_cmd))
    application.add_handler(CommandHandler("collection", collection_cmd))
    application.add_handler(CommandHandler("remind", remind_cmd))
    application.add_handler(CommandHandler("tldr", tldr_cmd))
    application.add_handler(CommandHandler("mcq", mcq_cmd))
    application.add_handler(CommandHandler("digest", digest_cmd))
    application.add_handler(CommandHandler("streak", streak_cmd))
    application.add_handler(CommandHandler("export", export_cmd))
    application.add_handler(CommandHandler("ping", ping_cmd))
    application.add_handler(CommandHandler("uptime", uptime_cmd))
    application.add_handler(CommandHandler("owner", owner_cmd))
    application.add_handler(CommandHandler("chatid", chatid_cmd))
    application.add_handler(CommandHandler("clone", clone_cmd))
    application.add_handler(CommandHandler("myclone", myclone_cmd))
    application.add_handler(CommandHandler("unclone", unclone_cmd))
    # Channels deliver commands as channel_post updates, not message updates —
    # CommandHandler alone won't see them, so /chatid needs this extra hook
    # to work when run inside your announcement channel.
    application.add_handler(
        MessageHandler(filters.UpdateType.CHANNEL_POST & filters.Regex(r"^/chatid"), chatid_cmd)
    )
    application.add_handler(CommandHandler("play", play_cmd))
    application.add_handler(CommandHandler("chat", chat_cmd))
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome
    ))
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(MessageHandler(
        filters.Document.ALL, handle_document
    ))
    application.add_handler(MessageHandler(
        filters.PHOTO, handle_photo
    ))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_text
    ))

    log.info("FIGO is running…")
    application.run_polling()


if __name__ == "__main__":
    main()
