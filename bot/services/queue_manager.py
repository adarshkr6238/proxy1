import asyncio
import logging
import os
import shutil
from bot.config.config import Config

logger = logging.getLogger(__name__)

class QueueManager:
    def __init__(self, bot):
        self.bot = bot
        self.queue = asyncio.Queue()
        self.current_task = None
        self.is_running = False
        self.user_settings = {} # Simple in-memory settings (can be persistent later)

    async def add_task(self, task):
        if self.queue.qsize() >= Config.MAX_QUEUE_SIZE:
            return False, "Queue is full"
        await self.queue.put(task)
        if not self.is_running:
            asyncio.create_task(self.worker())
        return True, self.queue.qsize()

    async def worker(self):
        self.is_running = True
        while not self.queue.empty():
            self.current_task = await self.queue.get()
            try:
                await self.process_task(self.current_task)
            except Exception as e:
                logger.error(f"Error processing task: {e}")
            finally:
                self.queue.task_done()
                self.cleanup_task(self.current_task)
                self.current_task = None
        self.is_running = False

    async def process_task(self, task):
        # Implementation in handlers/media_handler logic
        # This manager will be passed to handlers
        pass

    def cleanup_task(self, task):
        # Basic cleanup
        paths = task.get('paths', [])
        for p in paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

    def get_user_preset(self, user_id):
        return self.user_settings.get(user_id, Config.DEFAULT_PRESET)

    def set_user_preset(self, user_id, preset):
        self.user_settings[user_id] = preset

    def get_queue_status(self):
        return self.queue.qsize()
