import os
import time
import logging
from threading import Thread
import signal
import eventlet

# 设置缓存目录为当前工作目录下的 cache 文件夹
CACHE_DIR = os.path.join(os.getcwd(), 'cache')
CACHE_EXPIRATION = 3600  # 1小时
exit_flag = False

def cache_cleaner(logger):
    global exit_flag
    while not exit_flag:
        now = time.time()
        for filename in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, filename)
            if os.path.isfile(file_path) and (now - os.path.getmtime(file_path)) > CACHE_EXPIRATION:
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted expired cache file: {filename}")
                except Exception as e:
                    logger.error(f"Error deleting file {filename}: {e}")
        eventlet.sleep(CACHE_EXPIRATION // 2)  # 每半个 CACHE_EXPIRATION 的时间检查一次

def handle_exit(signum, frame):
    global exit_flag
    if exit_flag:
        return
    exit_flag = True
    logging.info(f"Signal handler called with signal {signum}")

def on_starting(server):
    # 启动缓存清理线程
    cleaner_thread = Thread(target=cache_cleaner, args=(server.log,), daemon=True)
    cleaner_thread.start()
    server.log.info("Started cache cleaner thread.")
    
    # 使用 Python 的原生信号模块设置信号处理程序
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

# Gunicorn 配置
bind = '0.0.0.0:3006'
workers = 4  # 根据服务器 CPU 核心数调整
worker_class = 'eventlet'  # 使用 eventlet 异步 worker
timeout = 120  # 增加超时时间
accesslog = '-'  # 将访问日志输出到控制台
errorlog = '-'   # 将错误日志输出到控制台
loglevel = 'info'  # 设置日志级别为 info

