import os
import sys

def get_app_root():
    """获取程序运行的根目录 (EXE 所在目录或 main.py 所在目录)"""
    if getattr(sys, 'frozen', False):
        # 打包后的 EXE 环境
        path = os.path.dirname(os.path.abspath(sys.executable))
    else:
        # 开发环境下，相对于 main.py
        import __main__
        if hasattr(__main__, "__file__"):
            path = os.path.dirname(os.path.abspath(__main__.__file__))
        else:
            path = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.normpath(path)

def get_resource_path(relative_path):
    """获取内置只读资源路径"""
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS', get_app_root())
        return os.path.normpath(os.path.join(base_path, relative_path))
    return os.path.normpath(os.path.join(get_app_root(), relative_path))

# --- 定义所有核心路径变量 ---
APP_ROOT = get_app_root()
DATA_DIR = os.path.join(APP_ROOT, "data")
CONFIG_INI = os.path.join(APP_ROOT, "VideoRenamer_Qt6.ini")
DB_PATH = os.path.join(APP_ROOT, "VideoRenamer.db")
CORE_ALGO_DIR = os.path.join(APP_ROOT, "anime-matcher-main")
PLACEHOLDERS_JSON = get_resource_path("src/utils/placeholders.json")
CORE_DB_PATH = os.path.join(DATA_DIR, "matcher_storage.db")
