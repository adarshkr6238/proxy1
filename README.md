# Telegram Video Compression Bot

Production-ready Telegram bot optimized for Render (512MB RAM) using MTProto for large files.

## Features
- **MTProto Support:** Handle files >2GB (no Bot API limits).
- **Sequential Queue:** Processes one video at a time to stay under 512MB RAM.
- **FFmpeg Powered:** H.264/AAC encoding with CRF-based quality.
- **Private:** Only approved users can use it.
- **Progress Tracking:** Real-time download/compress/upload bars.

## Deployment on Render

1. **Fork/Clone** this repository to your GitHub.
2. Create a new **Blueprint Instance** on Render.
3. Select your repository.
4. Set the following **Environment Variables**:
   - `API_ID`: From [my.telegram.org](https://my.telegram.org)
   - `API_HASH`: From [my.telegram.org](https://my.telegram.org)
   - `BOT_TOKEN`: From [@BotFather](https://t.me/BotFather)
   - `OWNER_ID`: Your Telegram User ID.
5. Deploy!

## Commands
- `/start` - Start the bot.
- `/help` - Show help and presets.
- `/settings` - Change compression level.
- `/queue` - Check waiting tasks.
- `/stats` - See system usage.

## Technical Details
- **RAM Optimization:** Uses `veryfast` FFmpeg preset and limited concurrency.
- **Storage:** Uses `/tmp` for processing, automatically cleaned up.
- **Async:** Built on `Pyrogram` for non-blocking I/O.
