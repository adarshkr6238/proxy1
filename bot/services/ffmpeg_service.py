import asyncio
import os
import subprocess
import json
import logging

logger = logging.getLogger(__name__)

async def get_video_info(file_path):
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json', 
        '-show_format', '-show_streams', file_path
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        return None
    return json.loads(stdout)

async def compress_video(input_path, output_path, preset_config, progress_callback):
    # Get video duration for progress calculation
    info = await get_video_info(input_path)
    if not info:
        return False
        
    duration = float(info.get('format', {}).get('duration', 0))
    
    crf = preset_config['crf']
    scale = preset_config['scale']
    
    # Base command optimized for low RAM
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-threads', '1', # Strict 1-thread to prevent RAM spikes
        '-c:v', 'libx264', '-preset', 'superfast', '-crf', str(crf),
        '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart'
    ]
    
    if scale != -1:
        cmd.extend(['-vf', f"scale=-2:{scale}"])
        
    cmd.append(output_path)
    
    process = await asyncio.create_subprocess_exec(
        *cmd, stderr=asyncio.subprocess.PIPE
    )
    
    # FFmpeg writes progress to stderr
    while True:
        # Read until \r or \n as FFmpeg uses \r for progress updates
        try:
            # We read chunk by chunk to avoid limit issues
            chunk = await process.stderr.read(1024)
            if not chunk:
                break
                
            line = chunk.decode('utf-8', errors='ignore')
            if "time=" in line:
                # Simple duration-based progress
                try:
                    # Look for time=00:00:00.00 pattern
                    import re
                    match = re.search(r"time=(\d+:\d+:\d+\.\d+)", line)
                    if match:
                        time_str = match.group(1)
                        h, m, s = time_str.split(":")
                        current_time = int(h)*3600 + int(m)*60 + float(s)
                        if duration > 0:
                            await progress_callback(current_time, duration)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error reading ffmpeg output: {e}")
            break
                
    await process.wait()
    return process.returncode == 0
