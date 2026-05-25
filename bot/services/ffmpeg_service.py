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
    
    # Base command
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', str(crf),
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
        line = await process.stderr.readline()
        if not line:
            break
            
        line = line.decode('utf-8')
        if "time=" in line:
            # Simple duration-based progress
            try:
                # Extract time=00:00:00.00
                time_str = line.split("time=")[1].split(" ")[0]
                h, m, s = time_str.split(":")
                current_time = int(h)*3600 + int(m)*60 + float(s)
                if duration > 0:
                    await progress_callback(current_time, duration)
            except Exception:
                pass
                
    await process.wait()
    return process.returncode == 0
