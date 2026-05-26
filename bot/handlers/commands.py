from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config.config import Config

async def start_cmd(client, message: Message):
    await message.reply_text(
        "👋 **Welcome to Video Compression Bot!**\n\n"
        "Send me any video, and I'll compress it for you.\n"
        "Optimized for High-Performance Hosting.\n\n"
        "Use /help to see compression modes.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings_main")]
        ])
    )

async def help_cmd(client, message: Message):
    help_text = (
        "📖 **Help & Info**\n\n"
        "**Compression Modes:**\n"
        "• `low`: Highest quality, largest size\n"
        "• `medium`: Balanced (720p/360p target)\n"
        "• `high`: Smallest size, lower quality (480p/240p target)\n\n"
        "**Supported Formats:** MP4, MKV, MOV, WEBM\n"
        "**Max Size:** No strict limit (MTProto supported).\n"
        "**Queue:** Sequential processing to maintain stability.\n"
        "**Cleanup:** Files deleted immediately after processing."
    )
    await message.reply_text(help_text)

async def settings_cmd(client, message: Message, queue_manager):
    current = queue_manager.get_user_preset(message.from_user.id)
    await message.reply_text(
        f"⚙️ **Settings**\n\nCurrent Preset: **{current}**",
        reply_markup=get_settings_markup()
    )

def get_settings_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Low Compression", callback_data="set_low")],
        [InlineKeyboardButton("Medium Compression (Default)", callback_data="set_medium")],
        [InlineKeyboardButton("High Compression", callback_data="set_high")]
    ])

async def set_preset_cb(client, callback, queue_manager):
    preset = callback.data.split("_")[1]
    queue_manager.set_user_preset(callback.from_user.id, preset)
    await callback.answer(f"✅ Preset updated to {preset}")
    await callback.edit_message_text(
        f"⚙️ **Settings**\n\nCurrent Preset: **{preset}**",
        reply_markup=get_settings_markup()
    )

async def stats_cmd(client, message: Message, queue_manager=None):
    if message.from_user.id != Config.OWNER_ID:
        await message.reply_text("⛔ **Access Denied:** This command is for the owner only.")
        return

    import shutil
    import psutil
    
    # System Stats
    total, used, free = shutil.disk_usage("/")
    cpu_percent = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    
    # Queue Stats
    if queue_manager:
        dl_queue = queue_manager.download_queue.qsize()
        comp_queue = queue_manager.compression_queue.qsize()
        active_dl = queue_manager.active_download_count
        waiting_slot = queue_manager.waiting_for_slot_count
        paused_tasks = len(queue_manager.paused_compression_tasks)
        active_comp = "Yes" if queue_manager.active_compression_task else "No"
    else:
        dl_queue = comp_queue = active_dl = waiting_slot = paused_tasks = 0
        active_comp = "Unknown"

    status = (
        "📊 **Owner Dashboard**\n\n"
        "💻 **System Health:**\n"
        f"├ **CPU:** {cpu_percent}%\n"
        f"├ **RAM:** {ram.percent}% ({ram.used // (2**20)}MB / {ram.total // (2**20)}MB)\n"
        f"└ **Disk:** {used // (2**20)}MB used / {total // (2**20)}MB total\n\n"
        "⚙️ **Pipeline Status:**\n"
        f"├ **Active Downloads:** {active_dl}/3\n"
        f"├ **Waiting for DL Slot:** {waiting_slot}\n"
        f"├ **Active Compression:** {active_comp}\n"
        f"└ **Paused Compressions:** {paused_tasks}\n\n"
        "📝 **Queues:**\n"
        f"├ **Download Queue:** {dl_queue}\n"
        f"└ **Compression Queue:** {comp_queue}"
    )
    await message.reply_text(status)

async def queue_cmd(client, message: Message, queue_manager):
    count = queue_manager.get_queue_status()
    current = queue_manager.get_current_task_info()
    
    status = "📝 **Queue Status**\n\n"
    if current:
        status += f"⚙️ **Currently Processing:** `{current}`\n"
    else:
        status += "✅ **Queue is empty.**\n"
        
    if count > 0:
        status += f"⏳ **Tasks Waiting:** {count}"
    
    await message.reply_text(status)

async def clear_cmd(client, message: Message, queue_manager):
    if message.from_user.id != Config.OWNER_ID:
        await message.reply_text("⛔ **Access Denied:** This command is for the owner only.")
        return
        
    await message.reply_text("🧹 **Cleaning System:** Stopping all tasks and wiping storage...")
    await queue_manager.clear_queues()
    await message.reply_text("✅ **System Reset:** All queues emptied and files deleted.")
