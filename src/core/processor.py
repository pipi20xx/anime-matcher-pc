import os
import sys
import time
import traceback
import asyncio

# 动态加载核心识别库
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORE_PATH = os.path.join(ROOT_DIR, "anime-matcher-main", "src")
if CORE_PATH not in sys.path:
    sys.path.append(CORE_PATH)

try:
    from anime_matcher.kernel import core_recognize
    from anime_matcher.data_models import MediaType
    from anime_matcher.special_episode_handler import SpecialEpisodeHandler
    from anime_matcher.providers.tmdb.client import TMDBProvider
    from anime_matcher.providers.bangumi.client import BangumiProvider
    # 注意：核心库内部可能有 storage 对象管理本地缓存
    from anime_matcher.storage_manager import storage 
    ALGO_AVAILABLE = True
except ImportError:
    print(f"Error: Could not import anime_matcher components from {CORE_PATH}")
    ALGO_AVAILABLE = False

from src.core.rules import RuleManager

class RecognitionResult:
    def __init__(self, data: dict, logs: list):
        self.logs = logs
        self._data = data
        for k, v in data.items(): setattr(self, k, v)
    def to_dict(self): return self._data

class RecognitionProcessor:
    def __init__(self, config_data=None):
        self.config = config_data or {}
        self.custom_words = self.config.get('custom_words', [])
        self.custom_groups = self.config.get('custom_groups', [])

    def recognize_file(self, filename_path: str) -> RecognitionResult:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._async_recognize(filename_path))
            loop.close()
            return result
        except Exception as e:
            return RecognitionResult({"title": "识别异常", "filename": os.path.basename(filename_path)}, [str(e)])

    async def _async_recognize(self, filename_path: str) -> RecognitionResult:
        start_time = time.time()
        logs = []
        filename = os.path.basename(filename_path)

        if not ALGO_AVAILABLE:
            return RecognitionResult({"title": "内核缺失"}, ["[ERROR] 请先下载核心算法"])

        try:
            # 1. 规则准备 (L1)
            db_noise = RuleManager.get_merged_rules('noise')
            db_groups = RuleManager.get_merged_rules('group')
            db_priv = RuleManager.get_merged_rules('privileged')
            
            if db_priv:
                SpecialEpisodeHandler.load_external_rules(db_priv)

            # 2. 本地内核解析
            meta = core_recognize(
                input_name=filename,
                custom_words=list(set(self.custom_words + db_noise)),
                custom_groups=list(set(self.custom_groups + db_groups)),
                original_input=filename,
                current_logs=logs,
                batch_enhancement=self.config.get('batch_enhancement', False),
                force_filename=True
            )

            # 3. 构造基础结论
            final_dict = {
                "title": meta.cn_name or meta.en_name or meta.processed_name or filename,
                "tmdb_id": str(meta.forced_tmdbid) if meta.forced_tmdbid else "",
                "category": "电影" if "movie" in str(meta.type).lower() else "剧集",
                "processed_name": meta.processed_name or "",
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
                "year": meta.year or "",
                "filename": filename,
                "path": filename_path
            }

            # 4. 云端联动 (L2 Cloud)
            cloud_data = None
            if self.config.get('with_cloud'):
                tmdb_key = self.config.get('tmdb_api_key')
                if tmdb_key:
                    logs.append("┃ [DEBUG] 启动云端对撞流...")
                    tmdb = TMDBProvider(api_key=tmdb_key, proxy=self.config.get('tmdb_proxy'))
                    m_type = "movie" if final_dict["category"] == "电影" else "tv"
                    
                    # 4.1 检查智能记忆 (如果启用)
                    if self.config.get('use_storage') and not final_dict["tmdb_id"]:
                        pattern_key = f"{meta.cn_name or meta.en_name}|{meta.year}"
                        memory = storage.get_memory(pattern_key)
                        if memory:
                            final_dict["tmdb_id"] = memory['tmdb_id']
                            logs.append(f"┃ [STORAGE] ⚡ 命中心特征记忆: 自动锁定 ID {final_dict['tmdb_id']}")

                    # 4.2 执行搜索或获取详情
                    if final_dict["tmdb_id"]:
                        cloud_data = await tmdb.get_details(final_dict["tmdb_id"], m_type, logs)
                    else:
                        # 尝试通过搜索匹配
                        cloud_data = await tmdb.smart_search(
                            meta.cn_name, meta.en_name, meta.year, m_type, logs,
                            anime_priority=self.config.get('anime_priority', True)
                        )
                        
                        # 如果开启了 Bangumi 故障转移且 TMDB 失败
                        if not cloud_data and self.config.get('bgm_failover'):
                            logs.append("┃ [DEBUG] TMDB 检索失败，尝试 Bangumi 故障转移...")
                            bgm = BangumiProvider(token=self.config.get('bangumi_token'), proxy=self.config.get('bangumi_proxy'))
                            bgm_subject = await bgm.search_subject(meta.cn_name or meta.en_name, logs)
                            if bgm_subject:
                                # 映射回 TMDB
                                cloud_data = await bgm.map_to_tmdb(bgm_subject, tmdb_api_key=tmdb_key, logs=logs, tmdb_proxy=self.config.get('tmdb_proxy'))

                    # 4.3 写入记忆
                    if self.config.get('use_storage') and cloud_data:
                        pattern_key = f"{meta.cn_name or meta.en_name}|{meta.year}"
                        storage.set_memory(pattern_key, str(cloud_data.get('id')), m_type, final_dict["season"])

            # 5. 更新最终字段
            if cloud_data:
                final_dict.update({
                    "title": cloud_data.get("title") or cloud_data.get("name") or final_dict["title"],
                    "tmdb_id": str(cloud_data.get("id", "")),
                    "year": (cloud_data.get("release_date") or cloud_data.get("first_air_date") or "")[:4] or final_dict["year"]
                })

            final_dict["duration"] = f"{time.time() - start_time:.2f}s"
            return RecognitionResult(final_dict, logs)

        except Exception as e:
            logs.append(f"[CRITICAL] {str(e)}\n{traceback.format_exc()}")
            return RecognitionResult({"title": "识别失败", "filename": filename}, logs)
