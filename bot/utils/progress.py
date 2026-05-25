import time
import math

async def progress_bar(current, total, status_text, message, start_time, last_update_time):
    now = time.time()
    if now - last_update_time < 3 and current != total:
        return last_update_time

    percentage = current * 100 / total
    speed = current / (now - start_time) if (now - start_time) > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    
    elapsed_time = format_time(now - start_time)
    eta_time = format_time(eta)

    bar_length = 10
    filled_length = int(round(bar_length * current / float(total)))
    bar = '█' * filled_length + '░' * (bar_length - filled_length)

    progress_str = (
        f"**{status_text}**\n"
        f"[{bar}] {percentage:.1f}%\n"
        f"🚀 Speed: {format_bytes(speed)}/s\n"
        f"⏳ ETA: {eta_time}\n"
        f"⏱️ Elapsed: {elapsed_time}"
    )

    try:
        await message.edit_text(progress_str)
    except Exception:
        pass
    
    return now

def format_bytes(size):
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

def format_time(seconds):
    if seconds < 0:
        return "00:00"
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"
