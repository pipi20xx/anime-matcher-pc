import os
import sys

def get_app_root():
    """获取程序运行的根目录 (EXE 所在目录或 main.py 所在目录)"""
    if getattr(sys, 'frozen', False):
        # 打包后的环境，sys.executable 是 EXE 的完整路径
        return os.path.dirname(sys.executable)
    # 开发环境，使用入口文件 main.py 的路径
    # 注意：这里假设 main.py 在根目录运行
    return os.path.dirname(os.path.abspath(sys.argv[0]))

def get_resource_path(relative_path):
    """获取内置只读资源路径 (针对 PyInstaller 内部资源)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 运行时会将 --add-data 的文件解压到这个临时目录
        base_path = getattr(sys, '_MEIPASS', get_app_root())
        return os.path.normpath(os.path.join(base_path, relative_path))
    return os.path.normpath(os.path.join(get_app_root(), relative_path))

# 预定义常用路径
APP_ROOT = get_app_root()
DATA_DIR = os.path.join(APP_ROOT, "data")
CONFIG_INI = os.path.join(APP_ROOT, "VideoRenamer_Qt6.ini")
DB_PATH = os.path.join(APP_ROOT, "VideoRenamer.db")
CORE_ALGO_DIR = os.path.join(APP_ROOT, "anime-matcher-main")
PLACEHOLDERS_JSON = get_resource_path("src/utils/placeholders.json")
CORE_DB_PATH = os.path.join(DATA_DIR, "matcher_storage.db")
