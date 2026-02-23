import os
import re
import traceback

class RenameEngine:
    """处理重命名的最终路径生成和文件操作"""
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
            except re.error:
                continue
        return text

    def build_paths(self, old_path, rec_result, custom_settings=None):
        """
        根据识别结果和用户设置计算新的完整路径。
        custom_settings: {
            'custom_season_enabled': bool, 'custom_season_value': str,
            'custom_episode_offset_enabled': bool, 'custom_episode_offset_value': str,
            'tmdb_id_override': str, 'media_type_override': str
        }
        """
        old_filename = os.path.basename(old_path)
        old_dir = os.path.dirname(old_path)
        file_no_ext, ext = os.path.splitext(old_filename)

        # 1. 应用自定义覆盖
        title = rec_result.title
        year = rec_result.year
        tmdb_id = rec_result.tmdb_id
        media_type = rec_result.media_type
        season_raw = rec_result.season
        episode_raw = rec_result.episode

        if custom_settings:
            if custom_settings.get('tmdb_id_override'):
                tmdb_id = custom_settings['tmdb_id_override']
                media_type = custom_settings.get('media_type_override', 'tv')
            if custom_settings.get('custom_season_enabled'):
                season_raw = custom_settings['custom_season_value']
            
            # 处理集数偏移
            if custom_settings.get('custom_episode_offset_enabled'):
                try:
                    offset = int(custom_settings.get('custom_episode_offset_value', 0))
                    episode_raw = str(max(1, int(episode_raw) + offset))
                except (ValueError, TypeError): pass

        # 2. 格式化变量准备
        season_padded = str(season_raw).zfill(2)
        episode_padded = str(episode_raw).zfill(2)
        
        format_data = {
            'title': title, 'year': year, 'tmdbid': tmdb_id,
            'season': season_padded, 'season_int': str(season_raw),
            'episode': episode_padded, 'filename': file_no_ext
        }

        # 3. 生成新文件名
        new_filename = self.rename_format
        if media_type == "movie" and not (custom_settings and custom_settings.get('custom_season_enabled')):
            # 电影模式下剥离 S/E 部分
            new_filename = re.sub(r'S\w*[\s\._-]*E\w*', '', new_filename, flags=re.IGNORECASE).strip()
            new_filename = re.sub(r'Season\s*\w*[\s\._-]*Episode\s*\w*', '', new_filename, flags=re.IGNORECASE).strip()
        
        for k, v in format_data.items():
            new_filename = new_filename.replace(f'{{{k}}}', str(v))
        
        new_filename = self.apply_regex_rules(new_filename)
        new_filename = re.sub(r'[<>:"/\|?*]', '_', new_filename).strip(" .")

        # 4. 生成文件夹路径
        main_folder = self.folder_format
        for k, v in format_data.items():
            main_folder = main_folder.replace(f'{{{k}}}', str(v))
        main_folder = re.sub(r'[<>:"/\|?*]', '_', main_folder).strip(" .")

        season_folder = ""
        if self.season_format.strip() and (media_type == "tv" or (custom_settings and custom_settings.get('custom_season_enabled'))):
            season_folder = self.season_format
            for k, v in format_data.items():
                season_folder = season_folder.replace(f'{{{k}}}', str(v))
            season_folder = re.sub(r'[<>:"/\|?*]', '_', season_folder).strip(" .")

        # 5. 组合最终完整路径
        target_dir = os.path.join(old_dir, main_folder, season_folder) if season_folder else os.path.join(old_dir, main_folder)
        new_full_path = os.path.join(target_dir, f"{new_filename}{ext}")

        return new_full_path, main_folder, season_folder

    def execute_rename(self, old_path, new_path):
        """执行实际的文件移动操作"""
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
