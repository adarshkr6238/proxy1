import os
import time
import shutil
import logging
from bot.config.config import Config

logger = logging.getLogger(__name__)

def setup_storage():
    for d in [Config.DOWNLOAD_DIR, Config.TEMP_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

def cleanup_old_files():
    now = time.time()
    # Cleanup /tmp older than 24h
    for d in [Config.DOWNLOAD_DIR, Config.TEMP_DIR]:
        for f in os.listdir(d):
            f_path = os.path.join(d, f)
            if os.stat(f_path).st_mtime < now - 86400:
                try:
                    if os.path.isfile(f_path):
                        os.remove(f_path)
                    else:
                        shutil.rmtree(f_path)
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")
