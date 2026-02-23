import os
import traceback
from PyQt6.QtCore import QThread, pyqtSignal
from src.core.processor import RecognitionProcessor
from src.core.renamer import RenameEngine

class RenameWorker(QThread):
    """协调 UI、识别和重命名的后台线程"""
    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    preview_signal = pyqtSignal(str, str, str, str)  # 原名, 新名, 主文件夹, 季文件夹
    finished_signal = pyqtSignal(list)

    def __init__(self, file_paths, config_data, preview_only=False):
        super().__init__()
        self.file_paths = file_paths
        self.config_data = config_data
        self.preview_only = preview_only
        self._is_interrupted = False
        self.results = []

    def requestInterruption(self):
        self._is_interrupted = True
        self.log_signal.emit("[INFO] 重命名已中断。")

    def run(self):
        total_files = len(self.file_paths)
        if total_files == 0:
            self.finished_signal.emit([])
            return

        # 1. 初始化处理器和重命名引擎
        processor = RecognitionProcessor(self.config_data)
        renamer = RenameEngine(
            rename_format=self.config_data.get('rename_format'),
            folder_format=self.config_data.get('folder_format'),
            season_format=self.config_data.get('season_format'),
            regex_rules=self.config_data.get('regex_rules', [])
        )

        processed_count = 0
        for i, video_path in enumerate(self.file_paths):
            if self._is_interrupted: break
            
            try:
                self.log_signal.emit(f"[INFO] 正在识别: {os.path.basename(video_path)}")
                
                # 2. 核心识别
                rec_result = processor.recognize_file(video_path)
                for log in rec_result.logs:
                    self.log_signal.emit(log)

                # 3. 计算新路径
                new_full_path, main_folder, season_folder = renamer.build_paths(
                    video_path, rec_result, self.config_data.get('custom_settings')
                )
                
                new_filename = os.path.basename(new_full_path)
                self.preview_signal.emit(os.path.basename(video_path), new_filename, main_folder, season_folder)

                # 4. 执行重命名（如果不是预览模式）
                if not self.preview_only:
                    success, msg = renamer.execute_rename(video_path, new_full_path)
                    if success:
                        self.log_signal.emit(f"[SUCCESS] {os.path.basename(video_path)} -> {new_filename}")
                        self.results.append((video_path, new_full_path))
                    else:
                        self.log_signal.emit(f"[ERROR] {os.path.basename(video_path)}: {msg}")
                else:
                    self.results.append((video_path, new_full_path))

                processed_count += 1
                progress = int((i + 1) / total_files * 100)
                self.progress_signal.emit(progress)

            except Exception as e:
                self.log_signal.emit(f"[CRITICAL] 处理文件时出错: {str(e)}")
                self.log_signal.emit(traceback.format_exc())

        self.finished_signal.emit(self.results)
