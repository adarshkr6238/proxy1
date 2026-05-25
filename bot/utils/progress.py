import time
import math

_last_string = {}
_cancelled_tasks = set()

def cancel_task(msg_id):
    _cancelled_tasks.add(msg_id)

def is_cancelled(msg_id):
    return msg_id in _cancelled_tasks

def clear_cancel_flag(msg_id):
    if msg_id in _cancelled_tasks:
        _cancelled_tasks.remove(msg_id)

async def progress_bar(current, total, status_text, message, start_time, last_update_time):
    global _last_string
    msg_id = message.id

    if is_cancelled(msg_id):
        raise Exception("CANCELLED")

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

    if _last_string.get(msg_id) == progress_str and current != total:
        return now
    
    _last_string[msg_id] = progress_str

    try:
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await message.edit_text(
            progress_str,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{msg_id}")]])
        )
    except Exception:
        pass
    
    if current == total and msg_id in _last_string:
        del _last_string[msg_id]
        
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
