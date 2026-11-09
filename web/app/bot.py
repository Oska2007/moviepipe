from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from .config import settings
from .db import pool

_app: Application | None = None

def _is_url(t: str) -> bool:
    t = (t or "").strip().lower()
    return t.startswith(("http://","https://","magnet:"))

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 *MoviePipe*\n\n"
        "Send me a magnet / torrent / direct link and I'll:\n"
        "1. Download\n2. Encode to x264\n3. Add Sinhala + English soft subs\n"
        "4. Upload to R2 + Telegram backup channel\n\n"
        "After I reply with a Job ID, **reply to that message** with `.srt` files to attach subs.\n\n"
        "Commands: /status ID  /list  /cancel ID",
        parse_mode="Markdown")

async def new_job(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not _is_url(text):
        return
    row = await pool().fetchrow(
        "INSERT INTO jobs(source_url,title) VALUES($1,$2) RETURNING id",
        text, None)
    jid = row["id"]
    msg = await update.message.reply_text(
        f"✅ Job *#{jid}* queued.\nReply to this message with `.srt` files to attach subtitles.",
        parse_mode="Markdown")
    ctx.bot_data.setdefault("job_msgs", {})[msg.message_id] = jid

async def attach_sub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith((".srt", ".ass", ".vtt")):
        return
    rep = update.message.reply_to_message
    if not rep:
        return
    jid = ctx.bot_data.get("job_msgs", {}).get(rep.message_id)
    if not jid:
        return
    name = doc.file_name.lower()
    lang = "sin" if any(k in name for k in ("sin", "si-", "si_", "sinhala")) else "eng"
    d = settings.DATA_DIR / "subs" / str(jid)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{lang}.srt"
    tg_file = await doc.get_file()
    await tg_file.download_to_drive(str(p))
    col = "sub_sinhala" if lang == "sin" else "sub_english"
    await pool().execute(f"UPDATE jobs SET {col}=$1 WHERE id=$2", str(p), jid)
    await update.message.reply_text(f"📎 {lang.upper()} subtitle attached to Job #{jid}")

async def status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        return await update.message.reply_text("Usage: /status <id>")
    r = await pool().fetchrow("SELECT * FROM jobs WHERE id=$1", int(ctx.args[0]))
    if not r:
        return await update.message.reply_text("Not found.")
    await update.message.reply_text(
        f"Job #{r['id']} — {r['status']} {r['progress']}%\n"
        f"{r['message'] or ''}\n{('error: ' + r['error']) if r['error'] else ''}")

async def list_jobs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = await pool().fetch("SELECT id,status,progress,title FROM jobs ORDER BY id DESC LIMIT 15")
    if not rows:
        return await update.message.reply_text("No jobs.")
    txt = "\n".join(f"#{r['id']} {r['status']} {r['progress']}% {(r['title'] or '')[:40]}" for r in rows)
    await update.message.reply_text(txt)

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        return await update.message.reply_text("Usage: /cancel <id>")
    await pool().execute("UPDATE jobs SET status='cancelled' WHERE id=$1 AND status NOT IN ('done','failed')", int(ctx.args[0]))
    await update.message.reply_text("Cancelled.")

async def start_bot():
    global _app
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    _app = (Application.builder()
            .token(settings.TELEGRAM_BOT_TOKEN)
            .base_url(f"{settings.TELEGRAM_BOT_API_URL}/bot")
            .base_file_url(f"{settings.TELEGRAM_BOT_API_URL}/bot")
            .build())
    _app.add_handler(CommandHandler("start", start))
    _app.add_handler(CommandHandler("status", status))
    _app.add_handler(CommandHandler("list", list_jobs))
    _app.add_handler(CommandHandler("cancel", cancel))
    _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, new_job))
    _app.add_handler(MessageHandler(filters.Document.ALL, attach_sub))
    await _app.initialize()
    await _app.start()
    await _app.updater.start_polling(drop_pending_updates=True)

async def stop_bot():
    if _app:
        await _app.updater.stop()
        await _app.stop()
        await _app.shutdown()