from __future__ import annotations

import asyncio

import io

import contextlib

import json

import logging

import os

import sqlite3

import time

import traceback

import html

from collections import deque

from datetime import datetime, timezone, timedelta

import aiohttp

from aiohttp import FormData

# ==================== НАСТРОЙКИ ====================

TOKEN = "8837204070:AAFJnoeJWBhaWEfXF3aV7EqKkIrRAIHQZEM"

PDF_URL = "https://priem.mgpk.by/uploads/schedule/substitutions.pdf"

REFERER = "https://priem.mgpk.by/students/schedule.html"

PDF_PATH = "substitutions.pdf"

DB_FILE = "bot.db"

CHECK_INTERVAL_MINUTES = 15

API = f"https://api.telegram.org/bot{TOKEN}"

CHUNK = 64 * 1024

try:

    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Europe/Moscow")

except Exception:

    TZ = timezone(timedelta(hours=3))

ADMIN_PASSWORD = "MPK-admin-2026"

SUPER_ADMIN_PASSWORD = "zarexu28"

RATE_LIMIT = 100

RATE_WINDOW = 60

MUTE_SECONDS = 300

TICKETS_PER_PAGE = 8

SCHEDULES = [

    ("1 курс", "course-1.pdf", "I семестр"),

    ("2 курс", "course-2.pdf", "III семестр"),

    ("3 курс", "course-3.pdf", "V семестр"),

    ("4 курс", "course-4.pdf", "VII семестр"),

]

KORPUS1_IMAGES = [

    ("1-й этаж", "k1-floor-1.jpg"),

    ("2-й этаж", "k1-floor-2.jpg"),

    ("3-й этаж", "k1-floor-3.jpg"),

]

FLOOR_IMAGES = [

    ("1-й этаж", "floor-1.jpg"),

    ("2-й этаж", "floor-2.jpg"),

    ("3-й этаж", "floor-3.jpg"),

]

ZAYAV_PDF = "zayavlenie.pdf"

ZVONKI_IMAGE = "zvonki.jpg"

GUIDE_PDF = "gaud.pdf"

SUBJECTS = {

    "math": {"title": "📐 Математика", "list": [

        "• Иванчик Валентина Анатольевна — каб. 314, 300",

        "• Кочеткова Ирина Алексеевна — каб. 105 и Корпус №2",

        "• Селезень Светлана Леонидовна — каб. Корпус №2, 223",

        "• Тимошко Жанна Иосифовна — каб. 312",

    ]},

    "it": {"title": "💻 Информатика", "list": [

        "• Иванчик Валентина Анатольевна — каб. 314, 300",

        "• Кочеткова Ирина Алексеевна — каб. 105 и Корпус №2",

        "• Пантюхова Елена Геннадьевна — каб. 321, 300",

        "• Селезень Светлана Леонидовна — каб. Корпус №2, 223",

        "• Сучок Денис Дмитриевич — каб. 305 и Корпус №2",

    ]},

    "physics": {"title": "⚛️ Физика", "list": [

        "• Скоковский Юрий Иосифович — каб. 204",

        "• Сучок Денис Дмитриевич — каб. 305 и Корпус №2",

        "• Третяк Тамара Александровна — каб. 305",

    ]},

    "chemistry": {"title": "🧪 Химия", "list": [

        "• Купцова Наталья Васильевна — каб. 301",

        "• Садовская Мария Владимировна — каб. 302",

        "• Серко Наталья Анатольевна — каб. Корпус №2",

    ]},

    "biology": {"title": "🌿 Биология", "list": [

        "• Авласевич Снежана Николаевна — каб. 212",

        "• Губич Оксана Антоновна — каб. Корпус №2, 104",

        "• Серко Наталья Анатольевна — каб. Корпус №2",

    ]},

    "rus": {"title": "📖 Русский язык и литература", "list": [

        "• Буда Екатерина Сергеевна — каб. 203",

        "• Сенько Ольга Сергеевна — каб. 203",

    ]},

    "bel": {"title": "📖 Белорусский язык и литература", "list": [

        "• Вайгант Оксана Александровна — каб. 315",

        "• Голговская Елена Петровна — каб. 320",

        "• Пастернак Ирина Владимировна — каб. 212",

    ]},

    "foreign": {"title": "🌍 Иностранный язык", "list": [

        "• Кублицкая Наталья Александровна — каб. 101",

    ]},

    "history": {"title": "📜 История / Обществоведение", "list": [

        "• Караник Елена Викентьевна — каб. 102",

        "• Латушко Александр Иванович — каб. 309",

        "• Монид Татьяна Михайловна — каб. 213",

    ]},

    "geo": {"title": "🗺 География", "list": [

        "• Пантюхова Елена Геннадьевна — каб. 321, 300",

    ]},

    "sport": {"title": "🏃 Физкультура", "list": [

        "• Говзич Владимир Анатольевич — Спортзал",

        "• Гришаенок Виктория Валерьевна — Спортзал",

        "• Есьманович Михаил Леонович — Спортзал",

        "• Рыжевич Олег Адамович — Спортзал",

        "• Цыганкова Екатерина Константиновна — Спортзал",

        "• Яновская Людмила Михайловна — Спортзал",

    ]},

    "med": {"title": "🩺 Медицинская подготовка", "list": [

        "• Губич Оксана Антоновна — каб. Корпус №2, 104",

        "• Кублицкая Наталья Александровна — каб. 101",

    ]},

    "mil": {"title": "🎖 Допризывная подготовка", "list": [

        "• Говзич Владимир Анатольевич — Спортзал",

        "• Крупеньков Виталий Михайлович — каб. 310",

    ]},

    "draw": {"title": "📏 Черчение", "list": [

        "• Велимович Анастасия Викторовна — каб. 314",

    ]},

}

K1_FLOORS_INFO = {

    0: "<b>1 этаж:</b>\n• 119 — отдел кадров\n• 116 — приемная\n• 112 — комендант\n• 111 — руководитель по военно-патриотическому воспитанию\n• 104 — хореографический зал",

    1: "<b>2 этаж:</b>\n• 201 — музей\n• 204 — зам. директора по производству и учебной работе\n• 205 — зав. радиомеханическим отделением\n• 206 — зав. отделением мехатроники\n• 207 — учебная часть\n• 216 — нач. отдела бух. учета\n• 217 — зам. директора по учебно-методической работе\n• 218 — бухгалтерия",

    2: "<b>3 этаж:</b>\n• 323 — архив курсовых работ\n• 313 — служба соц.-пед. поддержки и псих. помощи\n• 307 — зам. директора по воспитательной работе\n• 306 — профком\n• 303 — зав. дневным отделением\n• 300 — печать документов, ксерокопия (платно)",

}

logging.basicConfig(

    level=logging.INFO,

    format="%(asctime)s | %(levelname)s | %(message)s",

    datefmt="%H:%M:%S",

)

log = logging.getLogger("bot")

session = None

bcast_session = None

BOT_START_TS = int(time.time())

STATS = {"pdf_updates": 0, "messages": 0, "documents": 0}

_rate = {}

_muted_until = {}

_admin_state = {}

# ==================== БАЗА ====================

_db = None

def db() -> sqlite3.Connection:

    global _db

    if _db is None:

        _db = sqlite3.connect(DB_FILE, check_same_thread=False, isolation_level=None)

        _db.execute("PRAGMA journal_mode=WAL")

        _db.execute("PRAGMA synchronous=NORMAL")

        _db.execute("CREATE TABLE IF NOT EXISTS subscribers (chat_id INTEGER PRIMARY KEY, subscribed INTEGER DEFAULT 1)")

        _db.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, username TEXT, banned INTEGER DEFAULT 0, created_at INTEGER)")

        _db.execute("CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, username TEXT, action TEXT, ts INTEGER)")

        _db.execute("CREATE TABLE IF NOT EXISTS admins (chat_id INTEGER PRIMARY KEY, since INTEGER)")

        _db.execute("CREATE TABLE IF NOT EXISTS super_admins (chat_id INTEGER PRIMARY KEY, since INTEGER)")

        _db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")

        _db.execute(

            "CREATE TABLE IF NOT EXISTS support_tickets ("

            "id INTEGER PRIMARY KEY AUTOINCREMENT, "

            "user_id INTEGER NOT NULL, "

            "user_username TEXT, "

            "text TEXT NOT NULL, "

            "created_at INTEGER NOT NULL, "

            "assigned_to INTEGER, "

            "replied_by INTEGER, "

            "replied_by_username TEXT, "

            "reply_text TEXT, "

            "replied_at INTEGER)"

        )

        _db.execute("CREATE INDEX IF NOT EXISTS ix_act_chat ON activity(chat_id, ts)")

        _db.execute("CREATE INDEX IF NOT EXISTS ix_act_ts ON activity(ts)")

        _db.execute("CREATE INDEX IF NOT EXISTS ix_tickets_created ON support_tickets(created_at)")

        _db.execute("CREATE INDEX IF NOT EXISTS ix_tickets_assigned ON support_tickets(assigned_to)")

        _db.execute("CREATE INDEX IF NOT EXISTS ix_tickets_replied ON support_tickets(replied_by)")

    return _db

def get_setting(key: str, default=None):

    r = db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()

    return r[0] if r else default

def set_setting(key: str, value):

    db().execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", (key, str(value)))

def del_setting(key: str):

    db().execute("DELETE FROM settings WHERE key=?", (key,))

def get_support_admin():

    v = get_setting("support_admin_id")

    return int(v) if v and str(v).lstrip("-").isdigit() else None

def set_support_admin(cid):

    set_setting("support_admin_id", cid)

def clear_support_admin():

    del_setting("support_admin_id")

def user_name(cid: int) -> str:

    r = db().execute("SELECT username FROM users WHERE chat_id=?", (cid,)).fetchone()

    if r and r[0]:

        return f"@{r[0]}"

    return f"id{cid}"

def register_user(cid: int, username):

    db().execute("INSERT INTO users(chat_id, username, created_at) VALUES(?,?,?) ON CONFLICT(chat_id) DO UPDATE SET username=excluded.username", (cid, username, int(time.time())))

    db().execute("INSERT OR IGNORE INTO subscribers(chat_id, subscribed) VALUES(?, 1)", (cid,))

def is_banned(cid: int) -> bool:

    r = db().execute("SELECT banned FROM users WHERE chat_id=?", (cid,)).fetchone()

    return bool(r and r[0])

def set_ban(cid: int, banned: bool):

    db().execute("UPDATE users SET banned=? WHERE chat_id=?", (1 if banned else 0, cid))

def delete_user(cid: int):

    db().execute("DELETE FROM users WHERE chat_id=?", (cid,))

    db().execute("DELETE FROM subscribers WHERE chat_id=?", (cid,))

    db().execute("DELETE FROM activity WHERE chat_id=?", (cid,))

    _muted_until.pop(cid, None)

    _rate.pop(cid, None)

def log_action(cid: int, username, action: str):

    db().execute("INSERT INTO activity(chat_id, username, action, ts) VALUES(?,?,?,?)", (cid, username, action[:200], int(time.time())))

def cleanup_activity(days: int = 7):

    cutoff = int(time.time()) - days * 86400

    db().execute("DELETE FROM activity WHERE ts < ?", (cutoff,))

def clear_activity():

    db().execute("DELETE FROM activity")

def grant_admin(cid: int):

    db().execute("INSERT OR REPLACE INTO admins(chat_id, since) VALUES(?,?)", (cid, int(time.time())))

def revoke_admin(cid: int):

    db().execute("DELETE FROM admins WHERE chat_id=?", (cid,))

    db().execute("DELETE FROM super_admins WHERE chat_id=?", (cid,))

    if get_support_admin() == cid:

        clear_support_admin()

def is_admin(cid: int) -> bool:

    return bool(db().execute("SELECT 1 FROM admins WHERE chat_id=?", (cid,)).fetchone())

def grant_super(cid: int):

    db().execute("INSERT OR REPLACE INTO super_admins(chat_id, since) VALUES(?,?)", (cid, int(time.time())))

def revoke_super(cid: int):

    db().execute("DELETE FROM super_admins WHERE chat_id=?", (cid,))

def is_super(cid: int) -> bool:

    return bool(db().execute("SELECT 1 FROM super_admins WHERE chat_id=?", (cid,)).fetchone())

def subscribe(cid: int):

    db().execute("INSERT OR REPLACE INTO subscribers(chat_id, subscribed) VALUES(?, 1)", (cid,))

def unsubscribe(cid: int):

    db().execute("UPDATE subscribers SET subscribed=0 WHERE chat_id=?", (cid,))

def is_subscribed(cid: int) -> bool:

    r = db().execute("SELECT subscribed FROM subscribers WHERE chat_id=?", (cid,)).fetchone()

    return bool(r and r[0])

def all_subs():

    query = ("SELECT s.chat_id FROM subscribers s "

             "LEFT JOIN users u ON u.chat_id = s.chat_id "

             "WHERE s.subscribed = 1 AND (u.banned = 0 OR u.banned IS NULL)")

    return [r[0] for r in db().execute(query).fetchall()]

def count_subs() -> int:

    return len(all_subs())

# ==================== ТИКЕТЫ ПОДДЕРЖКИ ====================

def create_ticket(user_id: int, username, text: str) -> int:

    cur = db().execute(

        "INSERT INTO support_tickets(user_id, user_username, text, created_at, assigned_to) "

        "VALUES(?,?,?,?,?)",

        (user_id, username, (text or "")[:4000], int(time.time()), get_support_admin()),

    )

    return cur.lastrowid

def get_ticket(ticket_id: int):

    return db().execute("SELECT * FROM support_tickets WHERE id=?", (ticket_id,)).fetchone()

def reply_ticket(ticket_id: int, admin_id: int, admin_username: str, reply_text: str):

    db().execute(

        "UPDATE support_tickets SET replied_by=?, replied_by_username=?, reply_text=?, replied_at=? "

        "WHERE id=?",

        (admin_id, admin_username or "", (reply_text or "")[:4000], int(time.time()), ticket_id),

    )

# ✅ НОВОЕ: удаление одного тикета

def delete_ticket(ticket_id: int):

    db().execute("DELETE FROM support_tickets WHERE id=?", (ticket_id,))

# ✅ НОВОЕ: удаление всех отвеченных, возвращает количество

def delete_answered_tickets() -> int:

    cur = db().execute("DELETE FROM support_tickets WHERE replied_by IS NOT NULL")

    return cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0

def count_tickets(only_mine=None) -> int:

    if only_mine is not None:

        return db().execute(

            "SELECT COUNT(*) FROM support_tickets WHERE assigned_to=?",

            (only_mine,)

        ).fetchone()[0]

    return db().execute("SELECT COUNT(*) FROM support_tickets").fetchone()[0]

def count_open_tickets() -> int:

    return db().execute("SELECT COUNT(*) FROM support_tickets WHERE replied_by IS NULL").fetchone()[0]

def list_tickets(page=0, per=TICKETS_PER_PAGE, only_mine=None):

    offset = page * per

    if only_mine is not None:

        return db().execute(

            "SELECT id, user_id, user_username, text, created_at, assigned_to, "

            "replied_by, replied_by_username, replied_at "

            "FROM support_tickets WHERE assigned_to=? "

            "ORDER BY created_at ASC LIMIT ? OFFSET ?",

            (only_mine, per, offset),

        ).fetchall()

    return db().execute(

        "SELECT id, user_id, user_username, text, created_at, assigned_to, "

        "replied_by, replied_by_username, replied_at "

        "FROM support_tickets "

        "ORDER BY created_at ASC LIMIT ? OFFSET ?",

        (per, offset),

    ).fetchall()

def tickets_list_text(page: int, only_mine=None, is_super_view: bool = False) -> str:

    rows = list_tickets(page, TICKETS_PER_PAGE, only_mine)

    total = count_tickets(only_mine)

    if not rows:

        return "📭 <b>Обращений пока нет</b>"

    if only_mine is not None and not is_super_view:

        head = f"🆘 <b>Обращения в поддержку</b>"

    else:

        head = f"🆘 <b>Все обращения</b>"

    head += f"\nВсего: {total}"

    if total > TICKETS_PER_PAGE:

        pages = (total - 1) // TICKETS_PER_PAGE + 1

        head += f" · стр. {page + 1}/{pages}"

    lines = [head, ""]

    current_date = None

    for row in rows:

        tid, user_id, uname, text, created, assigned_to, rep_by, rep_by_name, rep_at = row

        dt = datetime.fromtimestamp(created, tz=TZ)

        day_str = dt.strftime("%d.%m.%Y")

        if day_str != current_date:

            lines.append(f"\n📅 <b>{day_str}</b>")

            current_date = day_str

        t = dt.strftime("%H:%M")

        status = "✅" if rep_by_name else "🆕"

        name = f"@{uname}" if uname else f"id{user_id}"

        preview = (text or "").replace("\n", " ").strip()[:45]

        if len((text or "")) > 45:

            preview += "…"

        lines.append(f"{status} <code>#{tid}</code> {t} — {name}: {preview}")

        if is_super_view and rep_by_name:

            lines.append(f"     ↳ ответил: <b>@{rep_by_name}</b>")

    return "\n".join(lines)

def ticket_view_text(ticket_id: int, is_super_view: bool = False) -> str:

    t = get_ticket(ticket_id)

    if not t:

        return "❌ Обращение не найдено"

    (tid, user_id, user_uname, text, created, assigned_to,

     rep_by, rep_by_name, rep_text, rep_at) = t

    name = f"@{user_uname}" if user_uname else f"id{user_id}"

    dt = datetime.fromtimestamp(created, tz=TZ).strftime("%d.%m.%Y %H:%M")

    lines = [

        f"🆘 <b>Обращение #{tid}</b>",

        "",

        f"👤 От: <b>{name}</b> (<code>{user_id}</code>)",

        f"🕐 Время: <b>{dt}</b>",

    ]

    if assigned_to:

        lines.append(f"🎯 Кому: <b>{user_name(assigned_to)}</b>")

    else:

        lines.append(f"🎯 Кому: <i>не назначено</i>")

    lines.append("")

    lines.append("💬 <b>Текст обращения:</b>")

    lines.append(f"<pre>{html.escape((text or '')[:3000])}</pre>")

    if rep_by_name:

        rdt = datetime.fromtimestamp(rep_at, tz=TZ).strftime("%d.%m.%Y %H:%M") if rep_at else "—"

        lines.append("")

        lines.append(f"✅ <b>Ответил:</b> <b>@{rep_by_name}</b>")

        lines.append(f"🕐 {rdt}")

        lines.append("💬 <b>Текст ответа:</b>")

        lines.append(f"<pre>{html.escape((rep_text or '')[:2000])}</pre>")

    else:

        lines.append("")

        lines.append("⏳ <b>Ожидает ответа</b>")

    return "\n".join(lines)

# ==================== АНТИ-СПАМ ====================

def check_rate(cid: int) -> bool:

    now = time.time()

    if _muted_until.get(cid, 0) > now:

        return False

    dq = _rate.setdefault(cid, deque())

    while dq and now - dq[0] > RATE_WINDOW:

        dq.popleft()

    dq.append(now)

    if len(dq) > RATE_LIMIT:

        _muted_until[cid] = now + MUTE_SECONDS

        dq.clear()

        return False

    return True

def mute_remaining(cid: int) -> int:

    return max(0, int(_muted_until.get(cid, 0) - time.time()))

def mute_user(cid: int, seconds: int):

    _muted_until[cid] = time.time() + seconds

def unmute_user(cid: int):

    _muted_until.pop(cid, None)

# ==================== PDF ====================

_chttp = None

_chttp_failed = False

def _get_chttp():

    global _chttp, _chttp_failed

    if _chttp is None and not _chttp_failed:

        try:

            from curl_cffi import requests as r

            _chttp = r

            log.info("✅ curl_cffi подключён")

        except ImportError:

            _chttp_failed = True

            log.warning("⚠️ curl_cffi не установлен — работаю через urllib. "

                        "Установи: pip install curl_cffi")

    return _chttp

_HEADERS = {

    "Referer": REFERER,

    "Accept": "application/pdf,application/octet-stream,*/*",

    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",

    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "

                   "AppleWebKit/537.36 (KHTML, like Gecko) "

                   "Chrome/124.0.0.0 Safari/537.36"),

    "Cache-Control": "no-cache, no-store, must-revalidate",

    "Pragma": "no-cache",

}

def _fetch_urllib(url: str):

    import urllib.request, ssl

    try:

        ctx = ssl.create_default_context()

        ctx.check_hostname = False

        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, headers=_HEADERS)

        with urllib.request.urlopen(req, timeout=60, context=ctx) as r:

            data = r.read()

            if data.startswith(b"%PDF"):

                return data

            log.warning("urllib: ответ не PDF (%d байт)", len(data))

    except Exception as e:

        log.warning("urllib exception: %s", e)

    return None

def _fetch_sync(url: str, impersonate: str):

    ch = _get_chttp()

    if ch is None:

        return _fetch_urllib(url)

    try:

        r = ch.get(url, impersonate=impersonate, headers=_HEADERS,

                   timeout=60, verify=False, allow_redirects=True)

        if r.status_code == 200 and r.content.startswith(b"%PDF"):

            return r.content

        log.warning("curl_cffi: статус %s, размер %d", r.status_code, len(r.content or b""))

    except Exception as e:

        log.warning("curl_cffi exception: %s", e)

    return None

async def fetch_pdf():

    ts_url = f"{PDF_URL}?t={int(time.time() * 1000)}"

    variants = [

        (ts_url, "chrome"),

        (PDF_URL, "chrome"),

        (ts_url, "firefox"),

        (PDF_URL, "firefox"),

    ]

    for u, imp in variants:

        c = await asyncio.to_thread(_fetch_sync, u, imp)

        if c is not None:

            log.info("✅ PDF скачан (%d байт)", len(c))

            return c

    log.warning("❌ fetch_pdf: все %d попыток провалились", len(variants))

    return None

def same_as_disk(content: bytes) -> bool:

    if not os.path.exists(PDF_PATH):

        return False

    try:

        if os.path.getsize(PDF_PATH) != len(content):

            return False

        with open(PDF_PATH, "rb") as f:

            off = 0

            while True:

                chunk = f.read(CHUNK)

                if not chunk:

                    return True

                if chunk != content[off:off + CHUNK]:

                    return False

                off += len(chunk)

    except OSError:

        return False

def save_pdf(content: bytes):

    with open(PDF_PATH, "wb") as f:

        f.write(content)

def pdf_date_str() -> str:

    if not os.path.exists(PDF_PATH):

        return "нет данных"

    return datetime.fromtimestamp(os.path.getmtime(PDF_PATH), tz=TZ).strftime("%d.%m.%Y в %H:%M")

def pdf_age_str() -> str:

    if not os.path.exists(PDF_PATH):

        return "PDF ещё не скачивался"

    secs = int(time.time() - os.path.getmtime(PDF_PATH))

    if secs < 60:

        return "только что"

    if secs < 3600:

        return f"{secs // 60} мин назад"

    if secs < 86400:

        return f"{secs // 3600} ч назад"

    return f"{secs // 86400} дн назад"

async def download_if_changed() -> bool:

    content = await fetch_pdf()

    if content is None:

        log.warning("⚠️ PDF не скачан — сайт недоступен или сменил формат")

        return False

    if same_as_disk(content):

        log.info("PDF не изменился (%d байт)", len(content))

        return False

    save_pdf(content)

    STATS["pdf_updates"] += 1

    log.info("✅ НОВЫЙ PDF сохранён — %d байт", len(content))

    return True

def generate_guide_pdf():

    try:

        from fpdf import FPDF

    except ImportError:

        log.error("Библиотека fpdf2 не установлена. Выполни: pip install fpdf2")

        return None

    pdf = FPDF()

    pdf.add_page()

    font_path = "DejaVuSans.ttf"

    if not os.path.exists(font_path):

        sys_fonts = [

            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",

            "/usr/share/fonts/TTF/DejaVuSans.ttf",

            "C:\\Windows\\Fonts\\arial.ttf",

            "C:\\Windows\\Fonts\\Arial.ttf",

        ]

        for f in sys_fonts:

            if os.path.exists(f):

                font_path = f

                break

    if not os.path.exists(font_path):

        log.error("Не найден шрифт с поддержкой кириллицы.")

        return None

    pdf.add_font("Font", "", font_path, uni=True)

    pdf.add_font("Font", "B", font_path, uni=True)

    pdf.set_font("Font", size=11)

    guide_text = (

        "ГАЙД ПО РАСПИСАНИЮ И \"МАГИИ ЗВЕЗД\"\n\n"

        "1. ЗВЕЗДЫ И ТРЕУГОЛЬНИКИ (ЧЕТНЫЕ / НЕЧЕТНЫЕ НЕДЕЛИ)\n"

        "Учеба крутится вокруг четных и нечетных недель. В расписании стоят звездочки или треугольники:\n"

        "- Одна звезда (*) / Треугольник вниз — 1-я неделя (НЕЧЕТНАЯ). Смотришь только верхнюю строчку.\n"

        "- Две звезды (**) / Треугольник вверх — 2-я неделя (ЧЕТНАЯ). Смотришь только нижнюю строчку.\n\n"

        "2. ВЕЛИКИЕ И УЖАСНЫЕ ЗАМЕНЫ\n"

        "Основное расписание — это просто план. Проверяй замены на завтра после 14:00–15:00.\n"

        "- Если твоей группы нет в файле замен — учись по обычному расписанию.\n"

        "- Если группа есть — замена важнее! Делай ровно то, что написано в документе.\n"

        "- Всегда проверяй кабинеты и корпуса — группу могли перекинуть!\n\n"

        "3. НАПОМИНАЛКА ПО ЗВОНКАМ\n"

        "- 1-я пара стартует ровно в 08:00.\n"

        "- Большой перерыв: 11:35 – 12:05 (в пятницу — 12:35 – 13:05).\n"

        "- Вторая смена: пары могут идти вплоть до 19:30.\n\n"

        "ЧЕК-ЛИСТ НА КАЖДЫЙ ДЕНЬ:\n"

        "1. Проснулся.\n"

        "2. Вспомнил, какая неделя.\n"

        "3. Скачал замены.\n"

        "4. Понял, в какой корпус идти.\n"

        "5. Выдвинулся на пары без паники!\n"

    )

    for line in guide_text.split("\n"):

        if not line.strip():

            pdf.ln(4)

            continue

        if line.startswith(("ГАЙД", "1.", "2.", "3.", "ЧЕК")):

            pdf.set_font("Font", "B", size=12)

            pdf.multi_cell(0, 6, line)

            pdf.set_font("Font", size=11)

        else:

            pdf.multi_cell(0, 6, line)

    pdf.output(GUIDE_PDF)

    return GUIDE_PDF

# ==================== TELEGRAM API ====================

async def api(method: str, params=None, timeout: int = 40):

    try:

        async with session.post(f"{API}/{method}", json=params or {},

                                timeout=aiohttp.ClientTimeout(total=timeout)) as r:

            return await r.json()

    except Exception as e:

        log.warning("%s: %s", method, e)

        return {"ok": False, "description": str(e)}

async def api_bcast(method: str, params=None, timeout: int = 60):

    try:

        async with bcast_session.post(f"{API}/{method}", json=params or {},

                                      timeout=aiohttp.ClientTimeout(total=timeout)) as r:

            return await r.json()

    except Exception as e:

        log.warning("bcast %s: %s", method, e)

        return {"ok": False, "description": str(e)}

async def send_message(chat_id: int, text: str, keyboard=None, parse_mode="HTML"):

    p = {"chat_id": chat_id, "text": text}

    if parse_mode:

        p["parse_mode"] = parse_mode

    if keyboard is not None:

        p["reply_markup"] = keyboard

    r = await api("sendMessage", p)

    if r.get("ok"):

        STATS["messages"] += 1

    return r

async def edit_message(chat_id: int, message_id: int, text: str, keyboard=None, parse_mode="HTML"):

    p = {"chat_id": chat_id, "message_id": message_id, "text": text}

    if parse_mode:

        p["parse_mode"] = parse_mode

    if keyboard is not None:

        p["reply_markup"] = keyboard

    return await api("editMessageText", p)

async def send_document(chat_id: int, path: str, filename: str, caption=None):

    data = FormData()

    data.add_field("chat_id", str(chat_id))

    if caption:

        data.add_field("caption", caption)

        data.add_field("parse_mode", "HTML")

    try:

        with open(path, "rb") as f:

            data.add_field("document", f, filename=filename, content_type="application/octet-stream")

            async with session.post(f"{API}/sendDocument", data=data,

                                    timeout=aiohttp.ClientTimeout(total=120)) as r:

                j = await r.json()

                if j.get("ok"):

                    STATS["documents"] += 1

                return j

    except Exception as e:

        log.warning("sendDocument: %s", e)

        return {"ok": False, "description": str(e)}

async def send_document_bcast(chat_id: int, path: str, filename: str, caption=None):

    data = FormData()

    data.add_field("chat_id", str(chat_id))

    if caption:

        data.add_field("caption", caption)

        data.add_field("parse_mode", "HTML")

    try:

        with open(path, "rb") as f:

            data.add_field("document", f, filename=filename, content_type="application/pdf")

            async with bcast_session.post(f"{API}/sendDocument", data=data,

                                          timeout=aiohttp.ClientTimeout(total=180)) as r:

                j = await r.json()

                if j.get("ok"):

                    STATS["documents"] += 1

                return j

    except Exception as e:

        log.warning("sendDocument(bcast): %s", e)

        return {"ok": False, "description": str(e)}

async def send_photo(chat_id: int, path: str, caption=None):

    data = FormData()

    data.add_field("chat_id", str(chat_id))

    if caption:

        data.add_field("caption", caption)

        data.add_field("parse_mode", "HTML")

    try:

        with open(path, "rb") as f:

            data.add_field("photo", f, filename=os.path.basename(path), content_type="image/jpeg")

            async with session.post(f"{API}/sendPhoto", data=data,

                                    timeout=aiohttp.ClientTimeout(total=120)) as r:

                j = await r.json()

                if j.get("ok"):

                    STATS["documents"] += 1

                return j

    except Exception as e:

        log.warning("sendPhoto: %s", e)

        return {"ok": False, "description": str(e)}

def _parse_retry_after(desc: str) -> int:

    try:

        if "retry after" in desc.lower():

            part = desc.lower().split("retry after", 1)[1]

            return int(part.strip().split()[0])

    except Exception:

        pass

    return 5

async def setup_commands():

    cmds = [

        {"command": "start",         "description": "🏠 Главное меню"},

        {"command": "substitutions", "description": "📄 Актуальные замены"},

        {"command": "schedule",      "description": "📚 Расписания занятий"},

        {"command": "guide",         "description": "📖 Гайд по расписанию (PDF)"},

        {"command": "teachers",      "description": "👨‍🏫 Преподаватели по предметам"},

        {"command": "navigator",     "description": "🧭 Навигатор студента"},

        {"command": "zvonki",        "description": "🔔 Расписание звонков"},

        {"command": "stipendiya",    "description": "🎓 Размеры стипендии"},

        {"command": "building",      "description": "🏫 Корпуса (карты)"},

        {"command": "zayavlenie",    "description": "📝 Заявления"},

        {"command": "support",       "description": "🆘 Техподдержка"},

        {"command": "settings",      "description": "⚙️ Настройки"},

        {"command": "admin",         "description": "🛠 Админ-панель"},

        {"command": "logout",        "description": "🚪 Выйти из админки"},

    ]

    res = await api("setMyCommands", {"commands": cmds})

    if res.get("ok"):

        log.info("Команды бота зарегистрированы")

    else:

        log.warning("setMyCommands: %s", res.get("description"))

    await api("setChatMenuButton", {"menu_button": {"type": "commands"}})

# ==================== КЛАВИАТУРЫ ====================

def kb_main() -> dict:

    return {"inline_keyboard": [

        [{"text": "📄 Актуальные замены", "callback_data": "now"},

         {"text": "📚 Расписания занятий", "callback_data": "sched"}],

        [{"text": "📖 Гайд по расписанию", "callback_data": "guide"},

         {"text": "👨‍🏫 Преподаватели", "callback_data": "teachers"}],

        [{"text": "🧭 Навигатор студента", "callback_data": "nav"}],

        [{"text": "🏫 Корпус 1", "callback_data": "k1"},

         {"text": "🏫 Корпус 2", "callback_data": "k2"}],

        [{"text": "📝 Заявления", "callback_data": "zayav"},

         {"text": "🔔 Звонки", "callback_data": "zvonki"}],

        [{"text": "🎓 Стипендия", "callback_data": "stip"}],

        [{"text": "⚙️ Настройки", "callback_data": "settings"}],

    ]}

def kb_reply() -> dict:

    return {

        "keyboard": [

            [{"text": "📄 Актуальные замены"}, {"text": "📚 Расписания"}],

            [{"text": "📖 Гайд"}, {"text": "👨‍🏫 Преподаватели"}],

            [{"text": "🧭 Навигатор"}, {"text": "🏫 Корпус 1"}],

            [{"text": "🏫 Корпус 2"}, {"text": "📝 Заявления"}],

            [{"text": "🔔 Звонки"}, {"text": "🎓 Стипендия"}],

            [{"text": "⚙️ Настройки"}],

        ],

        "resize_keyboard": True,

        "persistent": True,

        "input_field_placeholder": "Выбери действие…",

    }

def kb_navigator() -> dict:

    return {"inline_keyboard": [

        [{"text": "🏛 Учебные корпуса", "callback_data": "nav:buildings"}],

        [{"text": "🏠 Общежитие", "callback_data": "nav:dorm"},

         {"text": "🚉 Вокзал", "callback_data": "nav:station"}],

        [{"text": "🛒 Магазины", "callback_data": "nav:shops"}],

        [{"text": "☕ Кафе и рестораны", "callback_data": "nav:food"}],

        [{"text": "💊 Аптеки и помощь", "callback_data": "nav:med"}],

        [{"text": "📮 Почта и банкоматы", "callback_data": "nav:mail"}],

        [{"text": "💡 Советы первокурснику", "callback_data": "nav:tips"}],

        [{"text": "◀️ Назад", "callback_data": "back"}],

    ]}

def kb_nav_back() -> dict:

    return {"inline_keyboard": [[{"text": "◀️ В навигатор", "callback_data": "nav"}]]}

def kb_guide() -> dict:

    return {"inline_keyboard": [[{"text": "◀️ Назад", "callback_data": "back"}]]}

def kb_teachers() -> dict:

    return {"inline_keyboard": [

        [{"text": "📐 Математика", "callback_data": "teachers:math"},

         {"text": "💻 Информатика", "callback_data": "teachers:it"}],

        [{"text": "⚛️ Физика", "callback_data": "teachers:physics"},

         {"text": "🧪 Химия", "callback_data": "teachers:chemistry"}],

        [{"text": "🌿 Биология", "callback_data": "teachers:biology"},

         {"text": "🗺 География", "callback_data": "teachers:geo"}],

        [{"text": "📖 Русский язык", "callback_data": "teachers:rus"},

         {"text": "📖 Белорусский язык", "callback_data": "teachers:bel"}],

        [{"text": "🌍 Иностранный", "callback_data": "teachers:foreign"},

         {"text": "📜 История / Общество", "callback_data": "teachers:history"}],

        [{"text": "🏃 Физкультура", "callback_data": "teachers:sport"},

         {"text": "🩺 Мед. подготовка", "callback_data": "teachers:med"}],

        [{"text": "🎖 Допризывная", "callback_data": "teachers:mil"},

         {"text": "📏 Черчение", "callback_data": "teachers:draw"}],

        [{"text": "👨‍🏫 Список всех преподавателей", "callback_data": "teachers:all"}],

        [{"text": "◀️ Назад", "callback_data": "back"}],

    ]}

def kb_teachers_back() -> dict:

    return {"inline_keyboard": [[{"text": "◀️ К предметам", "callback_data": "teachers"}]]}

def kb_settings(uid: int) -> dict:

    if is_subscribed(uid):

        toggle = {"text": "🔕 Выключить уведомления", "callback_data": "settings:toggle"}

    else:

        toggle = {"text": "🔔 Включить уведомления", "callback_data": "settings:toggle"}

    return {"inline_keyboard": [

        [toggle],

        [{"text": "🆘 Техподдержка", "callback_data": "support"}],

        [{"text": "◀️ Назад", "callback_data": "back"}],

    ]}

def kb_support() -> dict:

    return {"inline_keyboard": [

        [{"text": "✍️ Написать в поддержку", "callback_data": "support:write"}],

        [{"text": "◀️ Назад", "callback_data": "settings"}],

    ]}

def kb_support_cancel() -> dict:

    return {"inline_keyboard": [[{"text": "❌ Отмена", "callback_data": "support"}]]}

def kb_stipendiya() -> dict:

    return {"inline_keyboard": [[{"text": "◀️ Назад", "callback_data": "back"}]]}

def kb_schedule() -> dict:

    rows = [[{"text": f"📘 {title} ({sub})", "callback_data": f"sched:{i}"}]

            for i, (title, _fn, sub) in enumerate(SCHEDULES)]

    rows.append([{"text": "◀️ Назад", "callback_data": "back"}])

    return {"inline_keyboard": rows}

def kb_korpus1() -> dict:

    rows = [[{"text": f"🗺 {name}", "callback_data": f"k1:floor:{i}"}]

            for i, (name, _fn) in enumerate(KORPUS1_IMAGES)]

    rows.append([{"text": "◀️ Назад", "callback_data": "back"}])

    return {"inline_keyboard": rows}

def kb_korpus2() -> dict:

    rows = [[{"text": f"🗺 {name}", "callback_data": f"k2:floor:{i}"}]

            for i, (name, _fn) in enumerate(FLOOR_IMAGES)]

    rows.append([{"text": "◀️ Назад", "callback_data": "back"}])

    return {"inline_keyboard": rows}

def kb_zayav() -> dict:

    return {"inline_keyboard": [

        [{"text": "📄 Освобождение от занятий", "callback_data": "zayav:free"}],

        [{"text": "💰 Материальная помощь", "callback_data": "zayav:mat"}],

        [{"text": "📝 Объяснительная", "callback_data": "zayav:ob"}],

        [{"text": "🏢 Заведующие отделениями", "callback_data": "zayav:heads"}],

        [{"text": "📎 Скачать образец PDF", "callback_data": "zayav:pdf"}],

        [{"text": "◀️ Назад", "callback_data": "back"}],

    ]}

def kb_zvonki() -> dict:

    return {"inline_keyboard": [[{"text": "◀️ Назад", "callback_data": "back"}]]}

def kb_admin(uid: int) -> dict:

    rows = [

        [{"text": "👥 Пользователи", "callback_data": "adm:users:0"},

         {"text": "🚫 Бан-лист", "callback_data": "adm:bans"}],

        [{"text": "🛡 Админ-состав", "callback_data": "adm:staff"}],

    ]

    if get_support_admin() == uid:

        open_cnt = count_open_tickets()

        badge = f" ({open_cnt})" if open_cnt else ""

        rows.insert(0, [{"text": f"🆘 Обращения{badge}",

                         "callback_data": "adm:tickets:0"}])

    if is_super(uid):

        rows.insert(0, [{"text": "👑 Super Admin", "callback_data": "sup"}])

    else:

        rows.append([{"text": "👑 Войти как главный админ",

                      "callback_data": "adm:superlogin"}])

    rows.append([{"text": "🚪 Выйти", "callback_data": "adm:logout"}])

    return {"inline_keyboard": rows}

def kb_super() -> dict:

    cur = get_support_admin()

    if cur:

        sup_btn = {"text": f"🆘 Поддержка: {user_name(cur)}", "callback_data": "sup:support_admin"}

    else:

        sup_btn = {"text": "🆘 Ответственный за поддержку", "callback_data": "sup:support_admin"}

    open_cnt = count_open_tickets()

    all_badge = f" ({open_cnt} новых)" if open_cnt else ""

    # ✅ Кнопка «Все обращения» вернулась — доступна суперу и ответственному

    return {"inline_keyboard": [

        [{"text": "📢 Текст всем", "callback_data": "sup:bcast"},

         {"text": "📄 PDF всем", "callback_data": "sup:bcast_pdf"}],

        [{"text": f"🆘 Все обращения{all_badge}", "callback_data": "sup:tickets:0"}],

        [sup_btn],

        [{"text": "💻 Python-консоль", "callback_data": "sup:py"},

         {"text": "🖥 Shell-консоль", "callback_data": "sup:sh"}],

        [{"text": "📡 Telegram API", "callback_data": "sup:api"},

         {"text": "🗄 SQL-запрос", "callback_data": "sup:sql"}],

        [{"text": "🛡 Админы", "callback_data": "sup:admins"},

         {"text": "✉️ DM юзеру", "callback_data": "sup:dm"}],

        [{"text": "📊 Статистика", "callback_data": "sup:stats"},

         {"text": "📈 Топ-10", "callback_data": "sup:top"}],

        [{"text": "🕐 Актив 24ч", "callback_data": "sup:recent"},

         {"text": "📋 Журнал", "callback_data": "sup:act"}],

        [{"text": "🔍 Поиск юзера", "callback_data": "sup:search"},

         {"text": "📥 Экспорт CSV", "callback_data": "sup:export"}],

        [{"text": "🔄 Обновить PDF", "callback_data": "sup:refresh"},

         {"text": "📄 Инфо PDF", "callback_data": "sup:pdf"}],

        [{"text": "♻️ Перезапуск сессий", "callback_data": "sup:reset"},

         {"text": "🧹 Очистить журнал", "callback_data": "sup:clear"}],

        [{"text": "◀️ В админку", "callback_data": "adm"}],

    ]}

# ✅ Обновлено: добавлен параметр can_delete — кнопка очистки отвеченных

def kb_tickets_list(page: int, is_super_view: bool = False, can_delete: bool = False) -> dict:

    per = TICKETS_PER_PAGE

    only_mine = None

    rows = list_tickets(page, per, only_mine)

    total = count_tickets(only_mine)

    kb_rows = []

    for row in rows:

        tid = row[0]

        user_id = row[1]

        uname = row[2]

        rep_name = row[7]

        name = f"@{uname}" if uname else f"id{user_id}"

        mark = "✅ " if rep_name else "🆕 "

        cb = f"sup:ticket:{tid}" if is_super_view else f"adm:ticket:{tid}"

        kb_rows.append([{"text": f"{mark}#{tid} {name}", "callback_data": cb}])

    nav = []

    back_prefix = "sup" if is_super_view else "adm"

    if page > 0:

        nav.append({"text": "◀️", "callback_data": f"{back_prefix}:tickets:{page - 1}"})

    if (page + 1) * per < total:

        nav.append({"text": "▶️", "callback_data": f"{back_prefix}:tickets:{page + 1}"})

    if nav:

        kb_rows.append(nav)

    if can_delete:

        kb_rows.append([{"text": "🧹 Удалить все отвеченные", "callback_data": "sup:ticketclear"}])

    kb_rows.append([{"text": "◀️ Назад", "callback_data": back_prefix}])

    return {"inline_keyboard": kb_rows}

# ✅ Обновлено: добавлен параметр can_delete — кнопка удаления тикета

def kb_ticket_view(tid: int, is_super_view: bool = False, can_delete: bool = False) -> dict:

    t = get_ticket(tid)

    rows = []

    if t and not t[7]:

        rows.append([{"text": "✍️ Ответить", "callback_data": f"sup:reply:{tid}"}])

        rows.append([{"text": "🚫 Забанить автора", "callback_data": f"adm:ban:{t[1]}"}])

    if can_delete:

        rows.append([{"text": "🗑 Удалить обращение", "callback_data": f"sup:ticketdel:{tid}"}])

    back_prefix = "sup" if is_super_view else "adm"

    rows.append([{"text": "◀️ К списку", "callback_data": f"{back_prefix}:tickets:0"}])

    return {"inline_keyboard": rows}

def kb_support_admin_select() -> dict:

    rows = db().execute(

        "SELECT a.chat_id, u.username FROM admins a "

        "LEFT JOIN users u ON u.chat_id=a.chat_id ORDER BY a.since ASC"

    ).fetchall()

    cur = get_support_admin()

    kb_rows = []

    for cid, uname in rows:

        name = f"@{uname}" if uname else f"id{cid}"

        role = "👑 " if is_super(cid) else "🛡 "

        check = "✅ " if cid == cur else ""

        kb_rows.append([{"text": f"{check}{role}{name}", "callback_data": f"sup:setsupport:{cid}"}])

    if not kb_rows:

        kb_rows.append([{"text": "— нет админов —", "callback_data": "sup"}])

    if cur:

        kb_rows.append([{"text": "❌ Снять ответственного (все админы)", "callback_data": "sup:unsetsupport"}])

    kb_rows.append([{"text": "◀️ Назад", "callback_data": "sup"}])

    return {"inline_keyboard": kb_rows}

def kb_super_admins() -> dict:

    rows = db().execute(

        "SELECT a.chat_id, u.username FROM admins a "

        "LEFT JOIN users u ON u.chat_id=a.chat_id ORDER BY a.since DESC"

    ).fetchall()

    kb_rows = []

    for cid, uname in rows:

        mark = "👑 " if is_super(cid) else "🛡 "

        name = f"@{uname}" if uname else f"id{cid}"

        kb_rows.append([{"text": f"{mark}{name}", "callback_data": f"sup:admview:{cid}"}])

    if not kb_rows:

        kb_rows.append([{"text": "— пусто —", "callback_data": "sup"}])

    kb_rows.append([{"text": "➕ Добавить админа", "callback_data": "sup:addadm"}])

    kb_rows.append([{"text": "◀️ Назад", "callback_data": "sup"}])

    return {"inline_keyboard": kb_rows}

def kb_super_admin_view(cid: int) -> dict:

    rows = []

    if is_super(cid):

        rows.append([{"text": "⬇️ Понизить до админа", "callback_data": f"sup:downgrade:{cid}"}])

        rows.append([{"text": "⬇️ Снять Super", "callback_data": f"sup:unsuper:{cid}"}])

    else:

        rows.append([{"text": "⬆️ Сделать Super", "callback_data": f"sup:mksuper:{cid}"}])

    rows.append([{"text": "🗑 Снять админку полностью", "callback_data": f"sup:unadm:{cid}"}])

    rows.append([{"text": "◀️ К списку", "callback_data": "sup:admins"}])

    return {"inline_keyboard": rows}

def kb_admin_user(cid: int, banned: bool) -> dict:

    ban_btn = ({"text": "✅ Разбанить", "callback_data": f"adm:unban:{cid}"}

               if banned else

               {"text": "🚫 Забанить", "callback_data": f"adm:ban:{cid}"})

    return {"inline_keyboard": [

        [{"text": "⏸ Мут 5 мин", "callback_data": f"adm:mute5:{cid}"},

         {"text": "⏸ Мут 1 час", "callback_data": f"adm:mute60:{cid}"}],

        [{"text": "▶️ Снять мут", "callback_data": f"adm:unmute:{cid}"},

         {"text": "🚷 Отписать", "callback_data": f"adm:unsub:{cid}"}],

        [ban_btn],

        [{"text": "✉️ Написать", "callback_data": f"adm:msg:{cid}"},

         {"text": "📈 Статистика", "callback_data": f"adm:ustat:{cid}"}],

        [{"text": "📅 История (7д)", "callback_data": f"adm:uhist:{cid}"}],

        [{"text": "🗑 Удалить юзера", "callback_data": f"adm:del:{cid}"}],

        [{"text": "◀️ К списку", "callback_data": "adm:users:0"}],

    ]}

def kb_admin_confirm_delete(cid: int) -> dict:

    return {"inline_keyboard": [

        [{"text": "⚠️ Да, удалить", "callback_data": f"adm:delok:{cid}"}],

        [{"text": "❌ Отмена", "callback_data": f"adm:u:{cid}"}],

    ]}

def kb_admin_users(page: int) -> dict:

    per = 10

    offset = page * per

    rows = db().execute(

        "SELECT u.chat_id, u.username, u.banned, "

        "COALESCE((SELECT MAX(ts) FROM activity a WHERE a.chat_id=u.chat_id), u.created_at) AS last_ts "

        "FROM users u ORDER BY last_ts DESC LIMIT ? OFFSET ?", (per, offset)

    ).fetchall()

    total = db().execute("SELECT COUNT(*) FROM users").fetchone()[0]

    kb_rows = []

    for cid, uname, banned, last_ts in rows:

        mark = "🚫 " if banned else ""

        name = f"@{uname}" if uname else f"id{cid}"

        t = datetime.fromtimestamp(last_ts, tz=TZ).strftime("%d.%m %H:%M")

        kb_rows.append([{"text": f"{mark}{name} · {t}", "callback_data": f"adm:u:{cid}"}])

    nav = []

    if page > 0:

        nav.append({"text": "◀️", "callback_data": f"adm:users:{page - 1}"})

    if offset + per < total:

        nav.append({"text": "▶️", "callback_data": f"adm:users:{page + 1}"})

    if nav:

        kb_rows.append(nav)

    kb_rows.append([{"text": "◀️ В админку", "callback_data": "adm"}])

    return {"inline_keyboard": kb_rows}

def kb_admin_bans() -> dict:

    rows = db().execute(

        "SELECT chat_id, username FROM users WHERE banned=1 ORDER BY created_at DESC LIMIT 30"

    ).fetchall()

    kb_rows = []

    for cid, uname in rows:

        name = f"@{uname}" if uname else f"id{cid}"

        kb_rows.append([{"text": f"✅ Разбанить {name}", "callback_data": f"adm:unban:{cid}"}])

    if not kb_rows:

        kb_rows.append([{"text": "— пусто —", "callback_data": "adm"}])

    kb_rows.append([{"text": "◀️ В админку", "callback_data": "adm"}])

    return {"inline_keyboard": kb_rows}

def kb_admin_staff(uid: int) -> dict:

    rows = [[{"text": "◀️ В админку", "callback_data": "adm"}]]

    if is_super(uid):

        rows.insert(0, [{"text": "🛠 Управление админами", "callback_data": "sup:admins"}])

        rows.insert(0, [{"text": "🆘 Ответственный за поддержку", "callback_data": "sup:support_admin"}])

    return {"inline_keyboard": rows}

def kb_cancel(target: str = "adm") -> dict:

    return {"inline_keyboard": [[{"text": "❌ Отмена", "callback_data": target}]]}

def kb_super_cancel() -> dict:

    return {"inline_keyboard": [[{"text": "❌ Отмена", "callback_data": "sup"}]]}

# ==================== ТЕКСТЫ ====================

def main_text() -> str:

    return ("👋 Привет! Я бот замен МПК.\n\n"

            "Слежу за расписанием и присылаю свежие замены, "

            "как только они появляются на сайте колледжа.\n\n"

            "Выбери действие:")

def support_text() -> str:

    cur = get_support_admin()

    if cur:

        who = f"👤 Отвечает: <b>{user_name(cur)}</b>"

    else:

        who = "👤 Отвечают дежурные администраторы"

    return (

        "🆘 <b>Техподдержка</b>\n\n"

        f"{who}\n\n"

        "Если что-то не работает, не приходят замены, "

        "или ты нашёл ошибку — напиши нам.\n\n"

        "📩 Нажми кнопку ниже и опиши проблему одним сообщением.\n"

        "Ответ придёт сюда же в чат.\n\n"

        "⚠️ Спам и оскорбления → бан."

    )

def settings_text(uid: int) -> str:

    status = "🔔 Включены" if is_subscribed(uid) else "🔕 Выключены"

    cur = get_support_admin()

    sup_line = f"🆘 Техподдержка ({user_name(cur)})" if cur else "🆘 Техподдержка"

    return (

        "⚙️ <b>Настройки</b>\n\n"

        f"Статус уведомлений: {status}\n"

        f"Подписчиков всего: {count_subs()}\n\n"

        "📋 <b>Что умеет бот</b>\n"

        "• Автоматически присылает PDF с заменами\n"

        "• Расписания занятий — PDF на 1–4 курс\n"

        "• Навигатор студента — карты, общежитие, кафе\n"

        "• Гайд по расписанию (PDF)\n"

        "• Преподаватели по предметам\n"

        "• Карты этажей Корпусов 1 и 2\n"

        "• Расписание звонков\n"

        "• 🎓 Размеры стипендии\n"

        "• Образцы заявлений\n"

        f"• {sup_line}\n\n"

        f"🗓 Последнее обновление замен: {pdf_date_str()} ({pdf_age_str()})"

    )

def schedule_text() -> str:

    return "📚 <b>Расписания занятий</b>\n\nВыбери свой курс — пришлю PDF-файл."

def stipendiya_text() -> str:

    return (

        "🎓 <b>Размеры стипендии</b>\n\n"

        "📊 <b>Средний балл</b> ➡️ <b>Размер стипендии</b>\n\n"

        "▫️ до 4,95 — <b>0р.</b>\n"

        "▫️ 4,95 – 5,9 — <b>144р. 14к.</b>\n"

        "▫️ 6,0 – 7,9 — <b>172р. 97к.</b>\n"

        "▫️ 8,0 – 8,9 — <b>201р. 80к.</b>\n"

        "▫️ 9,0 – 10,0 — <b>230р. 63к.</b>\n\n"

        "📌 <i>Размер стипендии зависит от среднего балла за семестр.</i>"

    )

def teachers_text(subject: str = None) -> str:

    if subject and subject in SUBJECTS:

        s = SUBJECTS[subject]

        return f"👨‍🏫 <b>{s['title']}</b>\n\n" + "\n".join(s['list'])

    return ("👨‍🏫 <b>Преподаватели</b>\n\n"

            "Выбери предмет, чтобы узнать, кто его ведет и в каком кабинете:")

def teachers_full_text() -> str:

    lines = ["👨‍🏫 <b>Все преподаватели по предметам</b>\n"]

    for s in SUBJECTS.values():

        lines.append(f"<b>{s['title']}</b>")

        lines.extend(s['list'])

        lines.append("")

    return "\n".join(lines)

def korpus1_text() -> str:

    return "🏫 <b>Корпус 1</b>\n\nКарты этажей со всеми аудиториями.\n\nВыбери этаж:"

def korpus2_text() -> str:

    return "🏫 <b>Корпус 2</b>\n\nКарты этажей со всеми аудиториями.\n\nВыбери этаж:"

def zvonki_text() -> str:

    return (

        "🔔 <b>Расписание звонков</b>\n\n"

        "• 1-я пара: <b>08:00</b>\n"

        "• Большой перерыв: <b>11:35 – 12:05</b> (Пятница: <b>12:35 – 13:05</b>)\n"

        "• Вторая смена: до <b>19:30</b>\n\n"

        "Не забывай про большой перерыв — это твое законное время, чтобы "

        "добежать до столовки или буфета!"

    )

def zayavlenie_text() -> str:

    return ("📝 <b>Заявления</b>\n\n"

            "Выбери нужный тип заявления. Внутри будет готовый текст, "

            "который можно скопировать в один клик.")

def zayav_free_text() -> str:

    return (

        "📄 <b>Заявление на освобождение от занятий</b>\n\n"

        "Нажми на текст ниже, чтобы скопировать:\n\n"

        "<pre>"

        "ЗАЯВЛЕНИЕ             Заведующему\n"

        "«__» ______ 20__г.    [ФИО],\n"

        "                      учащегося(учащейся)\n"

        "                      гр. [группа]\n"

        "                      [ФИО студента]\n\n"

        "Прошу отпустить меня с занятий [дата] по причине [причина].\n\n"

        "               ______________\n"

        "               подпись учащегося\n\n"

        "Староста    ____________  ____________\n"

        "               подпись       Ф.И.О.\n\n"

        "Куратор     ____________  ____________\n"

        "               подпись       Ф.И.О.\n\n"

        "Зав. отд.   ____________  ____________\n"

        "               подпись       Ф.И.О.\n"

        "</pre>\n\n"

        "⚠️ <b>Порядок оформления:</b>\n"

        "1️⃣ Скачай образец PDF.\n"

        "2️⃣ Заполни синей ручкой.\n"

        "3️⃣ Поставь подпись и дату.\n"

        "4️⃣ Подпиши у <b>старосты группы</b>.\n"

        "5️⃣ Затем у <b>куратора</b>.\n"

        "6️⃣ В конце — у <b>заведующего</b>."

    )

def zayav_mat_text() -> str:

    return (

        "💰 <b>Заявление на материальную помощь</b>\n\n"

        "Нажми на текст ниже, чтобы скопировать:\n\n"

        "<pre>"

        "ЗАЯВЛЕНИЕ             Директору ГУО МПК\n"

        "«__» ______ 20__г.    Клокелю М.Н.,\n"

        "                      учащегося(учащейся)\n"

        "                      гр. [группа]\n"

        "                      [ФИО студента]\n\n"

        "Прошу оказать мне материальную помощь в связи с тяжелым материальным положением по причине [причина].\n\n"

        "               ______________\n"

        "               подпись учащегося\n\n"

        "Староста    ____________  ____________\n"

        "               подпись       Ф.И.О.\n\n"

        "Куратор     ____________  ____________\n"

        "               подпись       Ф.И.О.\n\n"

        "Профорг     ____________  ____________\n"

        "               подпись       Ф.И.О.\n\n"

        "Зав. отд.   ____________  ____________\n"

        "               подпись       Ф.И.О.\n"

        "</pre>"

    )

def zayav_ob_text() -> str:

    return (

        "📝 <b>Объяснительная записка</b>\n\n"

        "Нажми на текст ниже, чтобы скопировать:\n\n"

        "<pre>"

        "ОБЪЯСНИТЕЛЬНАЯ        Заведующему\n"

        "«__» ______ 20__г.    [ФИО],\n"

        "                      учащегося(учащейся)\n"

        "                      гр. [группа]\n"

        "                      [ФИО студента]\n\n"

        "Я, [ФИО], отсутствовал(а) на учебных занятиях [дата] по причине [причина].\n\n"

        "               ______________\n"

        "               подпись учащегося\n\n"

        "Староста    ____________  ____________\n"

        "               подпись       Ф.И.О.\n\n"

        "Куратор     ____________  ____________\n"

        "               подпись       Ф.И.О.\n\n"

        "Зав. отд.   ____________  ____________\n"

        "               подпись       Ф.И.О.\n"

        "</pre>"

    )

def zayav_heads_text() -> str:

    return (

        "🏢 <b>Заведующие отделениями</b>\n\n"

        "1. <b>Пищевое технологическое отделение</b>\n"

        "Бузун Наталья Леонидовна — каб. 123 (Корпус №2)\n\n"

        "2. <b>Отделение технологий хлебопродуктов</b>\n"

        "Варпахович Наталья Александровна — каб. 319 (Корпус №2)\n\n"

        "3. <b>Радиомеханическое отделение</b>\n"

        "Шевчук Василий Васильевич — каб. 205 (Корпус №1)\n\n"

        "4. <b>Отделение мехатроники</b>\n"

        "Вечер Ольга Юзефовна — каб. 206 (Корпус №1)\n\n"

        "5. <b>Энергостроительное отделение</b>\n"

        "Кулик Ирина Михайловна — каб. 100 (Корпус №1)"

    )

def nav_main_text() -> str:

    return (

        "🧭 <b>Навигатор студента</b>\n\n"

        "Добро пожаловать в Молодечненский политехнический колледж! "

        "Здесь собраны адреса и ссылки на карты — учебные корпуса, "

        "общежитие, магазины, кафе, аптеки, почта и другое.\n\n"

        "Выбери нужный раздел:"

    )

def nav_buildings_text() -> str:

    return (

        "🏛 <b>Учебные корпуса</b>\n\n"

        "🏢 <b>Корпус № 1</b>\n"

        "Адрес: г. Молодечно, Центральная площадь, 2\n"

        "Карта: https://yandex.by/maps/?text=Молодечно%20Центральная%20площадь%202\n\n"

        "🏢 <b>Корпус № 2</b>\n"

        "Адрес: г. Молодечно, ул. Машерова, 19\n"

        "Карта: https://yandex.by/maps/?text=Молодечно%20улица%20Машерова%2019\n\n"

        "🔀 <b>Как добраться от 1-го ко 2-му:</b>\n"

        "• Пешком: 15–20 минут\n"

        "• Автобус №1: от «Центральная площадь» до «Драмтеатр» (5–10 мин)\n"

        "• Такси: 5–10 минут (около 5–8 BYN)\n"

        "Маршрут: https://yandex.by/maps/?rtext=Молодечно%20Центральная%20площадь%202~Молодечно%20улица%20Машерова%2019\n\n"

        "⚠️ Перед выходом проверь номер корпуса в расписании."

    )

def nav_dorm_text() -> str:

    return (

        "🏠 <b>Общежитие</b>\n\n"

        "Адрес: г. Молодечно, ул. Богдана Хмельницкого, 10\n"

        "Карта: https://yandex.by/maps/?text=Молодечно%20улица%20Богдана%20Хмельницкого%2010\n\n"

        "По вопросам заселения, оплаты и пропуска обращайся к ответственному сотруднику.\n\n"

        "Если ты иногородний — сохрани этот адрес в избранном!"

    )

def nav_station_text() -> str:

    return (

        "🚉 <b>Железнодорожный вокзал</b>\n\n"

        "Карта: https://yandex.by/maps/?text=Молодечно%20железнодорожный%20вокзал\n\n"

        "От вокзала можно доехать до:\n"

        "• Корпус № 1 — Центральная площадь, 2\n"

        "• Корпус № 2 — ул. Машерова, 19\n"

        "• Общежитие — ул. Б. Хмельницкого, 10\n\n"

        "Открой карту, укажи вокзал точкой отправления и выбери маршрут."

    )

def nav_shops_text() -> str:

    return (

        "🛒 <b>Продуктовые магазины</b>\n\n"

        "🛍 <b>Евроопт Market</b> — ул. Машерова, 19А\n"

        "https://yandex.by/maps/?text=Молодечно%20Евроопт%20Машерова%2019А\n\n"

        "🛍 <b>Копеечка</b> — ул. Притыцкого, 27\n"

        "https://yandex.by/maps/?text=Копеечка%20Молодечно%20Притыцкого%2027\n\n"

        "🛍 <b>Маяк</b> — ул. Космонавтов, 8Б\n"

        "https://yandex.by/maps/?text=Маяк%20магазин%20Молодечно%20Космонавтов%208Б\n\n"

        "🛍 <b>Светофор</b> — товары по сниженным ценам\n"

        "https://yandex.by/maps/?text=Светофор%20Молодечно\n\n"

        "💄 <b>Остров чистоты и вкуса</b> — ул. Великий Гостинец, 67\n"

        "https://yandex.by/maps/?text=Остров%20чистоты%20и%20вкуса%20Молодечно%20Великий%20Гостинец%2067"

    )

def nav_food_text() -> str:

    return (

        "☕ <b>Кофейни и десерты</b>\n\n"

        "• <b>Varka</b> — Б. Хмельницкого, 9\n"

        "https://yandex.by/maps/?text=Varka%20Молодечно%20Богдана%20Хмельницкого%209\n\n"

        "• <b>Малина Кофе</b> — Притыцкого, 21\n"

        "https://yandex.by/maps/?text=Малина%20Кофе%20Молодечно%20Притыцкого%2021\n\n"

        "• <b>Брауни</b> — Притыцкого, 25\n"

        "https://yandex.by/maps/?text=Брауни%20Молодечно%20Притыцкого%2025\n\n"

        "🍕 <b>Кафе, рестораны, фастфуд</b>\n\n"

        "• <b>ЕлиБалдели</b> — Притыцкого, 21\n"

        "https://yandex.by/maps/?text=ЕлиБалдели%20Молодечно%20Притыцкого%2021\n\n"

        "• <b>Хинкальня</b> — Притыцкого, 21\n"

        "https://yandex.by/maps/?text=Хинкальня%20Молодечно%20Притыцкого%2021\n\n"

        "• <b>ФО БО</b> — Волынца, 12Б\n"

        "https://yandex.by/maps/?text=ФО%20БО%20Молодечно%20Волынца%2012Б\n\n"

        "• <b>Додо Пицца</b> — Великий Гостинец, 143Б\n"

        "https://yandex.by/maps/?text=Додо%20Пицца%20Молодечно%20Великий%20Гостинец%20143Б\n\n"

        "• <b>Пицца Темпо</b> — Великий Гостинец, 143\n"

        "https://yandex.by/maps/?text=Пицца%20Темпо%20Молодечно%20Великий%20Гостинец%20143\n\n"

        "• <b>KFC</b> — Великий Гостинец, 143Б\n"

        "https://yandex.by/maps/?text=KFC%20Молодечно%20Великий%20Гостинец%20143Б\n\n"

        "• <b>Философия Sushi</b> — Скорины, 19В\n"

        "https://yandex.by/maps/?text=Философия%20Sushi%20Молодечно%20Франтишка%20Скорины%2019В\n\n"

        "• <b>Тунец</b> — Виленская, 8\n"

        "https://yandex.by/maps/?text=Тунец%20Молодечно%20Виленская%208\n\n"

        "• <b>Лагуна</b> — Б. Хмельницкого, 25\n"

        "https://yandex.by/maps/?text=Лагуна%20Молодечно%20Богдана%20Хмельницкого%2025\n\n"

        "• <b>Палац</b> — Центральная площадь, 4\n"

        "https://yandex.by/maps/?text=Палац%20кафе%20Молодечно%20Центральная%20площадь%204\n\n"

        "• <b>А ля Мацеля</b> — Притыцкого, 2\n"

        "https://yandex.by/maps/?text=A%20ля%20Мацеля%20Молодечно%20Притыцкого%202"

    )

def nav_med_text() -> str:

    return (

        "💊 <b>Аптеки и медицинская помощь</b>\n\n"

        "🏥 <b>Аптека «Доминантафарм» № 4</b> — ул. Волынца, 12\n"

        "https://yandex.by/maps/?text=Молодечно%20Доминантафарм%20Волынца%2012\n\n"

        "🏥 <b>Детская больница</b> — ул. Волынца, 8\n"

        "https://yandex.by/maps/?text=Детская%20больница%20Молодечно%20Волынца%208\n\n"

        "🏥 <b>Детская поликлиника</b> — ул. Виленская, 11В\n"

        "https://yandex.by/maps/?text=Детская%20поликлиника%20Молодечно%20Виленская%2011В\n\n"

        "⚠️ <b>Экстренные номера:</b>\n"

        "• 🚑 Скорая — <b>103</b>\n"

        "• 🆘 Единая служба — <b>112</b>"

    )

def nav_mail_text() -> str:

    return (

        "📮 <b>Почта и банкоматы</b>\n\n"

        "📬 <b>Белпочта — отделение № 6</b>\n"

        "ул. Притыцкого, 18\n"

        "https://yandex.by/maps/?text=Молодечно%20Белпочта%20Притыцкого%2018\n\n"

        "Что взять с собой: документ, удостоверяющий личность, "

        "адрес получателя и данные отправления.\n\n"

        "💳 <b>Банкоматы</b>\n"

        "Открой карту и введи запрос «банкоматы Молодечно»:\n"

        "https://yandex.by/maps/?text=банкоматы%20Молодечно"

    )

def nav_tips_text() -> str:

    return (

        "💡 <b>Советы первокурснику</b>\n\n"

        "<b>Перед первым учебным днём:</b>\n"

        "• Сохрани адреса обоих корпусов\n"

        "• Проверь расписание и место занятий\n"

        "• Построй маршрут от вокзала / общежития\n"

        "• Сохрани адрес общежития в телефоне\n"

        "• Узнай, где ближайшие магазины и аптеки\n"

        "• Найди места, где можно поесть между парами\n\n"

        "<b>Если опаздываешь:</b>\n"

        "Проверь адрес корпуса, открой карту и выбери маршрут с учётом времени.\n\n"

        "<b>Совет по экономии:</b>\n"

        "Если живёшь в общежитии — сравни цены в нескольких магазинах. "

        "Закупка на несколько дней обычно дешевле, чем ежедневные обеды в кафе.\n\n"

        "⚠️ Перед посещением проверяй актуальный адрес и часы работы."

    )

def uptime_str() -> str:

    secs = int(time.time() - BOT_START_TS)

    d, rem = divmod(secs, 86400)

    h, rem = divmod(rem, 3600)

    m, s = divmod(rem, 60)

    if d:

        return f"{d}д {h}ч {m}м"

    if h:

        return f"{h}ч {m}м"

    if m:

        return f"{m}м {s}с"

    return f"{s}с"

def admin_panel_text(uid: int) -> str:

    total = db().execute("SELECT COUNT(*) FROM users").fetchone()[0]

    banned = db().execute("SELECT COUNT(*) FROM users WHERE banned=1").fetchone()[0]

    muted = sum(1 for _, t in _muted_until.items() if t > time.time())

    admins = db().execute("SELECT COUNT(*) FROM admins").fetchone()[0]

    head = "👑 <b>Super Admin панель</b>" if is_super(uid) else "🛠 <b>Админ-панель</b>"

    cur = get_support_admin()

    sup_line = f"\n🆘 Ответственный за поддержку: <b>{user_name(cur)}</b>" if cur else ""

    tickets_line = ""

    # ✅ Счётчик обращений виден и ответственному, и суперу

    if get_support_admin() == uid or is_super(uid):

        open_cnt = count_open_tickets()

        total_t = count_tickets(None)

        tickets_line = f"\n🗂 Обращений: {total_t} (открытых: {open_cnt})"

    return (f"{head}\n\n"

            f"👥 Пользователей: {total}\n"

            f"🚫 В бане: {banned}\n"

            f"⏸ В муте: {muted}\n"

            f"🔔 Подписчиков: {count_subs()}\n"

            f"🛡 Админов: {admins}"

            f"{tickets_line}"

            f"{sup_line}\n")

def admin_stats_text() -> str:

    return (

        "📊 <b>Статистика бота</b>\n\n"

        f"⏱ Аптайм: {uptime_str()}\n"

        f"🔄 Обновлений PDF: {STATS['pdf_updates']}\n"

        f"✉️ Сообщений отправлено: {STATS['messages']}\n"

        f"📄 Документов/фото отправлено: {STATS['documents']}\n\n"

        f"👥 Пользователей: {db().execute('SELECT COUNT(*) FROM users').fetchone()[0]}\n"

        f"🔔 Подписчиков: {count_subs()}\n"

        f"🆘 Обращений: {count_tickets(None)} (открытых: {count_open_tickets()})\n"

        f"📋 Записей в журнале: {db().execute('SELECT COUNT(*) FROM activity').fetchone()[0]}\n"

    )

def admin_pdf_text() -> str:

    if not os.path.exists(PDF_PATH):

        return "📄 <b>PDF замен</b>\n\n❌ Файл отсутствует"

    size = os.path.getsize(PDF_PATH) / 1024

    return ("📄 <b>PDF замен</b>\n\n"

            f"📁 Файл: <code>{PDF_PATH}</code>\n"

            f"💾 Размер: {size:.1f} КБ\n"

            f"🗓 Обновлён: {pdf_date_str()}\n"

            f"⏳ Возраст: {pdf_age_str()}")

def admin_staff_text() -> str:

    rows = db().execute(

        "SELECT a.chat_id, u.username, a.since FROM admins a "

        "LEFT JOIN users u ON u.chat_id=a.chat_id ORDER BY a.since ASC"

    ).fetchall()

    if not rows:

        return "🛡 <b>Админ-состав</b>\n\n— пусто —"

    cur = get_support_admin()

    lines = ["🛡 <b>Админ-состав</b>", ""]

    for cid, uname, since in rows:

        role = "👑 Super" if is_super(cid) else "🛡 Админ"

        name = f"@{uname}" if uname else f"id{cid}"

        t = datetime.fromtimestamp(since or 0, tz=TZ).strftime("%d.%m.%Y")

        mark = " 🆘" if cid == cur else ""

        lines.append(f"{role} — {name} (с {t}){mark}")

    return "\n".join(lines)

def admin_user_text(cid: int) -> str:

    row = db().execute("SELECT username, banned, created_at FROM users WHERE chat_id=?", (cid,)).fetchone()

    if not row:

        return "Пользователь не найден."

    uname, banned, created = row

    acts = db().execute("SELECT action, ts FROM activity WHERE chat_id=? ORDER BY ts DESC LIMIT 15", (cid,)).fetchall()

    rem = mute_remaining(cid)

    if banned:

        status = "🚫 забанен"

    elif rem > 0:

        status = f"⏸ в муте ({rem} с)"

    else:

        status = "✅ активен"

    lines = [

        "👤 <b>Пользователь</b>",

        f"ID: <code>{cid}</code>",

        f"Username: @{uname}" if uname else "Username: —",

        f"Статус: {status}",

        f"Подписка: {'🔔 вкл' if is_subscribed(cid) else '🔕 выкл'}",

        f"Админ: {'👑 Super' if is_super(cid) else ('🛡 да' if is_admin(cid) else 'нет')}",

        f"Первый контакт: {datetime.fromtimestamp(created or 0, tz=TZ).strftime('%d.%m.%Y %H:%M')}",

        "",

        "📋 <b>Последние действия:</b>",

    ]

    if not acts:

        lines.append("— пусто —")

    for action, ts in acts:

        t = datetime.fromtimestamp(ts, tz=TZ).strftime("%d.%m %H:%M:%S")

        lines.append(f"<code>{t}</code> — {action}")

    return "\n".join(lines)

def admin_user_stats_text(cid: int) -> str:

    now = int(time.time())

    day, week, month = now - 86400, now - 7 * 86400, now - 30 * 86400

    def cnt(since: int) -> int:

        return db().execute("SELECT COUNT(*) FROM activity WHERE chat_id=? AND ts>=?", (cid, since)).fetchone()[0]

    total = db().execute("SELECT COUNT(*) FROM activity WHERE chat_id=?", (cid,)).fetchone()[0]

    rows = db().execute("SELECT action, COUNT(*) AS c FROM activity WHERE chat_id=? GROUP BY action ORDER BY c DESC LIMIT 5", (cid,)).fetchall()

    row = db().execute("SELECT username, banned, created_at FROM users WHERE chat_id=?", (cid,)).fetchone()

    uname = row[0] if row else None

    banned = bool(row[1]) if row else False

    created = row[2] if row else 0

    lines = [

        f"📈 <b>Статистика</b> <code>{cid}</code>",

        f"Username: @{uname}" if uname else "Username: —",

        f"Первый контакт: {datetime.fromtimestamp(created, tz=TZ).strftime('%d.%m.%Y %H:%M')}",

        f"Забанен: {'да' if banned else 'нет'}",

        f"В муте: {'да' if mute_remaining(cid) > 0 else 'нет'}",

        f"Подписка: {'вкл' if is_subscribed(cid) else 'выкл'}",

        "",

        f"✉️ Всего действий: {total}",

        f"🕐 За 24 часа: {cnt(day)}",

        f"📅 За 7 дней: {cnt(week)}",

        f"📆 За 30 дней: {cnt(month)}",

    ]

    if rows:

        lines.append("")

        lines.append("<b>Топ действий:</b>")

        for action, c in rows:

            lines.append(f"<code>{c}×</code> {action[:60]}")

    return "\n".join(lines)

def admin_user_hist_text(cid: int, days: int = 7) -> str:

    since = int(time.time()) - days * 86400

    rows = db().execute("SELECT action, ts FROM activity WHERE chat_id=? AND ts>=? ORDER BY ts DESC LIMIT 80", (cid, since)).fetchall()

    lines = [f"📅 <b>История за {days} дн.</b> (id <code>{cid}</code>)", ""]

    if not rows:

        lines.append("— пусто —")

    for action, ts in rows:

        t = datetime.fromtimestamp(ts, tz=TZ).strftime("%d.%m %H:%M:%S")

        lines.append(f"<code>{t}</code> — {action[:70]}")

    return "\n".join(lines)

def admin_top_text() -> str:

    since = int(time.time()) - 7 * 86400

    rows = db().execute(

        "SELECT a.chat_id, u.username, COUNT(*) AS c FROM activity a "

        "LEFT JOIN users u ON u.chat_id=a.chat_id WHERE a.ts>=? "

        "GROUP BY a.chat_id ORDER BY c DESC LIMIT 10", (since,)

    ).fetchall()

    lines = ["📈 <b>Топ-10 активных за 7 дней</b>", ""]

    if not rows:

        lines.append("— пусто —")

    for i, (cid, uname, c) in enumerate(rows, 1):

        name = f"@{uname}" if uname else f"id{cid}"

        lines.append(f"{i}. {name} — <code>{c}</code> действий")

    return "\n".join(lines)

def admin_recent_text() -> str:

    since = int(time.time()) - 86400

    rows = db().execute("SELECT chat_id, username, action, ts FROM activity WHERE ts>=? ORDER BY ts DESC LIMIT 40", (since,)).fetchall()

    lines = ["🕐 <b>Актив за 24 часа</b>", ""]

    if not rows:

        lines.append("— пусто —")

    for cid, uname, action, ts in rows:

        t = datetime.fromtimestamp(ts, tz=TZ).strftime("%H:%M:%S")

        who = f"@{uname}" if uname else f"id{cid}"

        lines.append(f"<code>{t}</code> {who}: {action[:60]}")

    return "\n".join(lines)

def admin_activity_text() -> str:

    rows = db().execute("SELECT chat_id, username, action, ts FROM activity ORDER BY ts DESC LIMIT 40").fetchall()

    lines = ["📋 <b>Последняя активность</b>", ""]

    if not rows:

        lines.append("— пусто —")

    for cid, uname, action, ts in rows:

        t = datetime.fromtimestamp(ts, tz=TZ).strftime("%d.%m %H:%M:%S")

        who = f"@{uname}" if uname else f"id{cid}"

        lines.append(f"<code>{t}</code> {who}: {action[:70]}")

    return "\n".join(lines)

def super_help_text() -> str:

    cur = get_support_admin()

    sup_line = f"🆘 <b>Ответственный за поддержку:</b> {user_name(cur)}\n\n" if cur else ""

    return (

        "👑 <b>Super Admin</b>\n\n"

        f"{sup_line}"

        "📢 <b>Текст всем</b>\n"

        "📄 <b>PDF всем</b> (принудительно)\n"

        "🆘 <b>Все обращения</b> (управление + удаление)\n"

        "🆘 <b>Ответственный за поддержку</b>\n"

        "💻 <b>Python-консоль</b>\n"

        "🖥 <b>Shell</b> (DANGEROUS!)\n"

        "📡 <b>API</b>\n"

        "🗄 <b>SQL</b>\n"

        "🛡 <b>Админы</b>\n"

        "✉️ <b>DM</b>\n"

        "📊 <b>Статистика / Топ / Актив / Журнал</b>\n"

        "🔍 <b>Поиск</b>\n"

        "📥 <b>CSV-экспорт</b>\n"

        "🔄 <b>Обновить PDF</b>\n"

        "♻️ <b>Перезапуск сессий</b>\n"

    )

def support_admin_select_text() -> str:

    cur = get_support_admin()

    if cur:

        head = f"🆘 <b>Ответственный за поддержку</b>\n\nСейчас: <b>{user_name(cur)}</b>\n\n"

    else:

        head = "🆘 <b>Ответственный за поддержку</b>\n\nСейчас: <i>не назначен</i> (обращения идут всем админам)\n\n"

    return head + "Выбери, кто будет получать и обрабатывать обращения пользователей:"

# ==================== СЦЕНАРИИ ====================

async def show_current(chat_id: int):

    if not os.path.exists(PDF_PATH):

        await send_message(chat_id, "🔄 Скачиваю актуальный PDF...")

        content = await fetch_pdf()

        if content is None:

            await send_message(chat_id, "❌ Не удалось получить файл с сайта.")

            return

        save_pdf(content)

    else:

        asyncio.create_task(_refresh_bg())

    caption = f"📄 Актуальные замены\n🗓 Обновлено: {pdf_date_str()} ({pdf_age_str()})"

    await send_document(chat_id, PDF_PATH, "Замены.pdf", caption)

async def show_guide(chat_id: int):

    if not os.path.exists(GUIDE_PDF):

        await send_message(chat_id, "⏳ Генерирую PDF-гайд...")

        path = await asyncio.to_thread(generate_guide_pdf)

        if not path or not os.path.exists(path):

            await send_message(chat_id, "❌ Не удалось создать PDF. Проверь `pip install fpdf2`.")

            return

    await send_document(chat_id, GUIDE_PDF, "gaud.pdf", "📖 Гайд по расписанию")

async def _refresh_bg():

    try:

        if await download_if_changed():

            log.info("PDF обновлён в фоне — рассылаю подписчикам")

            await broadcast(force=True)

    except Exception as e:

        log.warning("bg refresh: %s", e)

async def send_schedule(chat_id: int, idx: int):

    if idx < 0 or idx >= len(SCHEDULES):

        await send_message(chat_id, "❌ Неверный номер курса.")

        return

    title, fname, sub = SCHEDULES[idx]

    if not os.path.exists(fname):

        log.warning("Нет файла %s", fname)

        await send_message(chat_id, f"❌ Файл «{title}» не найден рядом с ботом ({fname}).")

        return

    await send_document(chat_id, fname, f"{title}.pdf", f"📘 Расписание — {title}\n🗓 {sub}")

async def send_k1_floor(chat_id: int, idx: int):

    if idx < 0 or idx >= len(KORPUS1_IMAGES):

        await send_message(chat_id, "❌ Неверный номер этажа.")

        return

    name, fname = KORPUS1_IMAGES[idx]

    if not os.path.exists(fname):

        await send_message(chat_id, f"❌ Карта «{name}» не найдена ({fname}).")

        return

    info = K1_FLOORS_INFO.get(idx, "")

    await send_photo(chat_id, fname, f"🗺 Корпус 1 — {name}\n\n{info}")

async def send_k2_floor(chat_id: int, idx: int):

    if idx < 0 or idx >= len(FLOOR_IMAGES):

        await send_message(chat_id, "❌ Неверный номер этажа.")

        return

    name, fname = FLOOR_IMAGES[idx]

    if not os.path.exists(fname):

        await send_message(chat_id, f"❌ Карта «{name}» не найдена ({fname}).")

        return

    await send_photo(chat_id, fname, f"🗺 Корпус 2 — {name}")

async def send_zayav_pdf(chat_id: int):

    if not os.path.exists(ZAYAV_PDF):

        await send_message(chat_id, f"❌ Образец не найден ({ZAYAV_PDF}).")

        return

    await send_document(chat_id, ZAYAV_PDF, "Образец_заявления.pdf", "📝 Образец заявления")

async def send_zvonki(chat_id: int):

    if not os.path.exists(ZVONKI_IMAGE):

        await send_message(chat_id, f"❌ Расписание звонков не найдено ({ZVONKI_IMAGE}).")

        return

    await send_photo(chat_id, ZVONKI_IMAGE, "🔔 Расписание звонков")

# ==================== КОНСОЛИ SUPER ADMIN ====================

async def exec_python(code: str) -> str:

    buf = io.StringIO()

    ns = {"__name__": "__console__"}

    ns.update({

        "asyncio": asyncio, "os": os, "time": time, "json": json,

        "db": db, "log": log, "STATS": STATS,

        "send_message": send_message, "api": api,

        "all_subs": all_subs, "count_subs": count_subs,

        "download_if_changed": download_if_changed,

        "fetch_pdf": fetch_pdf, "save_pdf": save_pdf,

        "broadcast": broadcast,

        "get_support_admin": get_support_admin,

        "set_support_admin": set_support_admin,

        "clear_support_admin": clear_support_admin,

        "create_ticket": create_ticket,

        "get_ticket": get_ticket,

        "reply_ticket": reply_ticket,

        "delete_ticket": delete_ticket,

        "delete_answered_tickets": delete_answered_tickets,

        "list_tickets": list_tickets,

        "count_tickets": count_tickets,

        "count_open_tickets": count_open_tickets,

        "session": session, "bcast_session": bcast_session,

    })

    try:

        try:

            compiled = compile(code, "<console>", "exec")

            with contextlib.redirect_stdout(buf):

                exec(compiled, ns)

        except SyntaxError:

            if "await" in code:

                body = "\n".join("    " + l for l in code.splitlines())

                wrapper = f"async def __c__():\n{body}\n"

                exec(compile(wrapper, "<console>", "exec"), ns)

                with contextlib.redirect_stdout(buf):

                    await ns["__c__"]()

            else:

                raise

    except Exception as e:

        tb = traceback.format_exc()

        return f"❌ {type(e).__name__}: {e}\n{tb[-600:]}"

    out = buf.getvalue()

    return out if out.strip() else "✅ OK"

async def exec_shell(cmd: str, timeout: int = 30) -> str:

    try:

        proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)

        try:

            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        except asyncio.TimeoutError:

            proc.kill()

            return f"⏱ Timeout {timeout}s"

        return stdout.decode(errors="replace") or f"✅ exit={proc.returncode}"

    except Exception as e:

        return f"❌ {type(e).__name__}: {e}"

async def exec_sql(sql: str) -> str:

    try:

        cur = db().execute(sql)

        s = sql.strip().lower()

        if s.startswith(("select", "pragma", "with", "explain")):

            rows = cur.fetchall()

            if not rows:

                return "— пусто —"

            head = [d[0] for d in (cur.description or [])]

            lines = [" | ".join(head)]

            for r in rows[:50]:

                lines.append(" | ".join(str(x) for x in r))

            if len(rows) > 50:

                lines.append(f"… +{len(rows) - 50} строк")

            return "\n".join(lines)

        return f"✅ rowcount={cur.rowcount}"

    except Exception as e:

        return f"❌ {type(e).__name__}: {e}"

async def reset_sessions():

    global session, bcast_session

    for s in (session, bcast_session):

        if s:

            try:

                await s.close()

            except Exception:

                pass

    session = aiohttp.ClientSession(

        timeout=aiohttp.ClientTimeout(total=60, connect=10, sock_read=50),

        connector=aiohttp.TCPConnector(limit=20, ttl_dns_cache=300, keepalive_timeout=30))

    bcast_session = aiohttp.ClientSession(

        timeout=aiohttp.ClientTimeout(total=180, connect=15, sock_read=120),

        connector=aiohttp.TCPConnector(limit=3, ttl_dns_cache=300, keepalive_timeout=30))

async def notify_admins(text: str, exclude=None):

    rows = db().execute("SELECT chat_id FROM admins").fetchall()

    for (cid,) in rows:

        if cid == exclude:

            continue

        try:

            await send_message(cid, text, parse_mode=None)

        except Exception:

            pass

async def admin_broadcast_custom(admin_cid: int, text: str, uname=None):

    who = f"@{uname}" if uname else f"id{admin_cid}"

    subs = all_subs()

    if not subs:

        await send_message(admin_cid, "Подписчиков нет.", kb_super())

        return

    log_action(admin_cid, uname, f"📢 Рассылка от {who}")

    await send_message(admin_cid, f"📢 Начинаю рассылку на {len(subs)}…")

    safe_text = html.escape(text)

    prefix = f"📢 <b>Объявление от {who}</b>\n\n{safe_text}"

    sent = failed = blocked = 0

    for cid in subs:

        if is_banned(cid):

            continue

        r = await api_bcast("sendMessage", {"chat_id": cid, "text": prefix, "parse_mode": "HTML"})

        if not r.get("ok"):

            desc = (r.get("description") or "")

            if "retry after" in desc.lower() or "too many requests" in desc.lower():

                await asyncio.sleep(_parse_retry_after(desc))

                r = await api_bcast("sendMessage", {"chat_id": cid, "text": prefix, "parse_mode": "HTML"})

        if r.get("ok"):

            sent += 1

            STATS["messages"] += 1

        else:

            failed += 1

            err = (r.get("description") or "").lower()

            if any(k in err for k in ("blocked", "deactivated", "chat not found")):

                blocked += 1

                unsubscribe(cid)

        await asyncio.sleep(0.1)

    report = (f"📢 <b>Рассылка завершена</b>\n\n"

              f"👤 Автор: {who}\n"

              f"✅ Доставлено: {sent}\n"

              f"❌ Ошибок: {failed}\n"

              f"🚫 Заблокировали: {blocked}")

    await send_message(admin_cid, report, kb_super())

    await notify_admins(f"📢 Рассылка от {who}\n\n{text[:500]}", exclude=admin_cid)

async def admin_search(admin_cid: int, query: str):

    q = query.strip()

    if q.startswith("@"):

        rows = db().execute("SELECT chat_id, username FROM users WHERE LOWER(username) LIKE LOWER(?) LIMIT 10", (f"%{q[1:]}%",)).fetchall()

    elif q.isdigit():

        r = db().execute("SELECT chat_id, username FROM users WHERE chat_id=?", (int(q),)).fetchone()

        rows = [r] if r else []

    else:

        rows = db().execute("SELECT chat_id, username FROM users WHERE LOWER(username) LIKE LOWER(?) LIMIT 10", (f"%{q}%",)).fetchall()

    if not rows:

        await send_message(admin_cid, "❌ Ничего не найдено.", kb_admin(admin_cid))

        return

    if len(rows) == 1:

        target = rows[0][0]

        await send_message(admin_cid, admin_user_text(target), kb_admin_user(target, is_banned(target)))

        return

    kb_rows = []

    for cid, uname in rows:

        name = f"@{uname}" if uname else f"id{cid}"

        kb_rows.append([{"text": name, "callback_data": f"adm:u:{cid}"}])

    kb_rows.append([{"text": "◀️ Назад", "callback_data": "sup"}])

    await send_message(admin_cid, f"🔍 Найдено {len(rows)}. Выбери:", {"inline_keyboard": kb_rows})

async def admin_export_csv(admin_cid: int):

    path = "users_export.csv"

    try:

        with open(path, "w", encoding="utf-8-sig", newline="") as f:

            f.write("chat_id,username,banned,subscribed,created_at,last_activity\n")

            rows = db().execute(

                "SELECT u.chat_id, u.username, u.banned, "

                "COALESCE(s.subscribed,0) AS sub, u.created_at, "

                "COALESCE((SELECT MAX(ts) FROM activity a WHERE a.chat_id=u.chat_id), u.created_at) AS last_ts "

                "FROM users u LEFT JOIN subscribers s ON s.chat_id=u.chat_id ORDER BY last_ts DESC"

            ).fetchall()

            for cid, uname, banned, sub, created, last_ts in rows:

                f.write(f"{cid},{uname or ''},{banned},{sub},"

                        f"{datetime.fromtimestamp(created or 0, tz=TZ).strftime('%Y-%m-%d %H:%M:%S')},"

                        f"{datetime.fromtimestamp(last_ts or 0, tz=TZ).strftime('%Y-%m-%d %H:%M:%S')}\n")

        await send_document(admin_cid, path, "users_export.csv", f"📥 Экспорт пользователей ({len(rows)} шт.)")

    finally:

        try:

            os.remove(path)

        except OSError:

            pass

# ==================== РАССЫЛКА ====================

async def broadcast(force: bool = False, sender: str | None = None):

    log.info("🔄 Проверяю замены (force=%s)...", force)

    if not force:

        if not await download_if_changed():

            log.info("ℹ️ Изменений нет — рассылка не нужна")

            return

    if not os.path.exists(PDF_PATH):

        log.warning("PDF-файл отсутствует — рассылка пропущена")

        return

    subs = all_subs()

    log.info("📣 Рассылаю PDF на %d подписчиков (sender=%s)", len(subs), sender or "auto")

    if not subs:

        log.info("Подписчиков нет — нечего рассылать")

        return

    if sender:

        caption = f"📢 <b>Рассылка от {sender}</b>\n🔔 Новые замены\n🗓 Обновлено: {pdf_date_str()}"

    else:

        caption = f"🔔 Новые замены\n🗓 Обновлено: {pdf_date_str()}"

    sent = failed = 0

    for cid in subs:

        if is_banned(cid):

            continue

        try:

            res = await send_document_bcast(cid, PDF_PATH, "Замены.pdf", caption)

            if not res.get("ok"):

                desc = res.get("description") or ""

                if "too many requests" in desc.lower() or "retry after" in desc.lower():

                    delay = _parse_retry_after(desc)

                    log.warning("Rate limit: ждём %d сек", delay)

                    await asyncio.sleep(delay)

                    res = await send_document_bcast(cid, PDF_PATH, "Замены.pdf", caption)

            if res.get("ok"):

                sent += 1

            else:

                failed += 1

                err = (res.get("description") or "").lower()

                log.warning("Ошибка отправки для id%d: %s", cid, res.get("description"))

                if any(k in err for k in ("blocked", "not found", "deactivated", "chat not found", "user is deactivated", "bot was blocked")):

                    unsubscribe(cid)

        except Exception as e:

            log.error("Сбой отправки для %d: %s", cid, e)

            failed += 1

        await asyncio.sleep(0.1)

    log.info("✅ Рассылка завершена: OK=%d, ошибок=%d", sent, failed)

# ==================== ОБРАБОТЧИКИ ====================

async def on_message(msg: dict):

    chat_id = msg["chat"]["id"]

    uid = chat_id

    uname = (msg.get("from") or {}).get("username")

    text = msg.get("text", "") or ""

    cmd = text.split()[0].split("@")[0] if text.startswith("/") else ""

    state = _admin_state.get(uid)

    if state:

        if state == "support_msg":

            _admin_state.pop(uid, None)

            text_clean = (text or "").strip()

            if not text_clean:

                await send_message(chat_id, "Пустое сообщение — отменено.", kb_main())

                return

            ticket_id = create_ticket(uid, uname, text_clean)

            name = f"@{uname}" if uname else f"id{uid}"

            cur = get_support_admin()

            header = (

                f"🆘 <b>Новое обращение #{ticket_id}</b>\n"

                f"👤 Ответственный: <b>{user_name(cur) if cur else 'не назначен'}</b>\n\n"

                f"От: {name}\n"

                f"ID: <code>{uid}</code>\n\n"

                f"{html.escape(text_clean)}"

            )

            kb_for_admin = {"inline_keyboard": [

                [{"text": "✍️ Ответить", "callback_data": f"sup:reply:{ticket_id}"}],

                [{"text": "🚫 Забанить", "callback_data": f"adm:ban:{uid}"}],

            ]}

            if cur:

                recipients = {cur}

            else:

                recipients = {r[0] for r in db().execute("SELECT chat_id FROM admins").fetchall()}

            log.info("🆘 Обращение #%d → %s", ticket_id, list(recipients))

            sent_to = 0

            for aid in recipients:

                r = await send_message(aid, header, kb_for_admin)

                if r.get("ok"):

                    sent_to += 1

            log_action(uid, uname, f"🆘 Обращение #{ticket_id}: {text_clean[:80]}")

            if sent_to:

                who = f" ({user_name(cur)})" if cur else ""

                await send_message(

                    chat_id,

                    f"✅ Обращение <b>#{ticket_id}</b> отправлено в поддержку{who}.\n"

                    "Ответ придёт сюда же в чат — жди.",

                    kb_main())

            else:

                await send_message(

                    chat_id,

                    "⚠️ Не удалось доставить — ответственный не в сети. Попробуй позже.",

                    kb_main())

            return

        if state.startswith("sup_reply:"):

            try:

                tid = int(state.split(":", 1)[1])

            except ValueError:

                _admin_state.pop(uid, None)

                return

            _admin_state.pop(uid, None)

            if not text.strip():

                await send_message(chat_id, "Пустой ответ — отменено.", kb_admin(uid))

                return

            # ✅ Ответить может только ответственный

            if not is_admin(uid) or uid != get_support_admin():

                await send_message(chat_id, "❌ Только ответственный за поддержку может отвечать.", kb_main())

                return

            t = get_ticket(tid)

            if not t:

                await send_message(chat_id, f"❌ Обращение #{tid} не найдено.", kb_admin(uid))

                return

            target = t[1]

            author = f"@{uname}" if uname else f"id{uid}"

            prefix = f"🆘 <b>Ответ поддержки {html.escape(author)}</b>\n\n"

            r = await send_message(target, prefix + html.escape(text), kb_main())

            if r.get("ok"):

                reply_ticket(tid, uid, uname or f"id{uid}", text)

                log_action(uid, uname, f"🆘 Ответ на #{tid} → id{target}")

                await send_message(

                    chat_id,

                    f"✅ Ответ отправлен id{target} (обращение #{tid})",

                    kb_admin(uid))

            else:

                await send_message(chat_id, f"❌ Не отправлено: {r.get('description')}", kb_admin(uid))

            return

        if state == "password":

            _admin_state.pop(uid, None)

            pw = text.strip()

            if pw == SUPER_ADMIN_PASSWORD:

                grant_admin(uid); grant_super(uid)

                log_action(uid, uname, "🔑 Вход (super admin)")

                await send_message(chat_id, "👑 Доступ <b>Super Admin</b> разрешён.")

                await send_message(chat_id, admin_panel_text(uid), kb_admin(uid))

            elif pw == ADMIN_PASSWORD:

                grant_admin(uid)

                log_action(uid, uname, "🔑 Вход в админку")

                await send_message(chat_id, "✅ Доступ разрешён.")

                await send_message(chat_id, admin_panel_text(uid), kb_admin(uid))

            else:

                log_action(uid, uname, "❌ Неверный пароль админа")

                await send_message(chat_id, "❌ Неверный пароль.")

            return

        if state == "super_password":

            _admin_state.pop(uid, None)

            pw = text.strip()

            if pw == SUPER_ADMIN_PASSWORD:

                grant_admin(uid); grant_super(uid)

                log_action(uid, uname, "👑 Вход главного админа")

                await send_message(chat_id, "👑 Теперь ты <b>главный админ</b>.")

                await send_message(chat_id, admin_panel_text(uid), kb_admin(uid))

                await send_message(chat_id, super_help_text(), kb_super())

            else:

                log_action(uid, uname, "❌ Неверный пароль главного админа")

                await send_message(chat_id, "❌ Неверный пароль.", kb_admin(uid))

            return

        if not is_admin(uid):

            _admin_state.pop(uid, None)

            return

        if state == "broadcast":

            _admin_state.pop(uid, None)

            if not is_super(uid):

                await send_message(chat_id, "❌ Рассылку может делать только главный админ.", kb_admin(uid))

                return

            if not text:

                await send_message(chat_id, "Пустой текст — отмена.", kb_super())

                return

            await admin_broadcast_custom(uid, text, uname)

            return

        if state == "search":

            _admin_state.pop(uid, None)

            await admin_search(uid, text)

            return

        if state.startswith("msg:"):

            try:

                target = int(state.split(":", 1)[1])

            except ValueError:

                _admin_state.pop(uid, None)

                return

            _admin_state.pop(uid, None)

            r = await send_message(target, text, parse_mode=None)

            if r.get("ok"):

                await send_message(chat_id, f"✅ Отправлено id{target}", kb_admin(uid))

            else:

                await send_message(chat_id, f"❌ Не отправлено: {r.get('description')}", kb_admin(uid))

            return

        if not is_super(uid):

            _admin_state.pop(uid, None)

            return

        if state == "sup_py":

            _admin_state.pop(uid, None)

            out = await exec_python(text)

            await send_message(chat_id, f"💻 <b>Результат:</b>\n<pre>{out[:3500]}</pre>", kb_super())

            return

        if state == "sup_sh":

            _admin_state.pop(uid, None)

            out = await exec_shell(text)

            await send_message(chat_id, f"🖥 <b>Вывод:</b>\n<pre>{out[:3500]}</pre>", kb_super())

            return

        if state == "sup_api":

            _admin_state.pop(uid, None)

            parts = text.split(maxsplit=1)

            method = parts[0].strip()

            params = {}

            if len(parts) > 1:

                try:

                    params = json.loads(parts[1])

                except json.JSONDecodeError as e:

                    await send_message(chat_id, f"❌ JSON error: {e}", kb_super())

                    return

            res = await api(method, params, timeout=60)

            out = json.dumps(res, ensure_ascii=False, indent=2)[:3500]

            await send_message(chat_id, f"📡 <code>{method}</code>:\n<pre>{out}</pre>", kb_super())

            return

        if state == "sup_sql":

            _admin_state.pop(uid, None)

            out = await exec_sql(text)

            await send_message(chat_id, f"🗄 <b>SQL:</b>\n<pre>{out[:3500]}</pre>", kb_super())

            return

        if state == "sup_dm":

            _admin_state.pop(uid, None)

            parts = text.split(maxsplit=1)

            if len(parts) < 2 or not parts[0].lstrip("-").isdigit():

                await send_message(chat_id, "Формат: <code>chat_id текст</code>", kb_super())

                return

            try:

                target = int(parts[0])

            except ValueError:

                await send_message(chat_id, "❌ chat_id должен быть числом.", kb_super())

                return

            r = await send_message(target, parts[1], parse_mode=None)

            if r.get("ok"):

                await send_message(chat_id, f"✅ Отправлено id{target}", kb_super())

            else:

                await send_message(chat_id, f"❌ Ошибка: {r.get('description')}", kb_super())

            return

        if state == "sup_addadm":

            _admin_state.pop(uid, None)

            try:

                target = int(text.strip())

            except ValueError:

                await send_message(chat_id, "❌ Нужен числовой chat_id.", kb_super())

                return

            grant_admin(target)

            log_action(uid, uname, f"🛡 Назначил админа id{target}")

            await notify_admins(f"🛡 id{target} назначен админом.\nАвтор: {f'@{uname}' if uname else f'id{uid}'}")

            await send_message(chat_id, f"✅ id{target} теперь админ.", kb_super())

            return

        _admin_state.pop(uid, None)

    # ---- Команды ----

    if cmd == "/start":

        await send_message(chat_id, main_text(), kb_main())

        await send_message(chat_id, "Кнопки быстрого доступа снизу 👇", kb_reply())

        return

    if cmd == "/substitutions":

        await show_current(chat_id); return

    if cmd == "/schedule":

        await send_message(chat_id, schedule_text(), kb_schedule()); return

    if cmd == "/guide":

        await show_guide(chat_id); return

    if cmd == "/teachers":

        await send_message(chat_id, teachers_text(), kb_teachers()); return

    if cmd == "/navigator":

        await send_message(chat_id, nav_main_text(), kb_navigator()); return

    if cmd == "/zvonki":

        await send_zvonki(chat_id); return

    if cmd == "/stipendiya":

        await send_message(chat_id, stipendiya_text(), kb_stipendiya()); return

    if cmd == "/building":

        await send_message(chat_id, "🏫 Выбери корпус:", {"inline_keyboard": [

            [{"text": "🏫 Корпус 1", "callback_data": "k1"}],

            [{"text": "🏫 Корпус 2", "callback_data": "k2"}]]})

        return

    if cmd == "/zayavlenie":

        await send_message(chat_id, zayavlenie_text(), kb_zayav()); return

    if cmd == "/support":

        await send_message(chat_id, support_text(), kb_support()); return

    if cmd == "/settings":

        await send_message(chat_id, settings_text(uid), kb_settings(uid)); return

    if cmd == "/admin":

        if is_admin(uid):

            await send_message(chat_id, admin_panel_text(uid), kb_admin(uid))

        else:

            _admin_state[uid] = "password"

            await send_message(chat_id, "🔐 Введи пароль администратора:")

        return

    if cmd == "/logout":

        if is_admin(uid):

            revoke_admin(uid)

            log_action(uid, uname, "🚪 Выход из админки")

            await send_message(chat_id, "👋 Вышел из админки.")

        else:

            await send_message(chat_id, "Ты не в админке.")

        return

    if text == "📄 Актуальные замены":       await show_current(chat_id)

    elif text == "📚 Расписания":            await send_message(chat_id, schedule_text(), kb_schedule())

    elif text == "📖 Гайд":                  await show_guide(chat_id)

    elif text == "👨‍🏫 Преподаватели":        await send_message(chat_id, teachers_text(), kb_teachers())

    elif text == "🧭 Навигатор":             await send_message(chat_id, nav_main_text(), kb_navigator())

    elif text == "🏫 Корпус 1":              await send_message(chat_id, korpus1_text(), kb_korpus1())

    elif text == "🏫 Корпус 2":              await send_message(chat_id, korpus2_text(), kb_korpus2())

    elif text == "📝 Заявления":             await send_message(chat_id, zayavlenie_text(), kb_zayav())

    elif text == "🔔 Звонки":                await send_zvonki(chat_id)

    elif text == "🎓 Стипендия":             await send_message(chat_id, stipendiya_text(), kb_stipendiya())

    elif text == "⚙️ Настройки":             await send_message(chat_id, settings_text(uid), kb_settings(uid))

async def on_callback(cb: dict):

    await api("answerCallbackQuery", {"callback_query_id": cb["id"]})

    data = cb.get("data", "")

    msg = cb.get("message") or {}

    chat_id = msg.get("chat", {}).get("id")

    message_id = msg.get("message_id")

    from_user = cb.get("from") or {}

    uid = from_user.get("id")

    uname = from_user.get("username")

    if not chat_id or uid is None:

        return

    # ==== Техподдержка (клиент) ====

    if data == "support":

        await edit_message(chat_id, message_id, support_text(), kb_support())

        return

    if data == "support:write":

        if is_banned(uid):

            return

        if mute_remaining(uid) > 0:

            await api("answerCallbackQuery",

                      {"callback_query_id": cb["id"], "text": "Ты в муте, попробуй позже"})

            return

        _admin_state[uid] = "support_msg"

        cur = get_support_admin()

        who = f"Отвечает: <b>{user_name(cur)}</b>" if cur else "Отвечают дежурные администраторы"

        await edit_message(

            chat_id, message_id,

            f"✍️ <b>Опиши проблему одним сообщением</b>\n\n"

            f"{who}\n\n"

            "Напиши текст — его увидят в поддержке.\n\n"

            "Отмена — кнопка ниже.",

            kb_support_cancel())

        return

    # ==== Обращения: ответственный через меню /admin ====

    if data.startswith("adm:tickets:"):

        if uid != get_support_admin():

            return

        try:

            page = int(data.split(":", 2)[2])

        except ValueError:

            page = 0

        await edit_message(chat_id, message_id,

                           tickets_list_text(page, None, is_super_view=False),

                           kb_tickets_list(page, is_super_view=False))

        return

    if data.startswith("adm:ticket:"):

        if uid != get_support_admin():

            return

        try:

            tid = int(data.split(":", 2)[2])

        except ValueError:

            return

        await edit_message(chat_id, message_id,

                           ticket_view_text(tid, is_super_view=False),

                           kb_ticket_view(tid, is_super_view=False))

        return

    # ==== Обращения: все обращения для супера и ответственного ====

    if data.startswith("sup:tickets:"):

        # ✅ Доступ: супер ИЛИ ответственный

        if not (is_super(uid) or uid == get_support_admin()):

            return

        try:

            page = int(data.split(":", 2)[2])

        except ValueError:

            page = 0

        await edit_message(chat_id, message_id,

                           tickets_list_text(page, None, is_super_view=True),

                           kb_tickets_list(page, is_super_view=True, can_delete=is_super(uid)))

        return

    if data.startswith("sup:ticket:"):

        # ✅ Доступ: супер ИЛИ ответственный

        if not (is_super(uid) or uid == get_support_admin()):

            return

        try:

            tid = int(data.split(":", 2)[2])

        except ValueError:

            return

        await edit_message(chat_id, message_id,

                           ticket_view_text(tid, is_super_view=True),

                           kb_ticket_view(tid, is_super_view=True, can_delete=is_super(uid)))

        return

    # ==== Удаление одного обращения (только супер) ====

    if data.startswith("sup:ticketdel:"):

        if not is_super(uid):

            return

        try:

            tid = int(data.split(":", 2)[2])

        except ValueError:

            return

        t = get_ticket(tid)

        if not t:

            await edit_message(chat_id, message_id,

                               f"❌ Обращение #{tid} уже удалено.",

                               kb_tickets_list(0, is_super_view=True, can_delete=True))

            return

        await edit_message(

            chat_id, message_id,

            f"🗑 <b>Удалить обращение #{tid}?</b>\n\n"

            f"👤 Автор: {user_name(t[1])}\n"

            f"💬 {(t[3] or '')[:150]}\n\n"

            "⚠️ Удаление необратимо.",

            {"inline_keyboard": [

                [{"text": "⚠️ Да, удалить", "callback_data": f"sup:ticketdelok:{tid}"}],

                [{"text": "❌ Отмена", "callback_data": f"sup:ticket:{tid}"}],

            ]})

        return

    if data.startswith("sup:ticketdelok:"):

        if not is_super(uid):

            return

        try:

            tid = int(data.split(":", 2)[2])

        except ValueError:

            return

        delete_ticket(tid)

        log_action(uid, uname, f"🗑 Удалил обращение #{tid}")

        await edit_message(chat_id, message_id,

                           f"✅ Обращение #{tid} удалено.",

                           kb_tickets_list(0, is_super_view=True, can_delete=True))

        return

    # ==== Очистка всех отвеченных (только супер) ====

    if data == "sup:ticketclear":

        if not is_super(uid):

            return

        total = count_tickets(None)

        open_cnt = count_open_tickets()

        answered = total - open_cnt

        await edit_message(

            chat_id, message_id,

            f"🧹 <b>Очистить все отвеченные обращения?</b>\n\n"

            f"📋 Всего обращений: {total}\n"

            f"✅ Отвечено (будут удалены): {answered}\n"

            f"🆕 Открытых (останутся): {open_cnt}\n\n"

            "⚠️ Удаление необратимо.",

            {"inline_keyboard": [

                [{"text": "⚠️ Да, удалить отвеченные", "callback_data": "sup:ticketclearok"}],

                [{"text": "❌ Отмена", "callback_data": "sup:tickets:0"}],

            ]})

        return

    if data == "sup:ticketclearok":

        if not is_super(uid):

            return

        n = delete_answered_tickets()

        log_action(uid, uname, f"🧹 Удалил отвеченные обращения: {n}")

        await edit_message(chat_id, message_id,

                           f"✅ Удалено отвеченных обращений: <b>{n}</b>",

                           kb_tickets_list(0, is_super_view=True, can_delete=True))

        return

    # ==== Ответ на обращение (только ответственный) ====

    if data.startswith("sup:reply:"):

        if uid != get_support_admin():

            return

        try:

            tid = int(data.split(":", 2)[2])

        except ValueError:

            return

        t = get_ticket(tid)

        if not t:

            return

        _admin_state[uid] = f"sup_reply:{tid}"

        author = f"@{uname}" if uname else f"id{uid}"

        await edit_message(

            chat_id, message_id,

            f"✍️ <b>Ответ на обращение #{tid}</b>\n"

            f"👤 Юзер: {user_name(t[1])}\n\n"

            f"Подпись в ответе: <b>{html.escape(author)}</b>\n\n"

            "Напиши текст ответа.",

            kb_cancel("adm"))

        return

    # ==== Назначение ответственного за поддержку ====

    if data == "sup:support_admin":

        if not is_super(uid):

            return

        await edit_message(chat_id, message_id, support_admin_select_text(), kb_support_admin_select())

        return

    if data.startswith("sup:setsupport:"):

        if not is_super(uid):

            return

        try:

            target = int(data.split(":", 2)[2])

        except ValueError:

            return

        if not is_admin(target):

            await edit_message(chat_id, message_id,

                               "❌ Этот пользователь больше не админ.", kb_support_admin_select())

            return

        set_support_admin(target)

        log_action(uid, uname, f"🆘 Назначил ответственного за поддержку id{target}")

        await notify_admins(

            f"🆘 Назначен новый ответственный за поддержку: <b>{user_name(target)}</b>.\n"

            f"Автор: {f'@{uname}' if uname else f'id{uid}'}")

        await edit_message(chat_id, message_id, support_admin_select_text(), kb_support_admin_select())

        return

    if data == "sup:unsetsupport":

        if not is_super(uid):

            return

        old = get_support_admin()

        clear_support_admin()

        log_action(uid, uname, "🆘 Снял ответственного за поддержку")

        if old:

            await notify_admins(

                f"🆘 Ответственный за поддержку {user_name(old)} снят.\n"

                f"Теперь обращения идут всем админам.\n"

                f"Автор: {f'@{uname}' if uname else f'id{uid}'}")

        await edit_message(chat_id, message_id, support_admin_select_text(), kb_support_admin_select())

        return

    # ==== Навигатор ====

    if data == "nav" or data.startswith("nav:"):

        if data == "nav":

            await edit_message(chat_id, message_id, nav_main_text(), kb_navigator())

        elif data == "nav:buildings":

            await edit_message(chat_id, message_id, nav_buildings_text(), kb_nav_back())

        elif data == "nav:dorm":

            await edit_message(chat_id, message_id, nav_dorm_text(), kb_nav_back())

        elif data == "nav:station":

            await edit_message(chat_id, message_id, nav_station_text(), kb_nav_back())

        elif data == "nav:shops":

            await edit_message(chat_id, message_id, nav_shops_text(), kb_nav_back())

        elif data == "nav:food":

            await edit_message(chat_id, message_id, nav_food_text(), kb_nav_back())

        elif data == "nav:med":

            await edit_message(chat_id, message_id, nav_med_text(), kb_nav_back())

        elif data == "nav:mail":

            await edit_message(chat_id, message_id, nav_mail_text(), kb_nav_back())

        elif data == "nav:tips":

            await edit_message(chat_id, message_id, nav_tips_text(), kb_nav_back())

        return

    if data == "teachers":

        await edit_message(chat_id, message_id, teachers_text(), kb_teachers()); return

    elif data.startswith("teachers:"):

        subject = data.split(":", 1)[1]

        if subject == "all":

            await edit_message(chat_id, message_id, teachers_full_text(), kb_teachers_back())

        else:

            await edit_message(chat_id, message_id, teachers_text(subject), kb_teachers_back())

        return

    if data.startswith("zayav:"):

        if data == "zayav:free":

            await edit_message(chat_id, message_id, zayav_free_text(), kb_zayav())

        elif data == "zayav:mat":

            await edit_message(chat_id, message_id, zayav_mat_text(), kb_zayav())

        elif data == "zayav:ob":

            await edit_message(chat_id, message_id, zayav_ob_text(), kb_zayav())

        elif data == "zayav:heads":

            await edit_message(chat_id, message_id, zayav_heads_text(), kb_zayav())

        elif data == "zayav:pdf":

            await send_zayav_pdf(chat_id)

        return

    if data == "stip":

        await edit_message(chat_id, message_id, stipendiya_text(), kb_stipendiya()); return

    if data == "settings:toggle":

        if is_subscribed(uid):

            unsubscribe(uid)

            await edit_message(chat_id, message_id, settings_text(uid), kb_settings(uid))

            await api("answerCallbackQuery", {"callback_query_id": cb["id"], "text": "Уведомления выключены"})

        else:

            subscribe(uid)

            await edit_message(chat_id, message_id, settings_text(uid), kb_settings(uid))

            await api("answerCallbackQuery", {"callback_query_id": cb["id"], "text": "Уведомления включены"})

        return

    if data == "sup" or data.startswith("sup:"):

        if not is_super(uid):

            return

        if data == "sup":

            await edit_message(chat_id, message_id, super_help_text(), kb_super())

        elif data == "sup:bcast":

            _admin_state[uid] = "broadcast"

            await edit_message(chat_id, message_id,

                "📢 <b>Рассылка (Super)</b>\n\nОтправь текст — его получат все подписчики.\n\nОтмена — «❌ Отмена».",

                kb_super_cancel())

        elif data == "sup:bcast_pdf":

            await edit_message(chat_id, message_id, "⏳ Принудительная рассылка PDF...", kb_super())

            content = await fetch_pdf()

            if not content:

                await edit_message(chat_id, message_id, "❌ Не удалось скачать PDF с сайта.", kb_super())

                return

            save_pdf(content)

            who = f"@{uname}" if uname else f"id{uid}"

            await broadcast(force=True, sender=who)

            await edit_message(chat_id, message_id, f"✅ Рассылка PDF от {who} завершена.", kb_super())

        elif data == "sup:py":

            _admin_state[uid] = "sup_py"

            await edit_message(chat_id, message_id,

                "💻 <b>Python-консоль</b>\n\nДоступны: <code>asyncio, os, time, json, db, log, STATS, "

                "send_message, api, all_subs, count_subs, download_if_changed, fetch_pdf, save_pdf, "

                "broadcast, get_support_admin, set_support_admin, clear_support_admin, "

                "create_ticket, get_ticket, reply_ticket, delete_ticket, delete_answered_tickets, "

                "list_tickets, count_tickets, count_open_tickets, "

                "session, bcast_session</code>. Поддерживается <code>await</code>.",

                kb_super_cancel())

        elif data == "sup:sh":

            _admin_state[uid] = "sup_sh"

            await edit_message(chat_id, message_id, "🖥 <b>Shell-консоль</b>\n\n⚠️ Осторожно! Отправь команду:", kb_super_cancel())

        elif data == "sup:api":

            _admin_state[uid] = "sup_api"

            await edit_message(chat_id, message_id,

                "📡 <b>Telegram API</b>\n\nФормат: <code>method {json}</code>\n"

                'Пример: <code>sendMessage {"chat_id":123,"text":"hi"}</code>',

                kb_super_cancel())

        elif data == "sup:sql":

            _admin_state[uid] = "sup_sql"

            await edit_message(chat_id, message_id, "🗄 <b>SQL-запрос</b>\n\nОтправь SQL.", kb_super_cancel())

        elif data == "sup:dm":

            _admin_state[uid] = "sup_dm"

            await edit_message(chat_id, message_id, "✉️ <b>DM юзеру</b>\n\nФормат: <code>chat_id текст</code>", kb_super_cancel())

        elif data == "sup:admins":

            await edit_message(chat_id, message_id, "🛡 <b>Управление админами</b>", kb_super_admins())

        elif data == "sup:addadm":

            _admin_state[uid] = "sup_addadm"

            await edit_message(chat_id, message_id, "➕ Отправь <code>chat_id</code> пользователя.", kb_super_cancel())

        elif data.startswith("sup:admview:"):

            target = int(data.split(":", 2)[2])

            await edit_message(chat_id, message_id, admin_user_text(target), kb_super_admin_view(target))

        elif data.startswith("sup:mksuper:"):

            target = int(data.split(":", 2)[2])

            grant_admin(target); grant_super(target)

            log_action(uid, uname, f"👑 Назначил super id{target}")

            await notify_admins(f"👑 <code>id{target}</code> назначен <b>главным админом</b>.\nАвтор: {f'@{uname}' if uname else f'id{uid}'}")

            await edit_message(chat_id, message_id, admin_user_text(target), kb_super_admin_view(target))

        elif data.startswith("sup:downgrade:"):

            target = int(data.split(":", 2)[2])

            if target == uid:

                await edit_message(chat_id, message_id, "❌ Нельзя понизить самого себя.", kb_super_admin_view(target))

            else:

                revoke_super(target)

                log_action(uid, uname, f"⬇️ Понизил до админа id{target}")

                await notify_admins(f"⬇️ <code>id{target}</code> понижен до обычного админа (был Super).\nАвтор: {f'@{uname}' if uname else f'id{uid}'}")

                await edit_message(chat_id, message_id, admin_user_text(target), kb_super_admin_view(target))

        elif data.startswith("sup:unsuper:"):

            target = int(data.split(":", 2)[2])

            if target == uid:

                await edit_message(chat_id, message_id, "❌ Нельзя снять super с себя.", kb_super_admin_view(target))

            else:

                revoke_super(target)

                log_action(uid, uname, f"⬇️ Снял super с id{target}")

                await notify_admins(f"⬇️ <code>id{target}</code> лишён прав Super.\nАвтор: {f'@{uname}' if uname else f'id{uid}'}")

                await edit_message(chat_id, message_id, admin_user_text(target), kb_super_admin_view(target))

        elif data.startswith("sup:unadm:"):

            target = int(data.split(":", 2)[2])

            if target == uid:

                await edit_message(chat_id, message_id, "❌ Нельзя снять админку с себя.", kb_super_admin_view(target))

            else:

                revoke_admin(target)

                log_action(uid, uname, f"🗑 Снял админку с id{target}")

                await notify_admins(f"🗑 <code>id{target}</code> снят с админки.\nАвтор: {f'@{uname}' if uname else f'id{uid}'}")

                await edit_message(chat_id, message_id, "✅ Доступ снят.", kb_super_admins())

        elif data == "sup:stats":

            await edit_message(chat_id, message_id, admin_stats_text(), kb_super())

        elif data == "sup:pdf":

            await edit_message(chat_id, message_id, admin_pdf_text(), kb_super())

        elif data == "sup:top":

            await edit_message(chat_id, message_id, admin_top_text(), kb_super())

        elif data == "sup:recent":

            await edit_message(chat_id, message_id, admin_recent_text(), kb_super())

        elif data == "sup:act":

            await edit_message(chat_id, message_id, admin_activity_text(), kb_super())

        elif data == "sup:export":

            await admin_export_csv(chat_id)

        elif data == "sup:search":

            _admin_state[uid] = "search"

            await edit_message(chat_id, message_id, "🔍 <b>Поиск</b>\n\nОтправь <code>@username</code> или <code>chat_id</code>.", kb_super_cancel())

        elif data == "sup:clear":

            clear_activity()

            log_action(uid, uname, "🧹 Очистил журнал")

            await edit_message(chat_id, message_id, "🧹 Журнал очищен.", kb_super())

        elif data == "sup:refresh":

            await edit_message(chat_id, message_id, "🔄 Проверяю сайт МПК…", kb_super())

            changed = await download_if_changed()

            if not os.path.exists(PDF_PATH):

                content = await fetch_pdf()

                if content:

                    save_pdf(content)

                    await edit_message(chat_id, message_id, "✅ PDF скачан впервые.", kb_super())

                else:

                    await edit_message(chat_id, message_id, "❌ Не удалось получить файл.", kb_super())

            elif changed:

                await edit_message(chat_id, message_id, f"✅ PDF обновлён!\n{pdf_date_str()}", kb_super())

            else:

                await edit_message(chat_id, message_id, f"ℹ️ Изменений нет.\nТекущий: {pdf_date_str()}", kb_super())

        elif data == "sup:reset":

            await edit_message(chat_id, message_id, "♻️ Пересоздаю HTTP-сессии…", kb_super())

            await reset_sessions()

            await edit_message(chat_id, message_id, "✅ Сессии перезапущены.", kb_super())

        return

    if data == "adm" or data.startswith("adm:"):

        if not is_admin(uid):

            return

        if data == "adm":

            await edit_message(chat_id, message_id, admin_panel_text(uid), kb_admin(uid))

        elif data == "adm:logout":

            revoke_admin(uid)

            log_action(uid, uname, "🚪 Выход из админки")

            await edit_message(chat_id, message_id, "👋 Вышел из админки.", kb_main())

        elif data == "adm:superlogin":

            if is_super(uid):

                await edit_message(chat_id, message_id, "👑 Ты уже главный админ.", kb_super()); return

            _admin_state[uid] = "super_password"

            await edit_message(chat_id, message_id, "🔐 <b>Вход главного админа</b>\n\nОтправь пароль.", kb_cancel("adm"))

        elif data == "adm:staff":

            await edit_message(chat_id, message_id, admin_staff_text(), kb_admin_staff(uid))

        elif data.startswith("adm:users:"):

            try:

                page = int(data.split(":", 2)[2])

            except ValueError:

                page = 0

            await edit_message(chat_id, message_id, f"👥 <b>Пользователи</b> (стр. {page + 1})", kb_admin_users(page))

        elif data == "adm:bans":

            await edit_message(chat_id, message_id, "🚫 <b>Бан-лист</b>\nНажми на юзера, чтобы разбанить:", kb_admin_bans())

        elif data.startswith("adm:u:"):

            target = int(data.split(":", 2)[2])

            await edit_message(chat_id, message_id, admin_user_text(target), kb_admin_user(target, is_banned(target)))

        elif data.startswith("adm:ustat:"):

            target = int(data.split(":", 2)[2])

            kb = {"inline_keyboard": [[{"text": "◀️ Назад", "callback_data": f"adm:u:{target}"}]]}

            await edit_message(chat_id, message_id, admin_user_stats_text(target), kb)

        elif data.startswith("adm:uhist:"):

            target = int(data.split(":", 2)[2])

            kb = {"inline_keyboard": [[{"text": "◀️ Назад", "callback_data": f"adm:u:{target}"}]]}

            await edit_message(chat_id, message_id, admin_user_hist_text(target, 7), kb)

        elif data.startswith("adm:ban:"):

            target = int(data.split(":", 2)[2])

            set_ban(target, True)

            log_action(target, None, "🚫 Забанен админом")

            await edit_message(chat_id, message_id, admin_user_text(target), kb_admin_user(target, True))

        elif data.startswith("adm:unban:"):

            target = int(data.split(":", 2)[2])

            set_ban(target, False)

            log_action(target, None, "✅ Разбанен админом")

            await edit_message(chat_id, message_id, admin_user_text(target), kb_admin_user(target, False))

        elif data.startswith("adm:mute5:"):

            target = int(data.split(":", 2)[2])

            mute_user(target, 300)

            log_action(target, None, "⏸ Мут 5 мин (админ)")

            await edit_message(chat_id, message_id, admin_user_text(target), kb_admin_user(target, is_banned(target)))

        elif data.startswith("adm:mute60:"):

            target = int(data.split(":", 2)[2])

            mute_user(target, 3600)

            log_action(target, None, "⏸ Мут 1 час (админ)")

            await edit_message(chat_id, message_id, admin_user_text(target), kb_admin_user(target, is_banned(target)))

        elif data.startswith("adm:unmute:"):

            target = int(data.split(":", 2)[2])

            unmute_user(target)

            log_action(target, None, "▶️ Снят мут (админ)")

            await edit_message(chat_id, message_id, admin_user_text(target), kb_admin_user(target, is_banned(target)))

        elif data.startswith("adm:unsub:"):

            target = int(data.split(":", 2)[2])

            unsubscribe(target)

            log_action(target, None, "🚷 Отписан админом")

            await edit_message(chat_id, message_id, admin_user_text(target), kb_admin_user(target, is_banned(target)))

        elif data.startswith("adm:msg:"):

            target = int(data.split(":", 2)[2])

            _admin_state[uid] = f"msg:{target}"

            await edit_message(chat_id, message_id,

                f"✉️ <b>Личное сообщение</b> для id <code>{target}</code>\n\nОтправь текст.",

                kb_cancel(f"adm:u:{target}"))

        elif data.startswith("adm:del:"):

            target = int(data.split(":", 2)[2])

            await edit_message(chat_id, message_id,

                f"🗑 <b>Удалить пользователя</b> id <code>{target}</code>?\n\nУдалятся: запись, подписка, вся история.",

                kb_admin_confirm_delete(target))

        elif data.startswith("adm:delok:"):

            target = int(data.split(":", 2)[2])

            delete_user(target)

            log_action(uid, uname, f"🗑 Удалён пользователь id{target}")

            await edit_message(chat_id, message_id, f"✅ Пользователь <code>{target}</code> удалён.", kb_admin(uid))

        return

    if data == "now":

        await show_current(chat_id)

    elif data == "guide":

        await show_guide(chat_id)

    elif data == "settings":

        await edit_message(chat_id, message_id, settings_text(uid), kb_settings(uid))

    elif data == "sched":

        await edit_message(chat_id, message_id, schedule_text(), kb_schedule())

    elif data.startswith("sched:"):

        idx = int(data.split(":", 1)[1])

        await send_schedule(chat_id, idx)

    elif data == "k1":

        await edit_message(chat_id, message_id, korpus1_text(), kb_korpus1())

    elif data.startswith("k1:floor:"):

        idx = int(data.split(":", 2)[2])

        await send_k1_floor(chat_id, idx)

    elif data == "k2":

        await edit_message(chat_id, message_id, korpus2_text(), kb_korpus2())

    elif data.startswith("k2:floor:"):

        idx = int(data.split(":", 2)[2])

        await send_k2_floor(chat_id, idx)

    elif data == "zayav":

        await edit_message(chat_id, message_id, zayavlenie_text(), kb_zayav())

    elif data == "zvonki":

        await send_zvonki(chat_id)

    elif data == "stip":

        await edit_message(chat_id, message_id, stipendiya_text(), kb_stipendiya())

    elif data == "back":

        await edit_message(chat_id, message_id, main_text(), kb_main())

# ==================== ДИСПЕТЧЕР ====================

async def dispatch(upd: dict):

    try:

        if "message" in upd:

            m = upd["message"]

            from_user = m.get("from") or {}

            cid = from_user.get("id") or m.get("chat", {}).get("id")

            uname = from_user.get("username")

            text = m.get("text", "") or ""

            action = f"msg: {text[:120]}" if text else f"msg: [{len(str(m))}b]"

        elif "callback_query" in upd:

            cq = upd["callback_query"]

            from_user = cq.get("from") or {}

            cid = from_user.get("id")

            uname = from_user.get("username")

            action = f"cb: {cq.get('data', '')[:120]}"

        else:

            return

        if cid is None:

            return

        register_user(cid, uname)

        if not is_admin(cid):

            if is_banned(cid):

                return

            if mute_remaining(cid) > 0:

                return

            if not check_rate(cid):

                log_action(cid, uname, "⚠️ MUTED (rate limit)")

                await send_message(cid, "🚫 Слишком много запросов. Ты в муте на 5 минут.")

                return

        state = _admin_state.get(cid)

        if state in ("password", "super_password"):

            log_action(cid, uname, "🔑 Ввод пароля")

        else:

            log_action(cid, uname, action)

        if "message" in upd:

            await on_message(upd["message"])

        elif "callback_query" in upd:

            await on_callback(upd["callback_query"])

    except Exception as e:

        log.exception("handler: %s", e)

# ==================== POLLING ====================

async def poll_loop():

    offset = 0

    backoff = 1

    while True:

        res = await api("getUpdates",

                        {"offset": offset, "timeout": 25, "allowed_updates": ["message", "callback_query"]},

                        timeout=45)

        if not res.get("ok"):

            log.warning("getUpdates failed: %s, retry in %ds", res.get("description"), backoff)

            await asyncio.sleep(backoff)

            backoff = min(backoff * 2, 30)

            continue

        backoff = 1

        for upd in res.get("result", []):

            offset = upd["update_id"] + 1

            asyncio.create_task(dispatch(upd))

# ==================== ПЕРИОДИЧЕСКАЯ ПРОВЕРКА ====================

async def periodic():

    await asyncio.sleep(10)

    while True:

        try:

            await broadcast()

        except Exception as e:

            log.exception("broadcast: %s", e)

        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)

# ==================== ЗАПУСК ====================

async def main():

    global session, bcast_session

    db()

    cleanup_activity(7)

    session = aiohttp.ClientSession(

        timeout=aiohttp.ClientTimeout(total=60, connect=10, sock_read=50),

        connector=aiohttp.TCPConnector(limit=20, ttl_dns_cache=300, keepalive_timeout=30))

    bcast_session = aiohttp.ClientSession(

        timeout=aiohttp.ClientTimeout(total=180, connect=15, sock_read=120),

        connector=aiohttp.TCPConnector(limit=3, ttl_dns_cache=300, keepalive_timeout=30))

    await setup_commands()

    asyncio.create_task(periodic())

    log.info("Бот запущен. Проверка каждые %d мин.", CHECK_INTERVAL_MINUTES)

    cur = get_support_admin()

    log.info("🆘 Ответственный за поддержку: %s", user_name(cur) if cur else "не назначен")

    log.info("🗂 Тикетов в базе: %d (открытых: %d)", count_tickets(None), count_open_tickets())

    try:

        await poll_loop()

    finally:

        await session.close()

        await bcast_session.close()

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        log.info("Остановлено пользователем")