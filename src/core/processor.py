import os
import sys
import time
import traceback

# 动态加载核心识别库
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORE_PATH = os.path.join(ROOT_DIR, "anime-matcher-main", "src")
if CORE_PATH not in sys.path:
    sys.path.append(CORE_PATH)

try:
    from anime_matcher.kernel import core_recognize
    from anime_matcher.data_models import MediaType
    from anime_matcher.special_episode_handler import SpecialEpisodeHandler
    ALGO_AVAILABLE = True
except ImportError:
    print(f"Error: Could not import anime_matcher core from {CORE_PATH}")
    ALGO_AVAILABLE = False

from src.core.rules import RuleManager

class RecognitionResult:
    """标准化的识别结果，与主项目 final_result 字段完全对齐"""
    def __init__(self, data: dict, logs: list):
        self.logs = logs
        self._data = data
        # 将字典转为对象属性
        for k, v in data.items():
            setattr(self, k, v)

    def to_dict(self):
        return self._data

class RecognitionProcessor:
    def __init__(self, custom_words=None, custom_groups=None):
        self.custom_words = custom_words or []
        self.custom_groups = custom_groups or []

    def recognize_file(self, filename_path: str) -> RecognitionResult:
        """调用本地内核进行深度识别并构建对标主项目的 final_result"""
        start_time = time.time()
        logs = []
        filename = os.path.basename(filename_path)

        if not ALGO_AVAILABLE:
            logs.append("[ERROR] 核心算法库未就绪。")
            return RecognitionResult({"title": "算法未就绪", "season": 1, "episode": "1"}, logs)
        
        try:
            # 1. 加载持久化规则
            db_noise = RuleManager.get_merged_rules('noise')
            db_groups = RuleManager.get_merged_rules('group')
            db_privileged = RuleManager.get_merged_rules('privileged')
            
            # 2. 注入特权规则
            if db_privileged:
                SpecialEpisodeHandler.load_external_rules(db_privileged)

            # 3. 合并参数并执行内核解析 (L1 Kernel)
            final_words = list(set(self.custom_words + db_noise))
            final_groups = list(set(self.custom_groups + db_groups))

            meta = core_recognize(
                input_name=filename,
                custom_words=final_words,
                custom_groups=final_groups,
                original_input=filename,
                current_logs=logs,
                batch_enhancement=False,
                force_filename=False
            )

            # 4. 构建对标 Docker 版的结论字典 (Final Mapping)
            m_type_zh = "电影" if "movie" in str(meta.type).lower() else "剧集"
            
            # 组装字段
            final_dict = {
                "title": meta.cn_name or meta.en_name or meta.processed_name or filename,
                "tmdb_id": str(meta.forced_tmdbid) if meta.forced_tmdbid else "",
                "category": m_type_zh,
                "processed_name": meta.processed_name or "",
                "poster_path": "", # 本地版暂无云端海报
                "release_date": "", # 本地版暂无上映日期
                "season": meta.begin_season if meta.begin_season is not None else 1,
                "episode": str(meta.begin_episode) if meta.begin_episode is not None else "1",
                "team": meta.resource_team or "",
                "resolution": meta.resource_pix or "",
                "video_encode": meta.video_encode or "",
                "video_effect": meta.video_effect or "",
                "audio_encode": meta.audio_encode or "",
                "subtitle": meta.subtitle_lang or "",
                "source": meta.resource_type or "",
                "platform": meta.resource_platform or "",
                "origin_country": "日本", # 核心默认为动漫识别
                "vote_average": 0.0,
                "year": meta.year or "",
                "duration": f"{time.time() - start_time:.2f}s",
                "filename": filename,
                "path": filename_path
            }

            return RecognitionResult(final_dict, logs)

        except Exception as e:
            logs.append(f"[ERROR] 核心识别崩溃: {str(e)}")
            logs.append(traceback.format_exc())
            # 返回空结果防止 UI 崩溃
            return RecognitionResult({"title": "识别失败", "filename": filename, "path": filename_path}, logs)
