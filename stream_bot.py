#!/usr/bin/env python3
"""
STARK YOUTUBE LIVE STREAMER – TELEGRAM CONTROLLED
Owner: @Mrstark29 | Channel: @STARK
💀 DEVILS WILL RISE 💀
"""

import os
import subprocess
import threading
import time
import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ================================================================
# CONFIG – YAHAN APNA BOT TOKEN DAALO
# ================================================================
BOT_TOKEN = "6761072436:AAH9IcHQ015ohX99UivgI3ORrfwmDws4Bdg"  # @BotFather se lo
ALLOWED_USERS = [5969149339]  # Apna Telegram ID daalo (Sirf tum hi control kar sakoge)

# ================================================================
# STATE
# ================================================================
STREAM_PROCESS = None
STREAM_ACTIVE = False
CURRENT_VIDEO = None
STREAM_KEY = None
RTMP_URL = "rtmp://a.rtmp.youtube.com/live2"  # Default YouTube

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        [InlineKeyboardButton("▶️ Start Stream", callback_data="start")],
        [InlineKeyboardButton("⏹ Stop Stream", callback_data="stop")],
        [InlineKeyboardButton("📤 Upload Video", callback_data="upload")],
        [InlineKeyboardButton("🔑 Set Stream Key", callback_data="setkey")],
        [InlineKeyboardButton("📊 Status", callback_data="status")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎬 <b>STARK YouTube Stream Controller</b>\n\n"
        "Use buttons below to control the stream.\n"
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

    if data == "start":
        if not STREAM_KEY:
            await query.edit_message_text("❌ Stream Key not set. Use /setkey first.")
            return
        if not CURRENT_VIDEO:
            await query.edit_message_text("❌ No video uploaded. Use /upload to send a video file.")
            return
        success, msg = start_ffmpeg_stream(CURRENT_VIDEO, STREAM_KEY)
        await query.edit_message_text(f"{'✅' if success else '❌'} {msg}")

    elif data == "stop":
        success, msg = stop_stream()
        await query.edit_message_text(f"{'✅' if success else '❌'} {msg}")

    elif data == "upload":
        await query.edit_message_text("📤 Send a video file (MP4). I will save it as stream_video.mp4")
        context.user_data['awaiting_video'] = True

    elif data == "setkey":
        await query.edit_message_text("🔑 Send your YouTube Stream Key (found in YouTube Studio → Go Live → Stream Settings)")
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

    # Video upload
    if context.user_data.get('awaiting_video'):
        if update.message.document and update.message.document.mime_type.startswith('video/'):
            file = await update.message.document.get_file()
            file_path = "stream_video.mp4"
            await file.download_to_drive(file_path)
            global CURRENT_VIDEO
            CURRENT_VIDEO = file_path
            context.user_data['awaiting_video'] = False
            await update.message.reply_text(f"✅ Video saved as {file_path}\nUse /start to control stream.")
        else:
            await update.message.reply_text("❌ Please send a valid video file (MP4).")

    # Stream Key
    elif context.user_data.get('awaiting_key'):
        key = update.message.text.strip()
        if key:
            global STREAM_KEY
            STREAM_KEY = key
            context.user_data['awaiting_key'] = False
            await update.message.reply_text(f"✅ Stream Key set: {STREAM_KEY[:8]}...")
        else:
            await update.message.reply_text("❌ Invalid key. Send again or /cancel")

    else:
        await update.message.reply_text("Use /start to control the stream.")

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✅ Cancelled current operation.")

# ================================================================
# MAIN
# ================================================================

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise SystemExit("❌ Set your BOT_TOKEN in the script.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.VIDEO | filters.TEXT, handle_message))

    print("🔥 STARK Stream Bot started. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()