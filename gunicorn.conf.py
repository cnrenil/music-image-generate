import os
import time
from threading import Thread
import eventlet

CACHE_DIR = os.path.join(os.getcwd(), 'cache')
CACHE_EXPIRATION = 3600  # 1小时
exit_flag = False

def ensure_cache_dir_exists(logger):
    if not os.path.exists(CACHE_DIR):
        try:
            os.makedirs(CACHE_DIR)
            logger.info(f"Created cache directory: {CACHE_DIR}")
        except Exception as e:
            logger.error(f"Error creating cache directory: {e}")
            raise

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
        eventlet.sleep(CACHE_EXPIRATION // 2)

def on_starting(server):
    ensure_cache_dir_exists(server.log)
    cleaner_thread = Thread(target=cache_cleaner, args=(server.log,), daemon=True)
    cleaner_thread.start()
    server.log.info("Started cache cleaner thread.")

bind = '0.0.0.0:3006' # 设置监听和端口
workers = 4 # 根据CPU数设置
worker_class = 'eventlet'
timeout = 120
accesslog = '-'
errorlog = '-'
loglevel = 'info'

