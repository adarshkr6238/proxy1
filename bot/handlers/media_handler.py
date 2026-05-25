import os
import time
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config.config import Config
from bot.utils.progress import progress_bar, format_bytes, is_cancelled, clear_cancel_flag
from bot.services.ffmpeg_service import compress_video
from bot.services.storage_service import setup_storage

logger = logging.getLogger(__name__)

async def handle_video(client, message, queue_manager):
    user_id = message.from_user.id
    if not message.video and not message.document:
        return

    if message.document:
        mime = message.document.mime_type or ""
        if not mime.startswith("video/"):
            return

    setup_storage()
    # Initial status message with cancel button
    status_msg = await message.reply_text(
        "⏳ Adding to queue...", 
        quote=True,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_init")]])
    )
    # Note: cancel_init will be handled differently or replaced once msg id is known
    
    task = {
        'message': message,
        'status_msg': status_msg,
        'user_id': user_id,
        'paths': [],
        'input_path': None
    }
    
    # Re-edit with correct msg id for callback
    await status_msg.edit_text(
        "⏳ Adding to queue...",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{status_msg.id}")]])
    )
    
    success, pos = await queue_manager.add_task(task)
    if not success:
        await status_msg.edit_text(f"❌ {pos}")
        return

    await status_msg.edit_text(
        f"📝 Added to queue (Position: {pos})\n\nVideos in queue are pre-downloaded to save time!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{status_msg.id}")]])
    )

async def download_stage(client, task):
    message = task['message']
    status_msg = task['status_msg']
    msg_id = status_msg.id
    
    if is_cancelled(msg_id):
        await status_msg.edit_text("❌ Task Cancelled.")
        return

    await status_msg.edit_text(
        "📥 Pre-downloading in background...",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{msg_id}")]])
    )
    start_time = time.time()
    last_update = start_time
    
    media = message.video or message.document
    file_ext = os.path.splitext(media.file_name or "video.mp4")[1]
    input_path = os.path.join(Config.DOWNLOAD_DIR, f"{message.id}{file_ext}")
    task['paths'].append(input_path)
    task['input_path'] = input_path

    async def down_progress(current, total):
        nonlocal last_update
        last_update = await progress_bar(current, total, "Downloading", status_msg, start_time, last_update)

    try:
        setup_storage()
        await message.download(file_name=input_path, progress=down_progress)
        if is_cancelled(msg_id):
            raise Exception("CANCELLED")
        await status_msg.edit_text(
            "✅ Downloaded! Waiting for compression slot...",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{msg_id}")]])
        )
    except Exception as e:
        if str(e) == "CANCELLED":
            await status_msg.edit_text("❌ Task Cancelled.")
        else:
            await status_msg.edit_text(f"❌ Download failed: {e}")
        raise e

async def compression_stage(client, task, queue_manager):
    message = task['message']
    status_msg = task['status_msg']
    user_id = task['user_id']
    input_path = task['input_path']
    msg_id = status_msg.id
    
    if is_cancelled(msg_id):
        await status_msg.edit_text("❌ Task Cancelled.")
        return

    # 2. Compress
    preset_name = queue_manager.get_user_preset(user_id)
    output_path = os.path.join(Config.TEMP_DIR, f"compressed_{message.id}.mp4")
    task['paths'].append(output_path)

    await status_msg.edit_text(
        f"⚙️ Compressing ({preset_name})...",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{msg_id}")]])
    )
    start_time = time.time()
    last_update = start_time

    async def comp_progress(current, total):
        nonlocal last_update
        last_update = await progress_bar(current, total, f"Compressing ({preset_name})", status_msg, start_time, last_update)

    try:
        # Check cancel inside compression loop happens via callback
        success, error_msg = await compress_video(input_path, output_path, preset_name, comp_progress)
        
        if is_cancelled(msg_id):
             raise Exception("CANCELLED")
             
        if not success:
            await status_msg.edit_text(f"❌ Compression failed:\n\n`{error_msg}`")
            return

        # 3. Upload
        await status_msg.edit_text(
            "📤 Uploading...",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{msg_id}")]])
        )
        start_time = time.time()
        last_update = start_time

        async def up_progress(current, total):
            nonlocal last_update
            last_update = await progress_bar(current, total, "Uploading", status_msg, start_time, last_update)

        orig_size = os.path.getsize(input_path)
        comp_size = os.path.getsize(output_path)
        
        if comp_size >= orig_size:
            await status_msg.edit_text("⚠️ Compressed file was larger. Sending original.")
            upload_path = input_path
            final_size = orig_size
            saved_str = "0% (Already optimized)"
        else:
            upload_path = output_path
            final_size = comp_size
            saved = (orig_size - comp_size) / orig_size * 100
            saved_str = f"{saved:.1f}%"

        caption = (
            f"✅ **Processing Complete**\n\n"
            f"📦 **Original:** {format_bytes(orig_size)}\n"
            f"📉 **Final:** {format_bytes(final_size)}\n"
            f"✨ **Saved:** {saved_str}\n"
            f"🛠️ **Preset:** {preset_name}"
        )

        await message.reply_video(
            video=upload_path,
            caption=caption,
            quote=True,
            progress=up_progress
        )
        await status_msg.delete()
        clear_cancel_flag(msg_id)
        import gc
        gc.collect() 
    except Exception as e:
        if str(e) == "CANCELLED":
            await status_msg.edit_text("❌ Task Cancelled.")
        else:
            await status_msg.edit_text(f"❌ Error: {e}")
        clear_cancel_flag(msg_id)
