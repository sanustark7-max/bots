#!/usr/bin/env python3
# YouTube Live Stream Bot - UPDATED v2.0
# Fixed: FFmpeg, Re-encode, Reconnection, Auto-monitor

import os
import subprocess
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import shutil

# ============ CONFIG ============
API_ID = 39322312  # my.telegram.org se lo
API_HASH = "8c7394157f601e78d46620de5fb22a2c"
BOT_TOKEN = "8450973856:AAG-BXSiayrOxInFYLIgkbOkCAGeH1M7IIM"
ALLOWED_USERS = [5969149339]  # Apna Telegram User ID

DOWNLOAD_PATH = "/root/videos"
STREAM_VIDEO_NAME = "stream_video.mp4"

# ============ STATE ============
class StreamState:
    def __init__(self):
        self.stream_key = None
        self.video_path = None
        self.reencoded_path = None
        self.is_streaming = False
        self.process = None
        self.monitor_task = None

state = StreamState()

# ============ CREATE FOLDERS ============
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# ============ PYROGRAM CLIENT ============
app = Client("live_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ============ HELPERS ============
async def monitor_stream(status_msg):
    """Monitor stream process and notify if it stops"""
    while state.is_streaming:
        await asyncio.sleep(15)
        if state.process and state.process.poll() is not None:
            state.is_streaming = False
            try:
                await status_msg.edit_text(
                    f"⚠️ **Stream stopped unexpectedly!**\n"
                    f"Use `/startstream` to restart.\n\n"
                    f"Check YouTube Studio for error details."
                )
            except:
                pass
            break

def reencode_video(input_path, output_path):
    """Re-encode video to H.264 + AAC for YouTube compatibility"""
    try:
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-y",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Re-encode error: {e.stderr}")
        return False

# ============ COMMANDS ============

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        await message.reply_text("⛔ Unauthorized access!")
        return
    
    await message.reply_text(
        "🎬 **YouTube Live Stream Bot v2.0**\n\n"
        "📤 **Send any MP4 video file** to upload.\n"
        "⏳ File will download via MTProto (2GB+ supported).\n"
        "🔑 Use `/setkey YOUR_STREAM_KEY` to set stream key.\n"
        "▶️ Use `/startstream` to start looping stream.\n"
        "⏹️ Use `/stopstream` to stop stream.\n"
        "📊 Use `/status` to check current status.\n\n"
        "⚠️ Video will be re-encoded for YouTube compatibility.",
        parse_mode=ParseMode.MARKDOWN
    )

@app.on_message(filters.video & filters.private)
async def handle_video(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        await message.reply_text("⛔ Unauthorized!")
        return
    
    video = message.video
    if not video:
        await message.reply_text("❌ Please send an MP4 video file.")
        return
    
    if video.file_size > 4 * 1024 * 1024 * 1024:
        await message.reply_text("❌ File too large! Max 4GB.")
        return
    
    status_msg = await message.reply_text("📥 **Downloading video...**\n⏳ This may take a while.")
    
    try:
        file_path = os.path.join(DOWNLOAD_PATH, STREAM_VIDEO_NAME)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        last_percent = 0
        
        def progress(current, total):
            nonlocal last_percent
            percent = int(current * 100 / total)
            if percent % 10 == 0 and percent != last_percent:
                last_percent = percent
                asyncio.create_task(
                    status_msg.edit_text(
                        f"📥 **Downloading video...**\n"
                        f"⏳ Progress: **{percent}%**"
                    )
                )
        
        downloaded_path = await client.download_media(
            message,
            file_name=file_path,
            progress=progress
        )
        
        if not downloaded_path or not os.path.exists(downloaded_path):
            raise Exception("File not found after download")
        
        state.video_path = downloaded_path
        
        await status_msg.edit_text(
            f"✅ **Video downloaded successfully!**\n\n"
            f"📁 Size: {video.file_size / (1024*1024):.2f} MB\n"
            f"⏱️ Duration: {video.duration} seconds\n\n"
            f"Now set your stream key with:\n"
            f"`/setkey YOUR_STREAM_KEY`\n\n"
            f"Then start stream with:\n"
            f"`/startstream`"
        )
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error downloading video:**\n`{e}`")

@app.on_message(filters.command("setkey"))
async def set_key_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply_text("❌ Usage: `/setkey YOUR_STREAM_KEY`")
        return
    
    state.stream_key = parts[1]
    await message.reply_text(
        f"✅ **Stream key set successfully!**\n"
        f"🔑 Key: `{state.stream_key}`\n\n"
        f"Now use `/startstream` to begin streaming."
    )

@app.on_message(filters.command("startstream"))
async def start_stream_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        return
    
    if not state.video_path or not os.path.exists(state.video_path):
        await message.reply_text("❌ No video found! Please send an MP4 video first.")
        return
    
    if not state.stream_key:
        await message.reply_text("❌ Stream key not set! Use `/setkey YOUR_STREAM_KEY`")
        return
    
    if state.is_streaming:
        await message.reply_text("⚠️ Stream is already running!")
        return
    
    status_msg = await message.reply_text("🎬 **Starting stream...**")
    
    try:
        # ============================================================
        # STEP 1: RE-ENCODE VIDEO (if not already done)
        # ============================================================
        reencoded_path = state.video_path.replace(".mp4", "_reencoded.mp4")
        
        if not os.path.exists(reencoded_path):
            await status_msg.edit_text("🔄 **Re-encoding video...** (1-2 minutes)")
            success = reencode_video(state.video_path, reencoded_path)
            if not success:
                await status_msg.edit_text("❌ **Failed to re-encode video!**\nCheck FFmpeg installation.")
                return
        
        state.reencoded_path = reencoded_path
        
        # ============================================================
        # STEP 2: STREAM WITH RECONNECTION FLAGS
        # ============================================================
        cmd = [
            "ffmpeg",
            "-re",
            "-stream_loop", "-1",
            "-i", reencoded_path,
            "-c", "copy",
            "-f", "flv",
            "-rtmp_live", "live",
            "-rtmp_buffer", "1000",
            "-timeout", "30000000",
            "-reconnect", "1",
            "-reconnect_at_eof", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-max_muxing_queue_size", "9999",
            f"rtmp://a.rtmp.youtube.com/live2/{state.stream_key}"
        ]
        
        state.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        state.is_streaming = True
        
        # Start monitor task
        if state.monitor_task:
            state.monitor_task.cancel()
        state.monitor_task = asyncio.create_task(monitor_stream(status_msg))
        
        await status_msg.edit_text(
            f"✅ **Stream started successfully!**\n\n"
            f"🔑 Key: `{state.stream_key}`\n"
            f"🔄 Video looping (re-encoded)\n"
            f"⏹️ Use `/stopstream` to stop.\n\n"
            f"⚠️ Stream will auto-reconnect if disconnected."
        )
        
    except Exception as e:
        state.is_streaming = False
        await status_msg.edit_text(f"❌ **Failed to start stream:**\n`{e}`")

@app.on_message(filters.command("stopstream"))
async def stop_stream_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        return
    
    if not state.is_streaming:
        await message.reply_text("⚠️ No stream is currently running!")
        return
    
    try:
        if state.process:
            state.process.terminate()
            try:
                state.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                state.process.kill()
        
        state.is_streaming = False
        
        if state.monitor_task:
            state.monitor_task.cancel()
            state.monitor_task = None
        
        await message.reply_text("⏹️ **Stream stopped successfully!**")
        
    except Exception as e:
        await message.reply_text(f"❌ **Error stopping stream:**\n`{e}`")

@app.on_message(filters.command("status"))
async def status_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        return
    
    video_exists = state.video_path and os.path.exists(state.video_path)
    video_size = "N/A"
    if video_exists:
        size_bytes = os.path.getsize(state.video_path)
        video_size = f"{size_bytes / (1024*1024):.2f} MB"
    
    reencoded_exists = state.reencoded_path and os.path.exists(state.reencoded_path)
    
    await message.reply_text(
        f"📊 **Stream Status**\n\n"
        f"🔑 Stream Key: `{state.stream_key or 'Not set'}`\n"
        f"📹 Video: `{state.video_path or 'No video'}`\n"
        f"📏 Size: `{video_size}`\n"
        f"🔄 Re-encoded: `{'✅' if reencoded_exists else '❌'}`\n"
        f"🔄 Streaming: `{'✅ Active' if state.is_streaming else '❌ Stopped'}`\n",
        parse_mode=ParseMode.MARKDOWN
    )

@app.on_message(filters.command("help"))
async def help_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ALLOWED_USERS:
        return
    
    await message.reply_text(
        "📖 **Commands:**\n\n"
        "📤 **Send MP4 video** — Upload video file\n"
        "🔑 `/setkey KEY` — Set YouTube stream key\n"
        "▶️ `/startstream` — Start looping stream\n"
        "⏹️ `/stopstream` — Stop stream\n"
        "📊 `/status` — Check current status\n"
        "📖 `/help` — Show this help\n\n"
        "⚡ **Stream will auto-reconnect if disconnected.**"
    )

# ============ MAIN ============
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 YouTube Live Stream Bot v2.0")
    print("📤 MTProto download (2GB+ support)")
    print("🔄 Auto-reconnect enabled")
    print("=" * 50)
    app.run()