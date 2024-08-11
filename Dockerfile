FROM python:3.12

# 设置工作目录
WORKDIR /app

# 安装系统依赖库
RUN apt-get update \
    && apt-get install -y \
        libx11-xcb1 \
        libxrandr2 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libxfixes3 \
        libxi6 \
        libgtk-3-0 \
        libgdk-pixbuf2.0-0 \
        libatk1.0-0 \
        libasound2 \
        libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

# 复制应用代码
COPY . /app

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install firefox

# 设置工作目录
WORKDIR /app

# 启动应用
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

