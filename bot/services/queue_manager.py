import asyncio
import logging
import os
import json
import shutil
import signal
from bot.config.config import Config

logger = logging.getLogger(__name__)

class QueueManager:
    def __init__(self, bot):
        self.bot = bot
        self.download_queue = asyncio.Queue()
        self.compression_queue = asyncio.Queue()
        
        self.current_task = None
        self.current_process = None # To store the FFmpeg process object
        self.is_paused = False
        
        self.settings_file = "user_settings.json" 
        self.user_settings = self._load_settings()

    def start_worker(self):
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
        # We will check priority during the download_worker/compression_worker logic
        if self.download_queue.qsize() + self.compression_queue.qsize() >= Config.MAX_QUEUE_SIZE:
            return False, "Queue is full"
        await self.download_queue.put(task)
        return True, self.download_queue.qsize() + self.compression_queue.qsize()

    async def download_worker(self):
        while True:
            task = await self.download_queue.get()
            try:
                await self.process_download(task)
                await self.compression_queue.put(task)
            except Exception as e:
                logger.error(f"Error in download worker: {e}")
                self.cleanup_task(task)
            finally:
                self.download_queue.task_done()

    async def compression_worker(self):
        while True:
            # Check for priority tasks (Short videos <= 5 min)
            # We look ahead in the compression queue
            task = await self._get_next_best_task()
            
            self.current_task = task
            try:
                await self.process_compression(self.current_task)
            except Exception as e:
                logger.error(f"Error in compression worker: {e}")
            finally:
                self.compression_queue.task_done()
                self.cleanup_task(self.current_task)
                self.current_task = None
                self.current_process = None

    async def _get_next_best_task(self):
        """Custom priority logic: Get first available short video if current is not busy, 
        or wait for next."""
        # Simple implementation: just take the next one. 
        # The 'Pause' logic will be triggered by handle_video when a short video arrives.
        return await self.compression_queue.get()

    async def check_and_pause_for_priority(self, new_task_duration):
        """Called by media_handler when a new video is added.
        If current task is > 20min and new task is <= 5min, we pause current."""
        if not self.current_task or not self.current_process:
            return
            
        curr_duration = self.current_task.get('duration', 0)
        
        if curr_duration > 1200 and new_task_duration <= 300: # > 20 min vs <= 5 min
            if not self.is_paused:
                logger.info(f"Pausing long task ({curr_duration}s) for short task ({new_task_duration}s)")
                try:
                    os.kill(self.current_process.pid, signal.SIGSTOP)
                    self.is_paused = True
                    await self.current_task['status_msg'].edit_text("⏸ **Paused:** Processing a shorter priority video first...")
                except Exception as e:
                    logger.error(f"Failed to pause process: {e}")

    def resume_if_paused(self):
        if self.is_paused and self.current_process:
            logger.info("Resuming paused long task...")
            try:
                os.kill(self.current_process.pid, signal.SIGCONT)
                self.is_paused = False
                # Status update happens in next progress bar tick
            except Exception as e:
                logger.error(f"Failed to resume process: {e}")

    async def process_download(self, task):
        pass

    async def process_compression(self, task):
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
            name = media.file_name or "Unknown Video"
            status = " (Paused)" if self.is_paused else ""
            return f"{name}{status}"
        return None
