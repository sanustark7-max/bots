#!/usr/bin/env python3
"""
Telegram File Downloader Bot for RDP
Supports 2GB+ files via MTProto (Pyrogram)
"""

import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime

# ============================================
# 🔥 CONFIG - YAHAN APNA DATA DAALO
# ============================================
API_ID = 39322312  # my.telegram.org se lo
API_HASH = "8c7394157f601e78d46620de5fb22a2c"
BOT_TOKEN = "8450973856:AAG-BXSiayrOxInFYLIgkbOkCAGeH1M7IIM"  # @BotFather se lo
ALLOWED_USERS = [5969149339]  # Apna Telegram User ID

DOWNLOAD_PATH = "/root/Downloads"  # RDP ka download folder

# ============================================
# CREATE DOWNLOAD FOLDER
# ============================================
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# ============================================
# PYROGRAM CLIENT
# ============================================
app = Client("file_downloader", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ============================================
# COMMANDS
# ============================================

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        await message.reply_text("⛔ Unauthorized access!")
        return
    
    await message.reply_text(
        "📥 **File Downloader Bot**\n\n"
        "Send me any file (2GB+ supported)\n"
        "I will download it to RDP folder:\n"
        f"📁 `{DOWNLOAD_PATH}`\n\n"
        "Commands:\n"
        "/start - Show this\n"
        "/status - Check status\n"
        "/path - Show download path"
    )

@app.on_message(filters.command("status"))
async def status_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        return
    
    # Check disk space
    import shutil
    total, used, free = shutil.disk_usage(DOWNLOAD_PATH)
    
    await message.reply_text(
        f"📊 **Status**\n\n"
        f"📁 Download Path: `{DOWNLOAD_PATH}`\n"
        f"💾 Free Space: `{free // (2**30)} GB`\n"
        f"📦 Total Space: `{total // (2**30)} GB`"
    )

@app.on_message(filters.command("path"))
async def path_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        return
    
    await message.reply_text(f"📁 `{DOWNLOAD_PATH}`")

@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def handle_file(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        await message.reply_text("⛔ Unauthorized!")
        return
    
    # Check if it's a file
    if message.document:
        file = message.document
        file_name = file.file_name or f"file_{file.file_id[:8]}"
    elif message.video:
        file = message.video
        file_name = f"video_{file.file_id[:8]}.mp4"
    elif message.audio:
        file = message.audio
        file_name = f"audio_{file.file_id[:8]}.mp3"
    elif message.photo:
        file = message.photo[-1]
        file_name = f"photo_{file.file_id[:8]}.jpg"
    else:
        await message.reply_text("❌ Unsupported file type!")
        return
    
    # Check file size (4GB limit)
    if file.file_size > 4 * 1024 * 1024 * 1024:
        await message.reply_text("❌ File too large! Max 4GB.")
        return
    
    status_msg = await message.reply_text(
        f"📥 **Downloading...**\n"
        f"📁 Name: `{file_name}`\n"
        f"📏 Size: `{file.file_size / (1024*1024):.2f} MB`\n"
        f"📂 Path: `{DOWNLOAD_PATH}`"
    )
    
    try:
        file_path = os.path.join(DOWNLOAD_PATH, file_name)
        
        # Delete if exists
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Progress callback
        last_percent = 0
        
        def progress(current, total):
            nonlocal last_percent
            percent = int(current * 100 / total)
            if percent % 10 == 0 and percent != last_percent:
                last_percent = percent
                asyncio.create_task(
                    status_msg.edit_text(
                        f"📥 **Downloading...**\n"
                        f"📁 Name: `{file_name}`\n"
                        f"⏳ Progress: `{percent}%`"
                    )
                )
        
        # ============================================
        # MTProto DOWNLOAD (2GB+ SUPPORT)
        # ============================================
        downloaded_path = await client.download_media(
            message,
            file_name=file_path,
            progress=progress
        )
        
        if downloaded_path and os.path.exists(downloaded_path):
            file_size = os.path.getsize(downloaded_path)
            await status_msg.edit_text(
                f"✅ **Download Complete!**\n\n"
                f"📁 Name: `{file_name}`\n"
                f"📏 Size: `{file_size / (1024*1024):.2f} MB`\n"
                f"📂 Path: `{downloaded_path}`\n\n"
                f"💡 File is ready to use!"
            )
        else:
            await status_msg.edit_text("❌ **Download failed!**")
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:**\n`{e}`")

# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("📥 Telegram File Downloader Bot")
    print(f"📁 Download Path: {DOWNLOAD_PATH}")
    print("📤 Send any file (2GB+ supported)")
    print("=" * 50)
    app.run()