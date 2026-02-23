import os
import sys
import time
import traceback
import asyncio
import importlib
import json
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
                "recognize": core_recognize, "sp_handler": SpecialEpisodeHandler,
                "tmdb": TMDBProvider, "bgm": BangumiProvider,
                "storage": storage, "render_engine": RenderEngine
            }
        except Exception as e:
            logs.append(f"┣ ❌ 核心库加载失败: {str(e)}")
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

        logs.append(f"🚀 --- [ANIME 深度审计流启动] ---")
        
        def on_off(b): return "ON" if b else "OFF"
        logs.append(f"┃ [配置] 云端联动[{on_off(self.config.get('with_cloud'))}] | 智能记忆[{on_off(self.config.get('use_storage'))}] | 动漫优先[{on_off(self.config.get('anime_priority'))}]")

        components = self._get_core_components(logs)
        if not components:
            return RecognitionResult({"title": "内核未就绪"}, logs + ["┗ ❌ 内核缺失，请在设置中下载算法。"])

        try:
            from src.core.rules import RuleManager
            db_noise = RuleManager.get_merged_rules('noise')
            db_group = RuleManager.get_merged_rules('group')
            db_privileged = RuleManager.get_merged_rules('privileged')
            db_render = RuleManager.get_merged_rules('render')
            
            logs.append("┃ [审计] 正在载入 SQLite 持久化规则...")
            logs.append(f"┣ 🏷️ Noise (识别词): {len(db_noise)} 条")
            logs.append(f"┣ 🏷️ Group (制作组): {len(db_group)} 条")
            logs.append(f"┣ 🏷️ Privileged (特权): {len(db_privileged)} 条")
            logs.append(f"┣ 🏷️ Render (渲染词): {len(db_render)} 条")

            if db_privileged:
                components["sp_handler"].load_external_rules(db_privileged)

            logs.append("┃")
            meta = components["recognize"](
                input_name=original_filename,
                custom_words=list(set(self.custom_words + db_noise)),
                custom_groups=list(set(self.custom_groups + db_group)),
                original_input=original_filename,
                current_logs=logs,
                batch_enhancement=self.config.get('batch_enhancement', False),
                force_filename=True
            )

            custom_settings = self.config.get('custom_settings', {})
            ui_tmdb_id = custom_settings.get('tmdb_id_override')
            ui_media_type = custom_settings.get('media_type_override', 'tv')
            
            final_tmdb_id = ui_tmdb_id if ui_tmdb_id else (str(meta.forced_tmdbid) if meta.forced_tmdbid else "")
            m_type_zh = "电影" if (ui_media_type == "movie" or "movie" in str(meta.type).lower()) else "剧集"
            m_type_en = "movie" if m_type_zh == "电影" else "tv"

            final_dict = {
                "title": meta.cn_name or meta.en_name or meta.processed_name or original_filename,
                "tmdb_id": final_tmdb_id, "category": m_type_zh, "processed_name": meta.processed_name or "",
                "poster_path": "", "release_date": "",
                "season": meta.begin_season if meta.begin_season is not None else 1,
                "episode": str(meta.begin_episode) if meta.begin_episode is not None else "1",
                "team": meta.resource_team or "", "resolution": meta.resource_pix or "",
                "video_encode": meta.video_encode or "", "video_effect": meta.video_effect or "",
                "audio_encode": meta.audio_encode or "", "subtitle": meta.subtitle_lang or "",
                "source": meta.resource_type or "", "platform": meta.resource_platform or "",
                "origin_country": "日本", "vote_average": 0.0, "year": meta.year or "",
                "duration": "", "filename": original_filename, "path": filename_path
            }

            if self.config.get('with_cloud') and self.config.get('tmdb_api_key'):
                logs.append("┃")
                logs.append("┃ [联动] 正在启动云端元数据对撞流程...")
                tmdb_client = components["tmdb"](api_key=self.config['tmdb_api_key'], proxy=self.config.get('tmdb_proxy'))
                cloud_data = None
                
                if not final_dict["tmdb_id"] and self.config.get('use_storage'):
                    memory = components["storage"].get_memory(f"{meta.cn_name or meta.en_name}|{meta.year}")
                    if memory: 
                        final_dict["tmdb_id"] = memory['tmdb_id']
                        logs.append(f"┃ [记忆] ⚡ 命中心特征指纹，自动锁定 ID: {final_dict['tmdb_id']}")
                
                if final_dict["tmdb_id"]:
                    cloud_data = await tmdb_client.get_details(final_dict["tmdb_id"], m_type_en, logs)
                else:
                    cloud_data = await tmdb_client.smart_search(meta.cn_name, meta.en_name, meta.year, m_type_en, logs, anime_priority=self.config.get('anime_priority', True))
                    
                    if not cloud_data and self.config.get('bgm_failover'):
                        logs.append("┃ [救灾] TMDB 检索无结果，触发 Bangumi 故障转移...")
                        bgm = components["bgm"](token=self.config.get('bangumi_token'), proxy=self.config.get('bangumi_proxy'))
                        bgm_subject = await bgm.search_subject(meta.cn_name or meta.en_name, logs)
                        if bgm_subject:
                            cloud_data = await bgm.map_to_tmdb(bgm_subject, tmdb_api_key=self.config['tmdb_api_key'], logs=logs, tmdb_proxy=self.config.get('tmdb_proxy'))

                if cloud_data:
                    logs.append(f"┗ ✅ 云端对撞成功: {cloud_data.get('title') or cloud_data.get('name')} (ID: {cloud_data.get('id')})")
                    final_dict.update({
                        "title": cloud_data.get("title") or cloud_data.get("name") or final_dict["title"],
                        "tmdb_id": str(cloud_data.get("id", "")),
                        "poster_path": cloud_data.get("poster_path", ""),
                        "release_date": cloud_data.get("release_date") or cloud_data.get("first_air_date") or "",
                        "vote_average": float(cloud_data.get("vote_average", 0.0)),
                        "origin_country": ", ".join(cloud_data.get("origin_country", [])) if isinstance(cloud_data.get("origin_country"), list) else ""
                    })
                    if not final_dict["year"] and final_dict["release_date"]: final_dict["year"] = final_dict["release_date"][:4]
                    
                    if self.config.get('use_storage'):
                        components["storage"].set_memory(f"{meta.cn_name or meta.en_name}|{meta.year}", str(cloud_data.get('id')), m_type_en, final_dict["season"])
                else:
                    logs.append("┗ ❌ 云端对撞未发现高置信度匹配")

            if db_render:
                logs.append("┃")
                logs.append(f"┃ [渲染] 正在应用 {len(db_render)} 条专家规则进行 L3 修正...")
                l1_info = {"cn_name": meta.cn_name, "en_name": meta.en_name, "season": meta.begin_season, "episode": meta.begin_episode}
                await components["render_engine"].apply_rules(final_result=final_dict, local_result=l1_info, raw_filename=original_filename, rules=db_render, logs=logs, tmdb_provider=tmdb_client if 'tmdb_client' in locals() else None)
                logs.append(f"┗ ✅ 专家渲染流程结束")

            final_dict["duration"] = f"{time.time() - start_time:.2f}s"
            logs.append(f"🏁 --- [识别任务结束: {final_dict['duration']}] ---")
            
            # --- 优化点：使用缩进排版输出 JSON，一行一个字段 ---
            logs.append(json.dumps(final_dict, ensure_ascii=False, indent=4))
            
            return RecognitionResult(final_dict, logs)

        except Exception as e:
            logs.append(f"[CRITICAL] 识别流程崩溃: {str(e)}\n{traceback.format_exc()}")
            return RecognitionResult({"title": "识别失败"}, logs)
