import os
import sys
import re
import traceback

# 动态加载核心识别库
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORE_PATH = os.path.join(ROOT_DIR, "anime-matcher-main", "src")
if CORE_PATH not in sys.path:
    sys.path.append(CORE_PATH)

try:
    from anime_matcher.kernel import core_recognize
    from anime_matcher.data_models import MediaType
    ALGO_AVAILABLE = True
except ImportError:
    print(f"Error: Could not import anime_matcher core from {CORE_PATH}")
    ALGO_AVAILABLE = False

class RecognitionResult:
    """标准化的识别结果，用于 UI 渲染"""
    def __init__(self, title, year, season, episode, tmdb_id, team, media_type, logs):
        self.title = title
        self.year = year
        self.season = season
        self.episode = episode
        self.tmdb_id = tmdb_id
        self.team = team
        self.media_type = media_type  # 'tv' or 'movie'
        self.logs = logs

class RecognitionProcessor:
    def __init__(self, custom_words=None, custom_groups=None):
        self.custom_words = custom_words or []
        self.custom_groups = custom_groups or []

    def recognize_file(self, filename: str) -> RecognitionResult:
        """调用本地核心进行文件识别"""
        logs = []
        if not ALGO_AVAILABLE:
            logs.append("[ERROR] 核心算法库未安装或未就绪。请前往“设置”下载核心算法。")
            return RecognitionResult("算法未就绪", "0000", "1", "1", "N/A", "N/A", "tv", logs)
        
        try:
            # 调用内核识别逻辑
            meta = core_recognize(
                input_name=filename,
                custom_words=self.custom_words,
                custom_groups=self.custom_groups,
                original_input=filename,
                current_logs=logs,
                batch_enhancement=False,
                force_filename=False
            )

            # 提取核心输出字段并映射到 UI 模型
            title = meta.cn_name or meta.en_name or "未知标题"
            year = meta.year or "0000"
            season = str(meta.begin_season) if meta.begin_season is not None else "1"
            episode = str(meta.begin_episode) if meta.begin_episode is not None else "1"
            tmdb_id = str(meta.forced_tmdbid) if meta.forced_tmdbid else "N/A"
            team = meta.resource_team or "N/A"
            
            # 媒体类型推断
            media_type = "tv"
            if hasattr(meta, 'type'):
                # 假设内核中 MediaType.MOVIE/TV 是枚举
                type_val = meta.type.value if hasattr(meta.type, 'value') else str(meta.type)
                if 'movie' in type_val.lower() or '电影' in type_val:
                    media_type = "movie"

            return RecognitionResult(title, year, season, episode, tmdb_id, team, media_type, logs)

        except Exception as e:
            logs.append(f"[ERROR] 核心识别崩溃: {str(e)}")
            logs.append(traceback.format_exc())
            return RecognitionResult("识别失败", "0000", "1", "1", "N/A", "N/A", "tv", logs)
