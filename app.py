from flask import Flask, request, send_file
from playwright.sync_api import sync_playwright
import os
import base64
import requests
import hashlib
import re
import logging

app = Flask(__name__)

# 配置 Flask 日志以使用 Gunicorn 的日志
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

@app.before_request
def log_request_info():
    if app.logger.isEnabledFor(logging.DEBUG):
        app.logger.debug(f"Request args: {request.args}")

def fetch_lyrics(lyrics_url, max_lines=150):
    try:
        response = requests.get(lyrics_url)
        response.raise_for_status()
        response.encoding = 'utf-8'
        lyrics = response.text
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching lyrics: {e}")
        return f"Error fetching lyrics: {e}"

    lyrics = lyrics.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    lyrics = re.sub(r'\[\d{2}:\d{2}\.\d{2,3}\]', '', lyrics)

    lyrics_lines = lyrics.splitlines()
    if len(lyrics_lines) > max_lines:
        lyrics_lines = lyrics_lines[:max_lines]
        lyrics_lines.append('歌词太长了，剩下的省略了...')

    return '<br>'.join(lyrics_lines)

def generate_image(cover_url, title, artist, lyrics, font_path, output_path):
    template_path = 'template.html'
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            template = file.read()
    except Exception as e:
        app.logger.error(f"Error reading template file: {e}")
        return f"Error reading template file: {e}"

    with open(font_path, 'rb') as f:
        font_data = base64.b64encode(f.read()).decode('utf-8')

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

    with sync_playwright() as p:
        browser = p.firefox.launch()
        page = browser.new_page()
        page.set_content(template)
        page.screenshot(path=output_path, full_page=True)
        browser.close()

@app.route('/')
def generate_image_endpoint():
    cover_url = request.args.get('cover', 'cover.jpg')
    title = request.args.get('title', 'Sample Song')
    artist = request.args.get('artist', 'Sample Artist')
    lyrics_url = request.args.get('lyrics', '')

    if lyrics_url:
        lyrics = fetch_lyrics(lyrics_url)
    else:
        lyrics = 'Line 1 of the lyrics<br>Line 2 of the lyrics<br>Line 3 of the lyrics'

    cache_dir = os.path.join(os.getcwd(), 'cache')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)

    hash_input = f"{cover_url}_{title}_{artist}_{lyrics_url}".encode('utf-8')
    cache_filename = hashlib.md5(hash_input).hexdigest()
    output_path = os.path.join(cache_dir, f"screenshot_{cache_filename}.png")

    if os.path.exists(output_path):
        app.logger.info(f"Serving cached image: {output_path}")
        return send_file(output_path, mimetype='image/png')

    font_path = os.path.join(os.getcwd(), 'fonts/HanYiWenHei/HYWenHei-65W-3.ttf')
    generate_image(cover_url, title, artist, lyrics, font_path, output_path)
    app.logger.info(f"Generated and cached image: {output_path}")
    return send_file(output_path, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)

