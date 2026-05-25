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
    # Surgical cleanup: Wipe EVERYTHING in temp dirs to prevent any leaks
    for d in [Config.DOWNLOAD_DIR, Config.TEMP_DIR]:
        if not os.path.exists(d):
            continue
        for f in os.listdir(d):
            f_path = os.path.join(d, f)
            try:
                if os.path.isfile(f_path) or os.path.islink(f_path):
                    os.unlink(f_path)
                elif os.path.isdir(f_path):
                    shutil.rmtree(f_path)
            except Exception as e:
                logger.error(f"Cleanup error for {f_path}: {e}")
