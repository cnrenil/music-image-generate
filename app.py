import os
import base64
import hashlib
import re
import logging
import time
from threading import Thread, Event
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright
from typing import Optional
import httpx

# 配置 FastAPI 应用
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行的逻辑
    cache_cleaner = CacheCleaner(CACHE_DIR, CACHE_EXPIRATION)
    app.state.cache_cleaner = cache_cleaner
    yield
    # 关闭时执行的逻辑
    cache_cleaner.stop()

app = FastAPI(lifespan=lifespan)

# 配置日志
logger = logging.getLogger('uvicorn')
logger.setLevel(logging.DEBUG)

CACHE_DIR = os.path.join(os.getcwd(), 'cache')
CACHE_EXPIRATION = 3600  # 默认1小时

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
                        logger.info(f"删除过期缓存文件: {filename}")
                    except Exception as e:
                        logger.error(f"删除文件 {filename} 时出错: {e}")
            logger.debug(f"检查完成，检查时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}")
            self.stop_event.wait(self.expiration // 2)

    def stop(self):
        self.stop_event.set()
        self.thread.join()
        logger.info("缓存清理线程已停止。")

@app.get("/")
async def generate_image_endpoint(
    cover: str = 'cover.jpg',  # 封面图像的 URL
    title: str = 'Sample Song',  # 标题
    artist: str = 'Sample Artist',  # 艺术家
    lyrics: Optional[str] = None  # 歌词内容
):
    # 检查缓存
    hash_input = f"{cover}_{title}_{artist}_{lyrics}".encode('utf-8')
    cache_filename = hashlib.md5(hash_input).hexdigest()
    output_path = os.path.join(CACHE_DIR, f"screenshot_{cache_filename}.png")

    if os.path.exists(output_path):
        logger.info(f"提供缓存中的图像: {output_path}")
        return StreamingResponse(open(output_path, "rb"), media_type="image/png")

    # 处理歌词内容
    if lyrics:
        lyrics_content = await fetch_lyrics(lyrics)
    else:
        lyrics_content = 'Line 1 of the lyrics<br>Line 2 of the lyrics<br>Line 3 of the lyrics'
    logger.debug("歌词处理完成")

    # 下载封面图像并转换为 Base64 编码
    cover_base64 = await download_cover_image_as_base64(cover)
    if cover_base64 is None:
        logger.error("封面图像下载失败")
        return "封面图像下载失败", 500

    # 设置字体路径
    font_path = os.path.join(os.getcwd(), 'fonts/HanYiWenHei/HYWenHei-65W-3.ttf')

    # 生成图片并检查结果
    start_time = time.time()
    success = await generate_image(cover_base64, title, artist, lyrics_content, font_path, output_path)
    elapsed_time = time.time() - start_time
    logger.debug(f"图像生成耗时 {elapsed_time:.2f} 秒")

    if success:
        logger.info(f"图像生成并缓存: {output_path}")
        return StreamingResponse(open(output_path, "rb"), media_type="image/png")
    else:
        logger.error("图像生成失败")
        return "图像生成失败", 500

async def fetch_lyrics(lyrics_url: str, max_lines: int = 150) -> str:
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(lyrics_url)
            response.raise_for_status()
            response.encoding = 'utf-8'
            lyrics = response.text
            logger.debug("歌词内容成功获取并解码为UTF-8")
    except httpx.RequestError as e:
        logger.error(f"获取歌词时出错: {e}")
        return f"获取歌词时出错: {e}"

    # 处理特殊字符
    lyrics = lyrics.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    lyrics = re.sub(r'\[\d{2}:\d{2}\.\d{2,3}\]', '', lyrics)

    # 截断歌词行数
    lyrics_lines = lyrics.splitlines()
    if len(lyrics_lines) > max_lines:
        lyrics_lines = lyrics_lines[:max_lines]
        lyrics_lines.append('歌词太长，剩下的省略了...')
        logger.debug("歌词行数超过最大限制，已应用截断")

    return '<br>'.join(lyrics_lines)

async def download_cover_image_as_base64(cover_url: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(cover_url)
            response.raise_for_status()
            # 将图像转换为 Base64 编码
            cover_base64 = base64.b64encode(response.content).decode('utf-8')
            logger.debug("封面图像成功下载并转换为 Base64")
            return f"data:image/jpeg;base64,{cover_base64}"
    except httpx.RequestError as e:
        logger.error(f"下载封面图像时出错: {e}")
        return None

async def generate_image(cover_base64: str, title: str, artist: str, lyrics_content: str, font_path: str, output_path: str) -> bool:
    template_path = 'template.html'
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            template = file.read()
        logger.debug("模板文件成功读取")
    except Exception as e:
        logger.error(f"读取模板文件时出错: {e}")
        return False

    # 加载字体并编码
    with open(font_path, 'rb') as f:
        font_data = base64.b64encode(f.read()).decode('utf-8')

    # 替换模板中的占位符
    font_face = f"""
    <style>
    @font-face {{
        font-family: 'HanYiWenHei';
        src: url(data:font/ttf;base64,{font_data}) format('truetype');
    }}
    </style>"""
    placeholders = {
        "[Music::FONT_FACE]": font_face,
        "[Music::IMAGE]": cover_base64,  # 使用 Base64 编码的封面图像
        "[Music::TITLE]": title,
        "[Music::ARTIST]": artist,
        "[Music::LYRICS]": lyrics_content  # 使用处理后的歌词内容
    }

    for key, value in placeholders.items():
        template = template.replace(key, value)
    logger.debug("模板占位符已替换")

    # 使用 Playwright 生成图像
    async with async_playwright() as p:
        browser = await p.firefox.launch()
        page = await browser.new_page()
        await page.set_content(template)
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()
        logger.debug(f"图像成功生成并保存到: {output_path}")

    return True

