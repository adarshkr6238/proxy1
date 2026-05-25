---
title: Telegram Video Compressor
emoji: 🎥
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# Telegram Video Compression Bot

Optimized for Hugging Face Spaces (16GB RAM) using MTProto for large files.

## Deployment on Hugging Face

1. **Create a New Space:** Go to [huggingface.co/new-space](https://huggingface.co/new-space).
2. **Name it:** e.g., `video-compressor`.
3. **SDK:** Select **Docker**.
4. **Template:** Blank.
5. **Private/Public:** Choose Private if you don't want others to see your logs.
6. **Settings -> Variables and Secrets:** Add the following **Secrets**:
   - `API_ID`: From [my.telegram.org](https://my.telegram.org)
   - `API_HASH`: From [my.telegram.org](https://my.telegram.org)
   - `BOT_TOKEN`: From [@BotFather](https://t.me/BotFather)
   - `OWNER_ID`: Your Telegram User ID.
7. **Upload Files:** Upload all files from this repo to the Space.

## Commands
- `/start` - Start the bot.
- `/help` - Show help and presets.
- `/settings` - Change compression level.
- `/queue` - Check waiting tasks.
- `/stats` - See system usage.
