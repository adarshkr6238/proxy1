import logging
import asyncio
import os
from aiohttp import web
from pyrogram import Client, filters, idle
from bot.config.config import Config
from bot.services.queue_manager import QueueManager
from bot.services.storage_service import setup_storage, cleanup_old_files
from bot.handlers.commands import start_cmd, help_cmd, settings_cmd, set_preset_cb, stats_cmd, queue_cmd
from bot.handlers.media_handler import handle_video, process_video_task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Health Check Server
async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check server started on port {port}")

class VideoBot(Client):
    def __init__(self):
        logger.info("Initializing bot...")
        super().__init__(
            "video_compression_bot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            workers=4
        )
        self.queue_manager = QueueManager(self)
        self.queue_manager.process_task = self._process_task_bridge

    async def _process_task_bridge(self, task):
        await process_video_task(self, task, self.queue_manager)

    async def start(self):
        await super().start()
        setup_storage()
        # Start health check server
        asyncio.create_task(start_health_server())
        # Start periodic cleanup
        asyncio.create_task(self._cleanup_loop())
        logger.info("Bot started successfully!")

    async def _cleanup_loop(self):
        while True:
            import gc
            cleanup_old_files()
            gc.collect() 
            await asyncio.sleep(600) 

bot = VideoBot()

# Manual Registration to pass queue_manager
@bot.on_message(filters.command("start") & filters.private)
async def _start(c, m): await start_cmd(c, m)

@bot.on_message(filters.command("help") & filters.private)
async def _help(c, m): await help_cmd(c, m)

@bot.on_message(filters.command("settings") & filters.private)
async def _settings(c, m): await settings_cmd(c, m, bot.queue_manager)

@bot.on_callback_query(filters.regex("^settings_main$"))
async def _settings_cb(c, cb):
    # Convert callback query to a pseudo-message to reuse settings_cmd logic
    # or just call it directly with cb.message
    await settings_cmd(c, cb.message, bot.queue_manager)
    await cb.answer()

@bot.on_callback_query(filters.regex("^set_"))
async def _set_preset(c, cb): await set_preset_cb(c, cb, bot.queue_manager)

@bot.on_message(filters.command("stats") & filters.private)
async def _stats(c, m): await stats_cmd(c, m)

@bot.on_message(filters.command("queue") & filters.private)
async def _queue(c, m): await queue_cmd(c, m, bot.queue_manager)

@bot.on_message((filters.video | filters.document) & filters.private)
async def _media(c, m): await handle_video(c, m, bot.queue_manager)

if __name__ == "__main__":
    bot.run()
