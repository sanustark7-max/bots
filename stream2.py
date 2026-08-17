#!/usr/bin/env python3
"""
STARK YOUTUBE LIVE STREAMER – TELEGRAM CONTROLLED (with YouTube Download)
Owner: @Mrstark29 | Channel: @STARK
💀 DEVILS WILL RISE 💀
"""

import os
import subprocess
import threading
import time
import logging
import shutil
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ================================================================
# CONFIG
# ================================================================
BOT_TOKEN = "8450973856:AAG-BXSiayrOxInFYLIgkbOkCAGeH1M7IIM"
ALLOWED_USERS = [5969149339]  # Apna Telegram ID

# ================================================================
# STATE
# ================================================================
STREAM_PROCESS = None
STREAM_ACTIVE = False
CURRENT_VIDEO = None
STREAM_KEY = None
RTMP_URL = "rtmp://a.rtmp.youtube.com/live2"
DOWNLOADING = False
DOWNLOAD_STATUS = ""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================================================
# YOUTUBE DOWNLOAD FUNCTION
# ================================================================
def download_youtube_video(url, output_path="stream_video.mp4"):
    """Download video from YouTube using yt-dlp"""
    try:
        # Remove old file
        if os.path.exists(output_path):
            os.remove(output_path)

        cmd = [
            "yt-dlp",
            "-f", "best[ext=mp4]",
            "--no-playlist",
            "-o", output_path,
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return False, result.stderr
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, "Download successful"
        return False, "File not created"
    except Exception as e:
        return False, str(e)

# ================================================================
# FFMPEG STREAM FUNCTION
# ================================================================
def start_ffmpeg_stream(video_path, stream_key):
    global STREAM_PROCESS, STREAM_ACTIVE
    if STREAM_ACTIVE:
        return False, "Stream already running"

    if not os.path.exists(video_path):
        return False, "Video file not found"

    cmd = [
        "ffmpeg",
        "-re",
        "-stream_loop", "-1",
        "-i", video_path,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-b:v", "2500k",
        "-maxrate", "3000k",
        "-bufsize", "5000k",
        "-pix_fmt", "yuv420p",
        "-g", "60",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-f", "flv",
        f"{RTMP_URL}/{stream_key}"
    ]

    try:
        STREAM_PROCESS = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        STREAM_ACTIVE = True
        return True, "Stream started"
    except Exception as e:
        return False, f"Error: {str(e)}"

def stop_stream():
    global STREAM_PROCESS, STREAM_ACTIVE
    if STREAM_PROCESS:
        STREAM_PROCESS.terminate()
        STREAM_PROCESS.wait(timeout=5)
        STREAM_PROCESS = None
    STREAM_ACTIVE = False
    return True, "Stream stopped"

# ================================================================
# TELEGRAM HANDLERS
# ================================================================

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("⛔ Unauthorized")
        return

    keyboard = [
        [InlineKeyboardButton("▶️ Start Stream", callback_data="start")],
        [InlineKeyboardButton("⏹ Stop Stream", callback_data="stop")],
        [InlineKeyboardButton("📥 Download from YouTube", callback_data="download")],
        [InlineKeyboardButton("🔑 Set Stream Key", callback_data="setkey")],
        [InlineKeyboardButton("📊 Status", callback_data="status")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎬 <b>STARK YouTube Stream Controller</b>\n\n"
        "Use buttons below.\n"
        f"Status: {'🟢 Running' if STREAM_ACTIVE else '🔴 Stopped'}\n"
        f"Video: {CURRENT_VIDEO or 'Not set'}\n"
        f"Stream Key: {STREAM_KEY or 'Not set'}",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await query.edit_message_text("⛔ Unauthorized")
        return

    data = query.data

    if data == "start":
        if not STREAM_KEY:
            await query.edit_message_text("❌ Stream Key not set.")
            return
        if not CURRENT_VIDEO:
            await query.edit_message_text("❌ No video. Use Download or Upload.")
            return
        success, msg = start_ffmpeg_stream(CURRENT_VIDEO, STREAM_KEY)
        await query.edit_message_text(f"{'✅' if success else '❌'} {msg}")

    elif data == "stop":
        success, msg = stop_stream()
        await query.edit_message_text(f"{'✅' if success else '❌'} {msg}")

    elif data == "download":
        await query.edit_message_text("📥 Send YouTube URL (e.g., https://youtu.be/abc123)")
        context.user_data['awaiting_url'] = True

    elif data == "setkey":
        await query.edit_message_text("🔑 Send your YouTube Stream Key")
        context.user_data['awaiting_key'] = True

    elif data == "status":
        status_text = (
            f"📊 <b>Stream Status</b>\n\n"
            f"🟢 Running: {'✅' if STREAM_ACTIVE else '❌'}\n"
            f"📹 Video: {CURRENT_VIDEO or 'Not set'}\n"
            f"🔑 Stream Key: {STREAM_KEY or 'Not set'}\n"
            f"🔗 RTMP: {RTMP_URL}"
        )
        await query.edit_message_text(status_text, parse_mode="HTML")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        return

    # YouTube URL
    if context.user_data.get('awaiting_url'):
        url = update.message.text.strip()
        if url.startswith(('http://', 'https://')) and ('youtube.com' in url or 'youtu.be' in url):
            await update.message.reply_text("🔄 Downloading video... This may take a few minutes.")
            # Run download in thread to avoid blocking
            def download_thread():
                global CURRENT_VIDEO, DOWNLOADING
                DOWNLOADING = True
                success, msg = download_youtube_video(url, "stream_video.mp4")
                DOWNLOADING = False
                if success:
                    CURRENT_VIDEO = "stream_video.mp4"
                    update.message.reply_text(f"✅ Download complete: {CURRENT_VIDEO}")
                else:
                    update.message.reply_text(f"❌ Download failed: {msg}")
            threading.Thread(target=download_thread, daemon=True).start()
            context.user_data['awaiting_url'] = False
        else:
            await update.message.reply_text("❌ Invalid YouTube URL")

    # Stream Key
    elif context.user_data.get('awaiting_key'):
        key = update.message.text.strip()
        if key:
            global STREAM_KEY
            STREAM_KEY = key
            context.user_data['awaiting_key'] = False
            await update.message.reply_text(f"✅ Stream Key set: {STREAM_KEY[:8]}...")
        else:
            await update.message.reply_text("❌ Invalid key")

    else:
        await update.message.reply_text("Use /start to control.")

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✅ Cancelled.")

# ================================================================
# MAIN
# ================================================================

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise SystemExit("❌ Set BOT_TOKEN")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    print("🔥 STARK Stream Bot started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()