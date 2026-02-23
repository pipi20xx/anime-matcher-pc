import os
import re
import traceback

class RenameEngine:
    """处理全字段重命名的最终路径生成引擎"""
    def __init__(self, rename_format, folder_format, season_format, regex_rules=None):
        self.rename_format = rename_format
        self.folder_format = folder_format
        self.season_format = season_format
        self.regex_rules = regex_rules or []

    def apply_regex_rules(self, text, is_filename=True):
        if not is_filename: return text
        for pattern_str, replacement in self.regex_rules:
            try:
                flags = 0
                if pattern_str.startswith('(?i)') or pattern_str.startswith('(?I)'):
                    pattern_str, flags = pattern_str[4:], re.IGNORECASE
                text = re.sub(pattern_str, replacement, text, flags=flags)
            except re.error: continue
        return text

    def build_paths(self, old_path, rec_result, custom_settings=None):
        """
        根据核心识别结果和全字段构建重命名路径。
        rec_result: RecognitionResult 对象，包含所有 final_result 字段。
        """
        old_filename = os.path.basename(old_path)
        old_dir = os.path.dirname(old_path)
        file_no_ext, ext = os.path.splitext(old_filename)

        # 1. 提取全字段
        format_data = rec_result.to_dict().copy()
        
        # 补全重命名引擎需要的额外字段
        format_data['season_int'] = str(format_data.get('season', 1))
        format_data['season'] = str(format_data.get('season', 1)).zfill(2)
        format_data['episode'] = str(format_data.get('episode', '01')).zfill(2)
        format_data['tmdbid'] = format_data.get('tmdb_id', 'N/A')

        # 2. 应用自定义覆盖
        if custom_settings:
            if custom_settings.get('tmdb_id_override'):
                format_data['tmdb_id'] = custom_settings['tmdb_id_override']
                format_data['tmdbid'] = custom_settings['tmdb_id_override']
            if custom_settings.get('custom_season_enabled'):
                s_val = custom_settings['custom_season_value']
                format_data['season_int'] = s_val
                format_data['season'] = s_val.zfill(2)
            if custom_settings.get('custom_episode_offset_enabled'):
                try:
                    offset = int(custom_settings.get('custom_episode_offset_value', 0))
                    original_ep = int(format_data.get('episode', 1))
                    new_ep = max(1, original_ep + offset)
                    format_data['episode'] = str(new_ep).zfill(2)
                except (ValueError, TypeError): pass

        # 3. 填充文件名占位符
        new_filename = self.rename_format
        # 针对电影模式且无季度指定时的逻辑
        if format_data.get('category') == "电影" and not (custom_settings and custom_settings.get('custom_season_enabled')):
             new_filename = re.sub(r'S\w*[\s\._-]*E\w*', '', new_filename, flags=re.IGNORECASE).strip()
             new_filename = re.sub(r'Season\s*\w*[\s\._-]*Episode\s*\w*', '', new_filename, flags=re.IGNORECASE).strip()
        
        # 动态替换所有 {}
        for k, v in format_data.items():
            new_filename = new_filename.replace(f'{{{k}}}', str(v) if v is not None else "")
        
        new_filename = self.apply_regex_rules(new_filename)
        new_filename = re.sub(r'[<>:"/\\|?*]', '_', new_filename).strip(" .")

        # 4. 生成文件夹路径
        main_folder = self.folder_format
        for k, v in format_data.items():
            main_folder = main_folder.replace(f'{{{k}}}', str(v) if v is not None else "")
        main_folder = re.sub(r'[<>:"/\\|?*]', '_', main_folder).strip(" .")

        season_folder = ""
        # 只有在非电影模式或者强制指定了季度时，才生成季文件夹
        if self.season_format.strip() and (format_data.get('category') == "剧集" or (custom_settings and custom_settings.get('custom_season_enabled'))):
            season_folder = self.season_format
            for k, v in format_data.items():
                season_folder = season_folder.replace(f'{{{k}}}', str(v) if v is not None else "")
            season_folder = re.sub(r'[<>:"/\\|?*]', '_', season_folder).strip(" .")

        # 5. 组装最终完整路径
        target_dir = os.path.join(old_dir, main_folder, season_folder) if season_folder else os.path.join(old_dir, main_folder)
        new_full_path = os.path.join(target_dir, f"{new_filename}{ext}")

        return new_full_path, main_folder, season_folder

    def execute_rename(self, old_path, new_path):
        if os.path.normpath(old_path) == os.path.normpath(new_path):
            return True, "无需重命名 (路径未变化)"
        if os.path.exists(new_path):
            return False, f"目标路径已存在: {new_path}"
        try:
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            os.rename(old_path, new_path)
            return True, "成功"
        except Exception as e:
            return False, f"重命名失败: {str(e)}"
