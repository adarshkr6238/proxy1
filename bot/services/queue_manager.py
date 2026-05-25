import asyncio
import logging
import os
import json
import shutil
from bot.config.config import Config

logger = logging.getLogger(__name__)

class QueueManager:
    def __init__(self, bot):
        self.bot = bot
        # Two-stage queue
        self.download_queue = asyncio.Queue()
        self.compression_queue = asyncio.Queue()
        
        self.current_task = None # Current compression task
        self.settings_file = "user_settings.json" 
        self.user_settings = self._load_settings()

    def start_worker(self):
        # Start both workers
        asyncio.create_task(self.download_worker())
        asyncio.create_task(self.compression_worker())

    def _load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                    return {int(k): v for k, v in data.items()}
            except Exception as e:
                logger.error(f"Error loading settings: {e}")
        return {}

    def _save_settings(self):
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.user_settings, f)
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    async def add_task(self, task):
        if self.download_queue.qsize() + self.compression_queue.qsize() >= Config.MAX_QUEUE_SIZE:
            return False, "Queue is full"
        await self.download_queue.put(task)
        return True, self.download_queue.qsize() + self.compression_queue.qsize()

    async def download_worker(self):
        """Worker 1: Pre-downloads videos in background"""
        while True:
            task = await self.download_queue.get()
            try:
                # Signal to media_handler to start download
                await self.process_download(task)
                # Once downloaded, move to compression queue
                await self.compression_queue.put(task)
            except Exception as e:
                logger.error(f"Error in download worker: {e}")
                self.cleanup_task(task)
            finally:
                self.download_queue.task_done()

    async def compression_worker(self):
        """Worker 2: Compresses and uploads sequentially"""
        while True:
            self.current_task = await self.compression_queue.get()
            try:
                # Signal to media_handler to start compression/upload
                await self.process_compression(self.current_task)
            except Exception as e:
                logger.error(f"Error in compression worker: {e}")
            finally:
                self.compression_queue.task_done()
                self.cleanup_task(self.current_task)
                self.current_task = None

    async def process_download(self, task):
        # Implementation bridge
        pass

    async def process_compression(self, task):
        # Implementation bridge
        pass

    def cleanup_task(self, task):
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
        self._save_settings()

    def get_queue_status(self):
        return self.download_queue.qsize() + self.compression_queue.qsize()

    def get_current_task_info(self):
        if self.current_task:
            media = self.current_task['message'].video or self.current_task['message'].document
            return media.file_name or "Unknown Video"
        return None
