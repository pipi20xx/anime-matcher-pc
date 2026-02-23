import os
import sys
import time
import traceback
import asyncio
import importlib
from src.utils.paths import CORE_ALGO_DIR, APP_ROOT

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

    def _get_core_components(self, logs):
        core_src_path = os.path.normpath(os.path.join(CORE_ALGO_DIR, "src"))
        if not os.path.exists(core_src_path):
            logs.append(f"┃ [DEBUG] 找不到内核路径: {core_src_path}")
            return None
        if core_src_path not in sys.path:
            sys.path.insert(0, core_src_path)
            importlib.invalidate_caches()
        try:
            import regex
            from anime_matcher.kernel import core_recognize
            from anime_matcher.special_episode_handler import SpecialEpisodeHandler
            from anime_matcher.providers.tmdb.client import TMDBProvider
            from anime_matcher.providers.bangumi.client import BangumiProvider
            from anime_matcher.storage_manager import storage
            from anime_matcher.render_engine import RenderEngine
            return {
                "recognize": core_recognize,
                "sp_handler": SpecialEpisodeHandler,
                "tmdb": TMDBProvider,
                "bgm": BangumiProvider,
                "storage": storage,
                "render_engine": RenderEngine
            }
        except Exception as e:
            logs.append(f"┣ ❌ 内核加载失败: {str(e)}")
            return None

    def recognize_file(self, filename_path: str) -> RecognitionResult:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._async_recognize(filename_path))
            loop.close()
            return result
        except Exception as e:
            return RecognitionResult({"title": "异常"}, [f"[CRITICAL] {str(e)}"])

    async def _async_recognize(self, filename_path: str) -> RecognitionResult:
        start_time = time.time()
        logs = []
        original_filename = os.path.basename(filename_path)

        components = self._get_core_components(logs)
        if not components:
            return RecognitionResult({"title": "内核未就绪"}, logs)

        try:
            from src.core.rules import RuleManager
            # --- [STAGE 0] 规则加载审计 (严格对齐分类名) ---
            db_noise = RuleManager.get_merged_rules('noise')
            db_group = RuleManager.get_merged_rules('group')
            db_privileged = RuleManager.get_merged_rules('privileged')
            db_render = RuleManager.get_merged_rules('render')
            
            logs.append("┃ [DEBUG][规则审计]: 持久化规则提取完成")
            logs.append(f"┣ 🏷️ Noise (识别词): {len(db_noise)} 条")
            logs.append(f"┣ 🏷️ Group (制作组): {len(db_group)} 条")
            logs.append(f"┣ 🏷️ Privileged (特权): {len(db_privileged)} 条")
            logs.append(f"┣ 🏷️ Render (渲染词): {len(db_render)} 条")

            # --- [STAGE 1] 规则注入 ---
            if db_privileged:
                components["sp_handler"].load_external_rules(db_privileged)

            meta = components["recognize"](
                input_name=original_filename,
                custom_words=list(set(self.custom_words + db_noise)),
                custom_groups=list(set(self.custom_groups + db_group)),
                original_input=original_filename,
                current_logs=logs,
                batch_enhancement=self.config.get('batch_enhancement', False),
                force_filename=True
            )

            # 基础结论对齐 22 字段
            final_dict = {
                "title": meta.cn_name or meta.en_name or meta.processed_name or original_filename,
                "tmdb_id": str(meta.forced_tmdbid) if meta.forced_tmdbid else "",
                "category": "电影" if "movie" in str(meta.type).lower() else "剧集",
                "processed_name": meta.processed_name or "",
                "poster_path": "", "release_date": "",
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
                "origin_country": "日本", "vote_average": 0.0,
                "year": meta.year or "", "duration": "",
                "filename": original_filename, "path": filename_path
            }

            # L2 云端联动
            tmdb_client = None
            if self.config.get('with_cloud') and self.config.get('tmdb_api_key'):
                tmdb_client = components["tmdb"](api_key=self.config['tmdb_api_key'], proxy=self.config.get('tmdb_proxy'))
                m_type = "movie" if final_dict["category"] == "电影" else "tv"
                
                cloud_data = None
                if self.config.get('use_storage'):
                    memory = components["storage"].get_memory(f"{meta.cn_name or meta.en_name}|{meta.year}")
                    if memory: final_dict["tmdb_id"] = memory['tmdb_id']
                
                if final_dict["tmdb_id"]:
                    cloud_data = await tmdb_client.get_details(final_dict["tmdb_id"], m_type, logs)
                else:
                    cloud_data = await tmdb_client.smart_search(meta.cn_name, meta.en_name, meta.year, m_type, logs)
                
                if cloud_data:
                    final_dict.update({
                        "title": cloud_data.get("title") or cloud_data.get("name") or final_dict["title"],
                        "tmdb_id": str(cloud_data.get("id", "")),
                        "poster_path": cloud_data.get("poster_path", ""),
                        "release_date": cloud_data.get("release_date") or cloud_data.get("first_air_date") or "",
                        "vote_average": float(cloud_data.get("vote_average", 0.0)),
                        "origin_country": ", ".join(cloud_data.get("origin_country", [])) if isinstance(cloud_data.get("origin_country"), list) else ""
                    })
                    if not final_dict["year"] and final_dict["release_date"]:
                        final_dict["year"] = final_dict["release_date"][:4]

            # --- [STAGE 3] L3 专家渲染 ---
            if db_render:
                l1_info = {"cn_name": meta.cn_name, "en_name": meta.en_name, "season": meta.begin_season, "episode": meta.begin_episode}
                await components["render_engine"].apply_rules(final_result=final_dict, local_result=l1_info, raw_filename=original_filename, rules=db_render, logs=logs, tmdb_provider=tmdb_client)

            final_dict["duration"] = f"{time.time() - start_time:.2f}s"
            return RecognitionResult(final_dict, logs)

        except Exception as e:
            logs.append(f"[CRITICAL] {str(e)}\n{traceback.format_exc()}")
            return RecognitionResult({"title": "识别失败", "filename": original_filename}, logs)
