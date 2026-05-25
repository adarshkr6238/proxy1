import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
    
    # Authorized users (comma-separated string in env)
    AUTH_USERS = set(int(x) for x in os.getenv("AUTH_USERS", "").split(",") if x.strip())
    AUTH_USERS.add(OWNER_ID)
    
    # Storage settings
    DOWNLOAD_DIR = "/tmp/bot_downloads"
    TEMP_DIR = "/tmp/bot_temp"
    
    # FFmpeg presets (Higher CRF = Smaller file)
    # Aggressive values to ensure reduction
    PRESETS = {
        "low": {"crf": 30, "scale": -1, "desc": "Light compression"},
        "medium": {"crf": 34, "scale": 720, "desc": "Balanced compression"},
        "high": {"crf": 40, "scale": 480, "desc": "Maximum compression (Tiny file)"}
    }
    
    DEFAULT_PRESET = "medium"
    
    # Progress bar update frequency (seconds)
    PROGRESS_UPDATE_INTERVAL = 3
    
    # Queue settings
    MAX_QUEUE_SIZE = 20
