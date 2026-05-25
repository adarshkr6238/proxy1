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

async def compress_video(input_path, output_path, preset_name, progress_callback, queue_manager):
    # Get video info
    info = await get_video_info(input_path)
    if not info:
        return False, "Could not get video info with ffprobe."
        
    duration = float(info.get('format', {}).get('duration', 0))
    video_stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
    if not video_stream:
        return False, "No video stream found in file."
        
    width = int(video_stream.get('width', 0))
    height = int(video_stream.get('height', 0))
    
    # Parse framerate
    fps_str = video_stream.get('avg_frame_rate', '0/1')
    try:
        num, den = map(int, fps_str.split('/'))
        fps = num / den if den != 0 else 0
    except:
        fps = 0

    # Logic for target bitrate and resolution
    target_height = -2 
    v_bitrate = "500k"
    a_bitrate = "64k"
    
    if duration > 900: # > 15 minutes
        if preset_name == "low":
            target_height = 360
            v_bitrate = "300k"
        elif preset_name == "medium":
            target_height = 240
            v_bitrate = "200k"
        else: # high
            target_height = 144
            v_bitrate = "100k"
    else: # <= 15 minutes
        if preset_name == "low":
            if height > 720:
                target_height = 400
            elif height >= 480:
                target_height = 360
            v_bitrate = "500k"
        elif preset_name == "medium":
            target_height = 360
            v_bitrate = "350k"
        else: # high
            target_height = 240
            v_bitrate = "200k"

    # Base command optimized for Hugging Face
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-threads', '0', 
        '-c:v', 'libx264', '-preset', 'superfast'
    ]

    # Apply FPS cap if necessary
    if fps > 24:
        cmd.extend(['-r', '24'])

    # Add bitrate and other flags
    cmd.extend([
        '-b:v', v_bitrate,
        '-c:a', 'aac', '-b:a', a_bitrate, '-movflags', '+faststart'
    ])
    
    if target_height != -2:
        cmd.extend(['-vf', f"scale=-2:{target_height}"])
        
    cmd.append(output_path)
    
    process = await asyncio.create_subprocess_exec(
        *cmd, stderr=asyncio.subprocess.PIPE
    )
    
    # Store process in queue_manager for pausing
    queue_manager.current_process = process
    
    last_error_lines = []
    
    # FFmpeg writes progress to stderr
    while True:
        try:
            chunk = await process.stderr.read(1024)
            if not chunk:
                break
                
            line = chunk.decode('utf-8', errors='ignore')
            last_error_lines.append(line)
            if len(last_error_lines) > 20:
                last_error_lines.pop(0)

            if "time=" in line:
                try:
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
            if str(e) == "CANCELLED":
                # Ensure process is killed on cancellation
                try:
                    process.kill()
                except:
                    pass
                raise e
            logger.error(f"Error reading ffmpeg output: {e}")
            break
                
    await process.wait()
    queue_manager.current_process = None
    
    if process.returncode != 0:
        error_msg = "".join(last_error_lines).strip()
        return False, error_msg or f"FFmpeg exited with code {process.returncode}"
    
    return True, None
