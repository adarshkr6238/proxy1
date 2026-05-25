import os
import time
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config.config import Config
from bot.utils.progress import progress_bar, format_bytes
from bot.services.ffmpeg_service import compress_video
from bot.services.storage_service import setup_storage

logger = logging.getLogger(__name__)

async def handle_video(client, message, queue_manager):
    user_id = message.from_user.id
    if user_id not in Config.AUTH_USERS:
        return

    if not message.video and not message.document:
        return

    # Check file size/type if it's a document
    if message.document:
        mime = message.document.mime_type or ""
        if not mime.startswith("video/"):
            return

    # Ensure storage exists
    setup_storage()

    # Add to queue
    status_msg = await message.reply_text("⏳ Adding to queue...", quote=True)
    
    task = {
        'message': message,
        'status_msg': status_msg,
        'user_id': user_id,
        'paths': []
    }
    
    success, pos = await queue_manager.add_task(task)
    if not success:
        await status_msg.edit_text(f"❌ {pos}")
        return

    if pos > 0:
        await status_msg.edit_text(f"📝 Added to queue at position {pos}")
    else:
        await status_msg.edit_text("⚙️ Processing started...")

async def process_video_task(client, task, queue_manager):
    message = task['message']
    status_msg = task['status_msg']
    user_id = task['user_id']
    
    # 1. Download
    await status_msg.edit_text("📥 Downloading...")
    start_time = time.time()
    last_update = start_time
    
    media = message.video or message.document
    file_ext = os.path.splitext(media.file_name or "video.mp4")[1]
    input_path = os.path.join(Config.DOWNLOAD_DIR, f"{message.id}{file_ext}")
    task['paths'].append(input_path)

    async def down_progress(current, total):
        nonlocal last_update
        last_update = await progress_bar(current, total, "Downloading", status_msg, start_time, last_update)

    try:
        await message.download(file_name=input_path, progress=down_progress)
    except Exception as e:
        await status_msg.edit_text(f"❌ Download failed: {e}")
        return

    # 2. Compress
    preset_name = queue_manager.get_user_preset(user_id)
    preset_config = Config.PRESETS[preset_name]
    output_path = os.path.join(Config.TEMP_DIR, f"compressed_{message.id}.mp4")
    task['paths'].append(output_path)

    await status_msg.edit_text(f"⚙️ Compressing ({preset_name})...")
    start_time = time.time()
    last_update = start_time

    async def comp_progress(current, total):
        nonlocal last_update
        last_update = await progress_bar(current, total, f"Compressing ({preset_name})", status_msg, start_time, last_update)

    success = await compress_video(input_path, output_path, preset_config, comp_progress)
    if not success:
        await status_msg.edit_text("❌ Compression failed.")
        return

    # 3. Upload
    await status_msg.edit_text("📤 Uploading...")
    start_time = time.time()
    last_update = start_time

    async def up_progress(current, total):
        nonlocal last_update
        last_update = await progress_bar(current, total, "Uploading", status_msg, start_time, last_update)

    try:
        orig_size = os.path.getsize(input_path)
        comp_size = os.path.getsize(output_path)
        saved = (orig_size - comp_size) / orig_size * 100
        
        caption = (
            f"✅ **Compression Complete**\n\n"
            f"📦 **Original:** {format_bytes(orig_size)}\n"
            f"📉 **Compressed:** {format_bytes(comp_size)}\n"
            f"✨ **Saved:** {saved:.1f}%\n"
            f"🛠️ **Preset:** {preset_name}"
        )

        await message.reply_video(
            video=output_path,
            caption=caption,
            quote=True,
            progress=up_progress
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Upload failed: {e}")
