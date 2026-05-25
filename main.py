import logging
import asyncio
import os
import signal
import uvloop # High performance event loop
from aiohttp import web
from pyrogram import Client, filters, idle
from bot.config.config import Config
from bot.services.queue_manager import QueueManager
from bot.services.storage_service import setup_storage, cleanup_old_files
from bot.handlers.commands import start_cmd, help_cmd, settings_cmd, set_preset_cb, stats_cmd, queue_cmd
from bot.handlers.media_handler import handle_video, download_stage, compression_stage
from bot.utils.progress import cancel_task

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
    port = int(os.environ.get("PORT", 7860))
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
            workers=2
        )
        self.queue_manager = QueueManager(self)
        self.queue_manager.process_download = self._download_bridge
        self.queue_manager.process_compression = self._compression_bridge

    async def _download_bridge(self, task):
        await download_stage(self, task)

    async def _compression_bridge(self, task):
        await compression_stage(self, task, self.queue_manager)

    async def start(self):
        await super().start()
        setup_storage()
        self.queue_manager.start_worker()
        asyncio.create_task(start_health_server())
        asyncio.create_task(self._cleanup_loop())
        logger.info("Bot started successfully!")

    async def _cleanup_loop(self):
        while True:
            import gc
            cleanup_old_files()
            gc.collect() 
            await asyncio.sleep(600) 

async def main():
    bot = VideoBot()

    # Define proper async wrappers for handlers that need queue_manager
    async def _settings_wrapper(c, m):
        await settings_cmd(c, m, bot.queue_manager)

    async def _settings_cb_wrapper(c, cb):
        await settings_cmd(c, cb.message, bot.queue_manager)
        await cb.answer()

    async def _set_preset_wrapper(c, cb):
        await set_preset_cb(c, cb, bot.queue_manager)

    async def _queue_wrapper(c, m):
        await queue_cmd(c, m, bot.queue_manager)

    async def _media_wrapper(c, m):
        await handle_video(c, m, bot.queue_manager)

    async def _cancel_cb_wrapper(c, cb):
        msg_id = int(cb.data.split("_")[1])
        cancel_task(msg_id)
        await cb.answer("Cancelling task...", show_alert=True)
        await cb.message.edit_text("❌ Cancellation requested. Moving to next task...")

    # Manual Registration with async wrappers
    bot.on_message(filters.command("start") & filters.private)(start_cmd)
    bot.on_message(filters.command("help") & filters.private)(help_cmd)
    bot.on_message(filters.command("settings") & filters.private)(_settings_wrapper)
    bot.on_callback_query(filters.regex("^settings_main$"))(_settings_cb_wrapper)
    bot.on_callback_query(filters.regex("^set_"))(_set_preset_wrapper)
    bot.on_callback_query(filters.regex("^cancel_"))(_cancel_cb_wrapper)
    bot.on_message(filters.command("stats") & filters.private)(stats_cmd)
    bot.on_message(filters.command("queue") & filters.private)(_queue_wrapper)
    bot.on_message((filters.video | filters.document) & filters.private)(_media_wrapper)

    await bot.start()
    await idle()
    await bot.stop()

if __name__ == "__main__":
    uvloop.install()
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}")
