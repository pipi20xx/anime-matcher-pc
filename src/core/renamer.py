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

    def apply_regex_rules(self, text):
        for pattern_str, replacement in self.regex_rules:
            try:
                flags = 0
                if pattern_str.startswith('(?i)') or pattern_str.startswith('(?I)'):
                    pattern_str, flags = pattern_str[4:], re.IGNORECASE
                text = re.sub(pattern_str, replacement, text, flags=flags)
            except re.error: continue
        return text

    def build_paths(self, old_path, rec_result, custom_settings=None):
        old_filename = os.path.basename(old_path)
        old_dir = os.path.dirname(old_path)
        file_no_ext, ext = os.path.splitext(old_filename)

        # 1. 基础数据
        raw_data = rec_result.to_dict().copy()
        
        # 2. 映射用户要求的具体占位符名
        # 处理补零
        s_val = raw_data.get('season', 1)
        e_val = raw_data.get('episode', '1')
        
        # 3. 应用自定义覆盖逻辑
        if custom_settings:
            if custom_settings.get('tmdb_id_override'):
                raw_data['tmdb_id'] = custom_settings['tmdb_id_override']
            if custom_settings.get('custom_season_enabled'):
                s_val = custom_settings['custom_season_value']
            if custom_settings.get('custom_episode_offset_enabled'):
                try:
                    offset = int(custom_settings.get('custom_episode_offset_value', 0))
                    original_ep = int(re.search(r'\d+', str(e_val)).group()) if re.search(r'\d+', str(e_val)) else 1
                    e_val = str(max(1, original_ep + offset))
                except: pass

        # 构造最终用于替换的字典
        format_data = {
            'title': raw_data.get('title', ''),
            'year': raw_data.get('year', ''),
            'category': raw_data.get('category', ''),
            'season': str(s_val),
            'season_02': str(s_val).zfill(2),
            'episode': str(e_val),
            'episode_02': str(e_val).zfill(2),
            'resolution': raw_data.get('resolution', ''),
            'team': raw_data.get('team', ''),
            'source': raw_data.get('source', ''),
            'video_encode': raw_data.get('video_encode', ''),
            'audio_encode': raw_data.get('audio_encode', ''),
            'subtitle': raw_data.get('subtitle', ''),
            'video_effect': raw_data.get('video_effect', ''),
            'platform': raw_data.get('platform', ''),
            'release_date': raw_data.get('release_date', ''),
            'tmdb_id': raw_data.get('tmdb_id', ''),
            'secondary_category': raw_data.get('secondary_category', ''),
            'main_category': raw_data.get('main_category', ''),
            'origin_country': raw_data.get('origin_country', ''),
            'filename': file_no_ext, # 清洗后原名
            'processed_name': raw_data.get('processed_name', ''),
            'original_filename': old_filename,
            'path': old_path
        }

        # 4. 执行替换
        new_filename = self.rename_format
        if format_data.get('category') == "电影" and not (custom_settings and custom_settings.get('custom_season_enabled')):
             new_filename = re.sub(r'S\w*[\s\._-]*E\w*', '', new_filename, flags=re.IGNORECASE).strip()
        
        for k, v in format_data.items():
            new_filename = new_filename.replace(f'{{{k}}}', str(v) if v is not None else "")
        
        new_filename = self.apply_regex_rules(new_filename)
        new_filename = re.sub(r'[<>:"/\\|?*]', '_', new_filename).strip(" .")

        main_folder = self.folder_format
        for k, v in format_data.items():
            main_folder = main_folder.replace(f'{{{k}}}', str(v) if v is not None else "")
        main_folder = re.sub(r'[<>:"/\\|?*]', '_', main_folder).strip(" .")

        season_folder = ""
        if self.season_format.strip() and (format_data.get('category') == "剧集" or (custom_settings and custom_settings.get('custom_season_enabled'))):
            season_folder = self.season_format
            for k, v in format_data.items():
                season_folder = season_folder.replace(f'{{{k}}}', str(v) if v is not None else "")
            season_folder = re.sub(r'[<>:"/\\|?*]', '_', season_folder).strip(" .")

        target_dir = os.path.join(old_dir, main_folder, season_folder) if season_folder else os.path.join(old_dir, main_folder)
        return os.path.join(target_dir, f"{new_filename}{ext}"), main_folder, season_folder

    def execute_rename(self, old_path, new_path):
        if os.path.normpath(old_path) == os.path.normpath(new_path):
            return True, "无需重命名"
        if os.path.exists(new_path):
            return False, f"目标已存在: {new_path}"
        try:
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            os.rename(old_path, new_path)
            return True, "成功"
        except Exception as e:
            return False, str(e)
