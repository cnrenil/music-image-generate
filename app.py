import os
import base64
import hashlib
import re
import logging
import time
from threading import Thread, Event
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from playwright.async_api import async_playwright
from typing import Optional
import httpx

# 配置 FastAPI 应用
app = FastAPI()

# 配置日志
logger = logging.getLogger('uvicorn')
logger.setLevel(logging.DEBUG)

CACHE_DIR = os.path.join(os.getcwd(), 'cache')
CACHE_EXPIRATION = 3600  # Default 1 hour

class CacheCleaner:
    def __init__(self, cache_dir: str, expiration: int):
        self.cache_dir = cache_dir
        self.expiration = expiration
        self.stop_event = Event()
        self.thread = Thread(target=self.clean_cache, daemon=True)
        self.thread.start()

    def clean_cache(self):
        while not self.stop_event.is_set():
            now = time.time()
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path) and (now - os.path.getmtime(file_path)) > self.expiration:
                    try:
                        os.remove(file_path)
                        logger.info(f"Deleted expired cache file: {filename}")
                    except Exception as e:
                        logger.error(f"Error deleting file {filename}: {e}")
            # Sleep a bit before next check
            self.stop_event.wait(self.expiration // 2)

    def stop(self):
        self.stop_event.set()
        self.thread.join()
        logger.info("Cache cleaner thread stopped.")

# 启动缓存清理器
cache_cleaner = CacheCleaner(CACHE_DIR, CACHE_EXPIRATION)

@app.on_event("shutdown")
async def shutdown_event():
    cache_cleaner.stop()

@app.get("/")
async def generate_image_endpoint(
    cover: str = 'cover.jpg',
    title: str = 'Sample Song',
    artist: str = 'Sample Artist',
    lyrics_url: Optional[str] = None
):
    # 检查缓存
    hash_input = f"{cover}_{title}_{artist}_{lyrics_url}".encode('utf-8')
    cache_filename = hashlib.md5(hash_input).hexdigest()
    output_path = os.path.join(CACHE_DIR, f"screenshot_{cache_filename}.png")

    if os.path.exists(output_path):
        logger.info(f"Providing image from cache: {output_path}")
        return StreamingResponse(open(output_path, "rb"), media_type="image/png")

    # 处理歌词
    if lyrics_url:
        lyrics = await fetch_lyrics(lyrics_url)
    else:
        lyrics = 'Line 1 of the lyrics<br>Line 2 of the lyrics<br>Line 3 of the lyrics'
    logger.debug("Lyrics processing complete")

    # 设置字体路径
    font_path = os.path.join(os.getcwd(), 'fonts/HanYiWenHei/HYWenHei-65W-3.ttf')

    # 生成图片并检查结果
    start_time = time.time()
    success = await generate_image(cover, title, artist, lyrics, font_path, output_path)
    elapsed_time = time.time() - start_time
    logger.debug(f"Image generation took {elapsed_time:.2f} seconds")

    if success:
        logger.info(f"Image generated and cached: {output_path}")
        return StreamingResponse(open(output_path, "rb"), media_type="image/png")
    else:
        logger.error("Image generation failed")
        return "Image generation failed", 500

async def fetch_lyrics(lyrics_url: str, max_lines: int = 150) -> str:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(lyrics_url)
            response.raise_for_status()
            response.encoding = 'utf-8'
            lyrics = response.text
            logger.debug("Lyrics content successfully fetched and decoded to UTF-8")
    except httpx.RequestError as e:
        logger.error(f"Error fetching lyrics: {e}")
        return f"Error fetching lyrics: {e}"

    # Process special characters
    lyrics = lyrics.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    lyrics = re.sub(r'\[\d{2}:\d{2}\.\d{2,3}\]', '', lyrics)

    # Truncate lyrics to max lines
    lyrics_lines = lyrics.splitlines()
    if len(lyrics_lines) > max_lines:
        lyrics_lines = lyrics_lines[:max_lines]
        lyrics_lines.append('Lyrics truncated...')
        logger.debug("Lyrics exceeded maximum line count, truncation applied")

    return '<br>'.join(lyrics_lines)

async def generate_image(cover_url: str, title: str, artist: str, lyrics: str, font_path: str, output_path: str) -> bool:
    template_path = 'template.html'
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            template = file.read()
        logger.debug("Template file successfully read")
    except Exception as e:
        logger.error(f"Error reading template file: {e}")
        return False

    # Load font and encode
    with open(font_path, 'rb') as f:
        font_data = base64.b64encode(f.read()).decode('utf-8')

    # Replace placeholders in template
    font_face = f"""
    <style>
    @font-face {{
        font-family: 'HanYiWenHei';
        src: url(data:font/ttf;base64,{font_data}) format('truetype');
    }}
    </style>"""
    placeholders = {
        "[Music::FONT_FACE]": font_face,
        "[Music::IMAGE]": cover_url,
        "[Music::TITLE]": title,
        "[Music::ARTIST]": artist,
        "[Music::LYRICS]": lyrics
    }

    for key, value in placeholders.items():
        template = template.replace(key, value)
    logger.debug("Template placeholders replaced")

    # Use Playwright to generate image
    async with async_playwright() as p:
        browser = await p.firefox.launch()
        page = await browser.new_page()
        await page.set_content(template)
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()
        logger.debug(f"Image successfully generated and saved to: {output_path}")

    return True

