#!/usr/bin/env python3
"""
STARK YOUTUBE DOWNLOAD + LOOP STREAM BOT
Owner: @Mrstark29 | Channel: @STARK
💀 DEVILS WILL RISE 💀
"""

import os
import subprocess
import threading
import time
import logging
import re
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ================================================================
# CONFIG – YAHAN APNA BOT TOKEN DAALO
# ================================================================
BOT_TOKEN = "8450973856:AAG-BXSiayrOxInFYLIgkbOkCAGeH1M7IIM"  # @BotFather se lo
ALLOWED_USERS = [5969149339]  # Apna Telegram ID daalo

# ================================================================
# STATE
# ================================================================
STREAM_PROCESS = None
STREAM_ACTIVE = False
CURRENT_VIDEO = None
STREAM_KEY = None
RTMP_URL = "rtmp://a.rtmp.youtube.com/live2"
DOWNLOADING = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================================================
# YOUTUBE DOWNLOAD FUNCTION
# ================================================================
def download_youtube_video(url):
    """Download video from YouTube using yt-dlp"""
    try:
        output_template = "stream_video.%(ext)s"
        cmd = [
            "yt-dlp",
            "-f", "best[height<=1080][ext=mp4]",
            "--no-playlist",
            "-o", output_template,
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            # Find downloaded file
            for f in Path('.').glob('stream_video.*'):
                if f.suffix in ['.mp4', '.mkv', '.webm']:
                    return str(f)
        return None
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None

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
# TELEGRAM COMMANDS
# ================================================================

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("⛔ Unauthorized")
        return

    keyboard = [
        [InlineKeyboardButton("📥 Download YouTube Video", callback_data="download")],
        [InlineKeyboardButton("▶️ Start Stream", callback_data="start")],
        [InlineKeyboardButton("⏹ Stop Stream", callback_data="stop")],
        [InlineKeyboardButton("🔑 Set Stream Key", callback_data="setkey")],
        [InlineKeyboardButton("📊 Status", callback_data="status")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🎬 <b>STARK YouTube Loop Stream Bot</b>\n\n"
        f"1. Send a YouTube link to download video\n"
        f"2. Set Stream Key\n"
        f"3. Start Stream\n\n"
        f"Current status: {'🟢 Running' if STREAM_ACTIVE else '🔴 Stopped'}\n"
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

    if data == "download":
        await query.edit_message_text("📤 Send a YouTube video link (e.g., https://youtu.be/VIDEO_ID)")
        context.user_data['awaiting_youtube_link'] = True

    elif data == "start":
        if not STREAM_KEY:
            await query.edit_message_text("❌ Stream Key not set. Use /start → Set Stream Key")
            return
        if not CURRENT_VIDEO:
            await query.edit_message_text("❌ No video downloaded. Download a YouTube video first.")
            return
        success, msg = start_ffmpeg_stream(CURRENT_VIDEO, STREAM_KEY)
        await query.edit_message_text(f"{'✅' if success else '❌'} {msg}")

    elif data == "stop":
        success, msg = stop_stream()
        await query.edit_message_text(f"{'✅' if success else '❌'} {msg}")

    elif data == "setkey":
        await query.edit_message_text("🔑 Send your YouTube Stream Key (YouTube Studio → Go Live → Stream Settings)")
        context.user_data['awaiting_key'] = True

    elif data == "status":
        status_text = (
            f"📊 <b>Stream Status</b>\n\n"
            f"🟢 Running: {'✅' if STREAM_ACTIVE else '❌'}\n"
            f"📹 Video: {CURRENT_VIDEO or 'Not set'}\n"
            f"🔑 Stream Key: {STREAM_KEY or 'Not set'}\n"
            f"🔗 RTMP URL: {RTMP_URL}"
        )
        await query.edit_message_text(status_text, parse_mode="HTML")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        return

    # YouTube link download
    if context.user_data.get('awaiting_youtube_link'):
        url = update.message.text.strip()
        if "youtube.com" in url or "youtu.be" in url:
            await update.message.reply_text("⬇️ Downloading video... Please wait.")
            video_path = download_youtube_video(url)
            if video_path:
                global CURRENT_VIDEO
                CURRENT_VIDEO = video_path
                context.user_data['awaiting_youtube_link'] = False
                await update.message.reply_text(f"✅ Video downloaded: {video_path}\nUse /start to control stream.")
            else:
                await update.message.reply_text("❌ Failed to download video. Check URL or try another.")
        else:
            await update.message.reply_text("❌ Invalid YouTube link. Send a valid URL.")

    # Stream Key
    elif context.user_data.get('awaiting_key'):
        key = update.message.text.strip()
        if key:
            global STREAM_KEY
            STREAM_KEY = key
            context.user_data['awaiting_key'] = False
            await update.message.reply_text(f"✅ Stream Key set: {STREAM_KEY[:8]}...")
        else:
            await update.message.reply_text("❌ Invalid key. Send again.")

    else:
        await update.message.reply_text("Use /start to control the bot.")

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✅ Cancelled current operation.")

# ================================================================
# MAIN
# ================================================================

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise SystemExit("❌ Set your BOT_TOKEN in the script.")

    # Check if yt-dlp is installed
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except:
        print("⚠️ yt-dlp not found. Installing...")
        subprocess.run(["pip", "install", "yt-dlp"])

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    print("🔥 STARK YouTube Loop Stream Bot started. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()