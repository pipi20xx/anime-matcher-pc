import os
import sys
import datetime
import traceback
import urllib.parse
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTextEdit, QFileDialog, QMessageBox,
                             QProgressBar, QGroupBox, QLineEdit, QTableWidget,
                             QTableWidgetItem, QHeaderView, QTabWidget, QFormLayout,
                             QComboBox, QPlainTextEdit, QCheckBox, QSplitter)
from PyQt6.QtCore import Qt, QUrl
from src.utils.config import config
from src.gui.worker import RenameWorker
from src.gui.rule_manager import RuleManagerWidget

VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.ts', '.flv', '.webm', '.mpg', '.mpeg']

class VideoRenamerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("剧集视频重命名工具 (Anime-Matcher Core) - PyQt6")
        self.setGeometry(100, 100, 1350, 850)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)
        self.worker = None
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        self.main_tab = QWidget()
        self.tab_widget.addTab(self.main_tab, "主界面")
        self.init_main_tab()
        
        # 规则管理 Tab
        self.rule_tab = RuleManagerWidget()
        self.tab_widget.addTab(self.rule_tab, "识别规则管理")

        self.settings_tab = QWidget()
        self.tab_widget.addTab(self.settings_tab, "设置")
        self.init_settings_tab()

    def init_main_tab(self):
        main_tab_layout = QVBoxLayout(self.main_tab)
        self.top_splitter = QSplitter(Qt.Orientation.Horizontal) 

        # 左侧：文件选择
        left_pane_widget = QWidget()
        left_pane_layout = QVBoxLayout(left_pane_widget)
        left_pane_layout.setContentsMargins(0,0,0,0)
        file_group = QGroupBox("文件/文件夹选择")
        file_layout = QVBoxLayout()
        self.file_list = QTextEdit()
        self.file_list.setPlaceholderText("拖放剧集文件或文件夹到这里...")
        # 禁用 QTextEdit 自身的拖拽接受，让事件传递给主窗口的 dropEvent 处理
        self.file_list.setAcceptDrops(False) 
        btn_layout = QHBoxLayout()
        self.browse_files_btn = QPushButton("浏览文件")
        self.browse_files_btn.clicked.connect(self.browse_files)
        self.browse_folder_btn = QPushButton("浏览文件夹")
        self.browse_folder_btn.clicked.connect(self.browse_folder)
        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_file_list)
        btn_layout.addWidget(self.browse_files_btn)
        btn_layout.addWidget(self.browse_folder_btn)
        btn_layout.addWidget(self.clear_btn)
        file_layout.addWidget(self.file_list)
        file_layout.addLayout(btn_layout)
        file_group.setLayout(file_layout)
        left_pane_layout.addWidget(file_group)
        self.top_splitter.addWidget(left_pane_widget)

        # 右侧：自定义选项
        right_pane_widget = QWidget()
        right_pane_layout = QVBoxLayout(right_pane_widget)
        right_pane_layout.setContentsMargins(0,0,0,0)
        custom_options_group = QGroupBox("自定义覆盖选项")
        custom_options_form_layout = QFormLayout()

        self.custom_season_checkbox = QCheckBox("自定义季度")
        self.custom_season_input = QLineEdit()
        self.custom_season_input.setPlaceholderText("例如: 1")
        self.custom_season_input.setEnabled(False)
        self.custom_season_checkbox.toggled.connect(self.custom_season_input.setEnabled)
        custom_options_form_layout.addRow(self.custom_season_checkbox, self.custom_season_input)

        self.custom_episode_offset_checkbox = QCheckBox("自定义集数偏移")
        self.custom_episode_offset_input = QLineEdit()
        self.custom_episode_offset_input.setPlaceholderText("例如: 12 或 -12")
        self.custom_episode_offset_input.setEnabled(False)
        self.custom_episode_offset_checkbox.toggled.connect(self.custom_episode_offset_input.setEnabled)
        custom_options_form_layout.addRow(self.custom_episode_offset_checkbox, self.custom_episode_offset_input)

        self.custom_tmdbid_checkbox = QCheckBox("自定义TMDBID")
        tmdb_id_line_layout = QHBoxLayout()
        self.custom_tmdbid_input = QLineEdit()
        self.custom_tmdbid_input.setEnabled(False)
        tmdb_id_line_layout.addWidget(self.custom_tmdbid_input, 2)
        self.custom_tmdb_media_type_combo = QComboBox()
        self.custom_tmdb_media_type_combo.addItem("剧集 (TV)", "tv")
        self.custom_tmdb_media_type_combo.addItem("电影 (Movie)", "movie")
        self.custom_tmdb_media_type_combo.setEnabled(False)
        tmdb_id_line_layout.addWidget(self.custom_tmdb_media_type_combo, 1)
        custom_options_form_layout.addRow(self.custom_tmdbid_checkbox, tmdb_id_line_layout)
        self.custom_tmdbid_checkbox.toggled.connect(self.custom_tmdbid_input.setEnabled)
        self.custom_tmdbid_checkbox.toggled.connect(self.custom_tmdb_media_type_combo.setEnabled)

        custom_options_group.setLayout(custom_options_form_layout)
        right_pane_layout.addWidget(custom_options_group)
        right_pane_layout.addStretch(1)
        self.top_splitter.addWidget(right_pane_widget)

        self.top_splitter.setSizes([int(self.width() * 0.5), int(self.width() * 0.5)])
        main_tab_layout.addWidget(self.top_splitter, 1)

        # 预览/结果表格
        preview_group = QGroupBox("预览/结果")
        preview_layout = QHBoxLayout()
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(["原文件名", "新文件名", "目标主文件夹", "目标季文件夹"])
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        preview_layout.addWidget(self.preview_table)
        preview_group.setLayout(preview_layout)
        main_tab_layout.addWidget(preview_group, 1)

        # 日志与进度
        progress_group = QGroupBox("日志与进度")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.log_output)
        progress_group.setLayout(progress_layout)
        main_tab_layout.addWidget(progress_group, 1)

        # 操作按钮
        action_layout = QHBoxLayout()
        self.preview_btn = QPushButton("预览重命名")
        self.preview_btn.clicked.connect(lambda: self.start_processing(preview_only=True))
        self.execute_btn = QPushButton("执行重命名")
        self.execute_btn.clicked.connect(lambda: self.start_processing(preview_only=False))
        self.execute_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_processing)
        self.cancel_btn.setEnabled(False)
        action_layout.addWidget(self.preview_btn)
        action_layout.addWidget(self.execute_btn)
        action_layout.addWidget(self.cancel_btn)
        main_tab_layout.addLayout(action_layout)
        self.setAcceptDrops(True)

    def init_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)
        
        format_group = QGroupBox("重命名格式与占位符")
        format_layout = QFormLayout()
        
        # 增加更专业的默认格式选项
        self.rename_format_combo = QComboBox()
        self.rename_format_combo.addItems([
            "[{team}] {title} - S{season}E{episode} [{resolution}][{video_encode}][{subtitle}]",
            "{title} ({year}) - S{season}E{episode} [{resolution}]",
            "{title} - S{season}E{episode} - {filename}",
            "{title}.S{season}E{episode}.{resolution}.{video_encode}-{team}",
            "S{season}E{episode}.{title}"
        ])
        self.rename_format_combo.setEditable(True)
        format_layout.addRow("文件名格式:", self.rename_format_combo)
        
        self.folder_format_input = QLineEdit()
        self.folder_format_input.setText("({year}){title}[tmdbid={tmdbid}]")
        format_layout.addRow("主文件夹格式:", self.folder_format_input)
        
        self.season_format_input = QLineEdit()
        self.season_format_input.setText("Season {season_int}")
        format_layout.addRow("季文件夹格式:", self.season_format_input)
        
        # 增加占位符说明按钮
        self.help_btn = QPushButton("查看所有可用占位符说明")
        self.help_btn.clicked.connect(self.show_placeholder_help)
        format_layout.addRow(self.help_btn)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        regex_group = QGroupBox("正则替换规则 (应用于新文件名)")
        regex_layout = QVBoxLayout()
        self.regex_rules_edit = QPlainTextEdit()
        placeholder = "例如:\n(?i) unwanted => replacement\n\\[[^\\]]*\\] => (移除方括号内容)"
        self.regex_rules_edit.setPlaceholderText(placeholder)
        regex_layout.addWidget(self.regex_rules_edit)
        regex_group.setLayout(regex_layout)
        layout.addWidget(regex_group)

        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        algo_group = QGroupBox("算法管理")
        algo_layout = QVBoxLayout()
        self.algo_status_label = QLabel("核心算法状态: 正在检查...")
        
        btn_h_layout = QHBoxLayout()
        self.download_algo_btn = QPushButton("自动下载/更新 (GitHub)")
        self.download_algo_btn.clicked.connect(self.download_core_algorithm)
        self.manual_algo_btn = QPushButton("手动部署说明")
        self.manual_algo_btn.clicked.connect(self.show_manual_instructions)
        btn_h_layout.addWidget(self.download_algo_btn)
        btn_h_layout.addWidget(self.manual_algo_btn)
        
        algo_layout.addWidget(self.algo_status_label)
        algo_layout.addLayout(btn_h_layout)
        algo_group.setLayout(algo_layout)
        layout.addWidget(algo_group)

        layout.addStretch(1)
        self.check_algo_status()

    def show_manual_instructions(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        target_path = os.path.join(root_dir, "anime-matcher-main")
        
        instructions = (
            "<b>手动部署核心算法步骤:</b><br><br>"
            "1. 访问 GitHub 项目页: <a href='https://github.com/pipi20xx/anime-matcher'>https://github.com/pipi20xx/anime-matcher</a><br>"
            "2. 点击 'Code' -> 'Download ZIP' 下载压缩包。<br>"
            "3. 解压下载的 ZIP 文件。<br>"
            "4. 将解压出来的文件夹重命名为 <b>anime-matcher-main</b>。<br>"
            "5. 将该文件夹移动到本软件的根目录下：<br>"
            f"<code style='color: blue;'>{root_dir}</code><br><br>"
            "<b>完成后的目录结构应该是:</b><br>"
            f"┣ {os.path.basename(root_dir)}/<br>"
            "┃ ┣ anime-matcher-main/ (核心算法文件夹)<br>"
            "┃ ┣ main.py (本程序入口)<br>"
            "┃ ┗ src/ (本程序代码)<br><br>"
            "部署完成后，重启本软件或再次检查状态即可。"
        )
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("手动部署核心算法指南")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(instructions)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()

    def check_algo_status(self):
        core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "anime-matcher-main")
        if os.path.exists(core_path):
            self.algo_status_label.setText("核心算法状态: 已就绪 (本地已存在)")
            self.algo_status_label.setStyleSheet("color: green;")
            return True
        else:
            self.algo_status_label.setText("核心算法状态: 未找到 (请下载)")
            self.algo_status_label.setStyleSheet("color: red;")
            return False

    def download_core_algorithm(self):
        from src.utils.downloader import DownloadWorker
        url = "https://github.com/pipi20xx/anime-matcher/archive/refs/heads/main.zip"
        target_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "anime-matcher-main")
        
        self.download_algo_btn.setEnabled(False)
        self.log_output.append("[INFO] 开始下载核心算法...")
        self.progress_bar.setValue(0)
        
        self.dl_worker = DownloadWorker(url, target_dir)
        self.dl_worker.progress_signal.connect(self.progress_bar.setValue)
        self.dl_worker.log_signal.connect(self.log_output.append)
        self.dl_worker.finished_signal.connect(self.on_download_finished)
        self.dl_worker.start()

    def on_download_finished(self, success, message):
        self.download_algo_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "成功", message)
            self.check_algo_status()
        else:
            QMessageBox.warning(self, "失败", message)

    def load_settings(self):
        self.rename_format_combo.setCurrentText(config.get_value("rename_format", "{title} - S{season}E{episode} - {filename}"))
        self.folder_format_input.setText(config.get_value("folder_format", "({year}){title}[tmdbid={tmdbid}]"))
        self.season_format_input.setText(config.get_value("season_format", "Season {season_int}"))
        self.regex_rules_edit.setPlainText(config.get_value("regex_rules", ""))
        self.custom_season_checkbox.setChecked(config.get_value("custom_season_enabled", False, type=bool))
        self.custom_tmdbid_checkbox.setChecked(config.get_value("custom_tmdbid_enabled", False, type=bool))

    def show_placeholder_help(self):
        msg = (
            "<b>可用占位符说明 (全字段对齐):</b><br><br>"
            "<b>基础信息:</b><br>"
            "  {title}: 最终采信标题<br>"
            "  {season}: 补零季度 (如 01)<br>"
            "  {season_int}: 原始季度 (如 1)<br>"
            "  {episode}: 补零集数或范围 (如 13 或 01-12)<br>"
            "  {year}: 最终采信年份<br>"
            "  {tmdb_id} / {tmdbid}: TMDB 编号<br><br>"
            "<b>技术规格:</b><br>"
            "  {team}: 制作小组 (如 Airota)<br>"
            "  {resolution}: 分辨率 (如 1080p)<br>"
            "  {video_encode}: 视频编码 (如 x265)<br>"
            "  {video_effect}: 视频特效 (如 HDR, DV)<br>"
            "  {audio_encode}: 音频编码 (如 FLAC)<br>"
            "  {subtitle}: 字幕语言 (如 CHS, CHT)<br><br>"
            "<b>高级属性:</b><br>"
            "  {source}: 资源来源 (如 WEB-DL, BluRay)<br>"
            "  {platform}: 发布平台 (如 B-Global)<br>"
            "  {category}: 媒体分类 (剧集 / 电影)<br>"
            "  {origin_country}: 制片国家<br>"
            "  {vote_average}: 评分<br><br>"
            "<b>程序字段:</b><br>"
            "  {filename}: 原始文件名(无扩展名)<br>"
            "  {duration}: 识别耗时"
        )
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("占位符使用帮助")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(msg)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()

    def save_settings(self):
        config.set_value("rename_format", self.rename_format_combo.currentText())
        config.set_value("folder_format", self.folder_format_input.text())
        config.set_value("season_format", self.season_format_input.text())
        config.set_value("regex_rules", self.regex_rules_edit.toPlainText())
        config.set_value("custom_season_enabled", self.custom_season_checkbox.isChecked())
        config.set_value("custom_tmdbid_enabled", self.custom_tmdbid_checkbox.isChecked())
        QMessageBox.information(self, "成功", "设置已保存！")

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择视频文件", "", "视频文件 (*.mkv *.mp4 *.avi *.ts);;所有文件 (*.*)")
        if files: self.add_paths_to_list(files)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            video_files = []
            for root, _, files in os.walk(folder):
                for f in files:
                    if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS:
                        video_files.append(os.path.join(root, f))
            self.add_paths_to_list(video_files)

    def add_paths_to_list(self, paths):
        current_text = self.file_list.toPlainText()
        existing = set(current_text.splitlines())
        
        processed_paths = []
        for p in paths:
            # 1. URL 解码 (修复百分号编码)
            p = urllib.parse.unquote(p)
            
            # 2. 剥离 file:/// 或 file:// 前缀
            if p.startswith('file:///'):
                p = p[8:]
            elif p.startswith('file://'):
                p = p[7:]
            
            # 3. 针对 Windows 下的路径修正 (如 /D:/ -> D:/)
            if os.name == 'nt' and len(p) > 2 and p[0] == '/' and p[2] == ':':
                p = p[1:]
                
            # 4. 标准化路径格式
            p = os.path.normpath(p)
            
            if p not in existing:
                processed_paths.append(p)
                existing.add(p)

        if processed_paths:
            prefix = "\n" if current_text.strip() else ""
            self.file_list.append(prefix + "\n".join(processed_paths))

    def clear_file_list(self):
        self.file_list.clear()
        self.preview_table.setRowCount(0)
        self.progress_bar.setValue(0)

    def start_processing(self, preview_only=False):
        file_text = self.file_list.toPlainText()
        file_paths = [p.strip() for p in file_text.splitlines() if p.strip()]
        if not file_paths:
            QMessageBox.warning(self, "警告", "请先添加文件！")
            return

        # 构造配置数据
        config_data = {
            'rename_format': self.rename_format_combo.currentText(),
            'folder_format': self.folder_format_input.text(),
            'season_format': self.season_format_input.text(),
            'regex_rules': self.parse_regex_rules(),
            'custom_settings': {
                'custom_season_enabled': self.custom_season_checkbox.isChecked(),
                'custom_season_value': self.custom_season_input.text(),
                'custom_episode_offset_enabled': self.custom_episode_offset_checkbox.isChecked(),
                'custom_episode_offset_value': self.custom_episode_offset_input.text(),
                'tmdb_id_override': self.custom_tmdbid_input.text() if self.custom_tmdbid_checkbox.isChecked() else None,
                'media_type_override': self.custom_tmdb_media_type_combo.currentData()
            }
        }

        self.preview_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.set_ui_enabled(False)

        self.worker = RenameWorker(file_paths, config_data, preview_only)
        self.worker.log_signal.connect(self.log_output.append)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.preview_signal.connect(self.update_preview_table)
        self.worker.finished_signal.connect(self.processing_finished)
        self.worker.start()

    def parse_regex_rules(self):
        rules = []
        for line in self.regex_rules_edit.toPlainText().splitlines():
            if '=>' in line:
                p, r = line.split('=>', 1)
                rules.append((p.strip(), r.strip()))
        return rules

    def update_preview_table(self, old, new, main, season):
        row = self.preview_table.rowCount()
        self.preview_table.insertRow(row)
        self.preview_table.setItem(row, 0, QTableWidgetItem(old))
        self.preview_table.setItem(row, 1, QTableWidgetItem(new))
        self.preview_table.setItem(row, 2, QTableWidgetItem(main))
        self.preview_table.setItem(row, 3, QTableWidgetItem(season))
        self.preview_table.scrollToBottom()

    def set_ui_enabled(self, enabled):
        self.browse_files_btn.setEnabled(enabled)
        self.browse_folder_btn.setEnabled(enabled)
        self.preview_btn.setEnabled(enabled)
        self.execute_btn.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
        self.cancel_btn.setEnabled(not enabled)

    def cancel_processing(self):
        if self.worker: self.worker.requestInterruption()

    def processing_finished(self, results):
        self.set_ui_enabled(True)
        QMessageBox.information(self, "完成", f"处理完成！共处理 {len(results)} 个文件。")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            # 获取拖拽内容的原始字符串表示
            urls = [u.toString() for u in event.mimeData().urls()]
            self.add_paths_to_list(urls)
            event.acceptProposedAction()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoRenamerGUI()
    window.show()
    sys.exit(app.exec())
