from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config.config import Config

@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    if message.from_user.id not in Config.AUTH_USERS:
        return
    await message.reply_text(
        "👋 **Welcome to Video Compression Bot!**\n\n"
        "Send me any video, and I'll compress it for you.\n"
        "Optimized for Render Free Instance.\n\n"
        "Use /help to see compression modes.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings_main")]
        ])
    )

@Client.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message: Message):
    if message.from_user.id not in Config.AUTH_USERS:
        return
    help_text = (
        "📖 **Help & Info**\n\n"
        "**Compression Modes:**\n"
        "• `low`: Highest quality, largest size (CRF 24)\n"
        "• `medium`: Balanced (CRF 28, 720p target)\n"
        "• `high`: Smallest size, lower quality (CRF 32, 480p target)\n\n"
        "**Supported Formats:** MP4, MKV, MOV, WEBM\n"
        "**Max Size:** No strict limit (MTProto supported), but Render storage is limited.\n"
        "**Queue:** Sequential processing to save RAM.\n"
        "**Cleanup:** Files deleted immediately after processing."
    )
    await message.reply_text(help_text)

@Client.on_message(filters.command("settings") & filters.private)
async def settings_cmd(client, message: Message, queue_manager):
    if message.from_user.id not in Config.AUTH_USERS:
        return
    current = queue_manager.get_user_preset(message.from_user.id)
    await message.reply_text(
        f"⚙️ **Settings**\n\nCurrent Preset: **{current}**",
        reply_markup=get_settings_markup()
    )

def get_settings_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Low Compression (Large)", callback_data="set_low")],
        [InlineKeyboardButton("Medium Compression (Default)", callback_data="set_medium")],
        [InlineKeyboardButton("High Compression (Small)", callback_data="set_high")]
    ])

@Client.on_callback_query(filters.regex("^set_"))
async def set_preset_cb(client, callback, queue_manager):
    preset = callback.data.split("_")[1]
    queue_manager.set_user_preset(callback.from_user.id, preset)
    await callback.answer(f"✅ Preset updated to {preset}")
    await callback.edit_message_text(
        f"⚙️ **Settings**\n\nCurrent Preset: **{preset}**",
        reply_markup=get_settings_markup()
    )

@Client.on_message(filters.command("stats") & filters.private)
async def stats_cmd(client, message: Message):
    if message.from_user.id not in Config.AUTH_USERS:
        return
    # Simple stats, can be expanded
    import shutil
    total, used, free = shutil.disk_usage("/")
    await message.reply_text(
        "📊 **System Stats**\n\n"
        f"💾 **Storage:** {used // (2**20)}MB used / {total // (2**20)}MB total\n"
        "🚀 **Mode:** Async MTProto\n"
        "📍 **Instance:** Render"
    )

@Client.on_message(filters.command("queue") & filters.private)
async def queue_cmd(client, message: Message, queue_manager):
    if message.from_user.id not in Config.AUTH_USERS:
        return
    count = queue_manager.get_queue_status()
    await message.reply_text(f"📝 **Queue Status**\n\nTasks waiting: {count}")
