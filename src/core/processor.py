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
        """在这里，我们将所有调试信息写入 logs 列表，这会显示在 GUI 的日志框中"""
        # 1. 计算核心库 src 目录
        core_src_path = os.path.normpath(os.path.join(CORE_ALGO_DIR, "src"))
        logs.append(f"┃ [DEBUG] 程序根目录: {APP_ROOT}")
        logs.append(f"┃ [DEBUG] 正在检索内核: {core_src_path}")
        
        # 2. 物理检查
        if not os.path.exists(core_src_path):
            logs.append(f"┣ ❌ 错误：在上述路径下未找到 'src' 文件夹。")
            logs.append(f"┣ 💡 请确保：{CORE_ALGO_DIR} 文件夹下包含 'src' 目录。")
            return None

        # 3. 动态注入 sys.path
        if core_src_path not in sys.path:
            sys.path.insert(0, core_src_path)
            importlib.invalidate_caches()
            logs.append(f"┣ ✅ 已将路径加入系统搜索列表")

        # 4. 尝试导入关键组件
        try:
            # 预检依赖
            import regex
            
            # 动态导入 (必须使用 __import__ 或在此时 import，防止顶部导入失败)
            from anime_matcher.kernel import core_recognize
            from anime_matcher.special_episode_handler import SpecialEpisodeHandler
            from anime_matcher.providers.tmdb.client import TMDBProvider
            from anime_matcher.providers.bangumi.client import BangumiProvider
            from anime_matcher.storage_manager import storage
            
            logs.append("┣ ✅ 核心算法组件加载成功！")
            return {
                "recognize": core_recognize,
                "sp_handler": SpecialEpisodeHandler,
                "tmdb": TMDBProvider,
                "bgm": BangumiProvider,
                "storage": storage
            }
        except ImportError as e:
            logs.append(f"┣ ❌ 依赖缺失: {str(e)}")
            logs.append(f"┣ 💡 请确保环境已安装: regex, requests, peewee")
            return None
        except Exception as e:
            logs.append(f"┣ ❌ 导入崩溃: {str(e)}")
            logs.append(f"┣ 📋 堆栈: {traceback.format_exc().splitlines()[-1]}")
            return None

    def recognize_file(self, filename_path: str) -> RecognitionResult:
        """主入口"""
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
        filename = os.path.basename(filename_path)

        # 这里的 logs 会通过 RecognitionResult 返回给 UI
        components = self._get_core_components(logs)
        if not components:
            # 虽然返回了结果，但 logs 里已经包含了详细的 DEBUG 信息
            return RecognitionResult({"title": "内核未就绪"}, logs)

        try:
            # 识别逻辑开始...
            from src.core.rules import RuleManager
            db_noise = RuleManager.get_merged_rules('noise')
            db_groups = RuleManager.get_merged_rules('group')
            db_priv = RuleManager.get_merged_rules('privileged')
            
            if db_priv:
                components["sp_handler"].load_external_rules(db_priv)

            meta = components["recognize"](
                input_name=filename,
                custom_words=list(set(self.custom_words + db_noise)),
                custom_groups=list(set(self.custom_groups + db_groups)),
                original_input=filename,
                current_logs=logs,
                batch_enhancement=self.config.get('batch_enhancement', False),
                force_filename=True
            )

            # 后续逻辑保持不变...
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

            if self.config.get('with_cloud') and self.config.get('tmdb_api_key'):
                tmdb = components["tmdb"](api_key=self.config['tmdb_api_key'], proxy=self.config.get('tmdb_proxy'))
                m_type = "movie" if final_dict["category"] == "电影" else "tv"
                
                # 检查智能记忆
                if self.config.get('use_storage'):
                    pattern_key = f"{meta.cn_name or meta.en_name}|{meta.year}"
                    memory = components["storage"].get_memory(pattern_key)
                    if memory:
                        final_dict["tmdb_id"] = memory['tmdb_id']
                        logs.append(f"┃ [STORAGE] ⚡ 命中心特征记忆: {final_dict['tmdb_id']}")

                # 搜索详情
                if final_dict["tmdb_id"]:
                    cloud_data = await tmdb.get_details(final_dict["tmdb_id"], m_type, logs)
                else:
                    cloud_data = await tmdb.smart_search(meta.cn_name, meta.en_name, meta.year, m_type, logs)
                
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
            return RecognitionResult({"title": "识别失败"}, logs)
