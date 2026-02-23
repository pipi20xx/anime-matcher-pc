import os
import zipfile
import requests
import shutil
import tempfile
import traceback
from PyQt6.QtCore import QThread, pyqtSignal

class DownloadWorker(QThread):
    """鲁棒的后台下载与自动部署核心算法线程"""
    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, url, target_dir):
        super().__init__()
        self.url = url
        self.target_dir = target_dir  # 最终目录名，如 .../anime-matcher-main

    def run(self):
        tmp_zip = None
        extract_tmp_dir = None
        try:
            self.log_signal.emit(f"[INFO] 正在从 {self.url} 下载算法包...")
            
            # 1. 下载文件
            response = requests.get(self.url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
                for chunk in response.iter_content(chunk_size=16384):
                    if chunk:
                        tmp_file.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.progress_signal.emit(progress)
                tmp_zip = tmp_file.name

            self.log_signal.emit("[INFO] 下载完成，正在准备解压部署...")

            # 2. 创建一个临时的解压中转目录
            extract_tmp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(tmp_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_tmp_dir)

            # 3. 寻找解压出来的真实文件夹 (GitHub ZIP 会在根目录放一个名为 'anime-matcher-main' 或类似名称的文件夹)
            # 我们寻找第一个包含 __init__.py 的子目录或者第一个文件夹
            items = os.listdir(extract_tmp_dir)
            if not items:
                raise Exception("ZIP 压缩包内为空")
            
            extracted_folder_name = items[0]
            source_path = os.path.join(extract_tmp_dir, extracted_folder_name)

            # 4. 部署到目标位置
            if os.path.exists(self.target_dir):
                self.log_signal.emit("[INFO] 清理旧版核心...")
                shutil.rmtree(self.target_dir)

            self.log_signal.emit(f"[INFO] 正在将 {extracted_folder_name} 部署到目标路径...")
            shutil.move(source_path, self.target_dir)

            self.finished_signal.emit(True, "核心算法部署成功！")
            
        except Exception as e:
            err_msg = f"操作失败: {str(e)}"
            self.log_signal.emit(f"[ERROR] {err_msg}\n{traceback.format_exc()}")
            self.finished_signal.emit(False, err_msg)
        
        finally:
            # 清理临时工作区
            if tmp_zip and os.path.exists(tmp_zip):
                os.remove(tmp_zip)
            if extract_tmp_dir and os.path.exists(extract_tmp_dir):
                shutil.rmtree(extract_tmp_dir)
