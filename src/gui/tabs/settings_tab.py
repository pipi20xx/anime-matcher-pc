import os
import requests
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, 
                             QLineEdit, QComboBox, QPlainTextEdit, QPushButton, 
                             QLabel, QMessageBox, QHBoxLayout)
from PyQt6.QtCore import Qt
from src.utils.config import config
from src.utils.downloader import DownloadWorker

class SettingsTab(QWidget):
    """
    设置与算法管理页签。
    负责：命名格式、正则规则、自定义覆盖、核心算法下载更新。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        # --- 1. 重命名格式 ---
        format_group = QGroupBox("重命名格式与占位符")
        format_layout = QFormLayout()
        
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
        format_layout.addRow("主文件夹格式:", self.folder_format_input)
        
        self.season_format_input = QLineEdit()
        format_layout.addRow("季文件夹格式:", self.season_format_input)
        
        self.help_btn = QPushButton("查看所有可用占位符说明")
        self.help_btn.clicked.connect(self.show_placeholder_help)
        format_layout.addRow(self.help_btn)
        
        format_group.setLayout(format_layout)
        self.layout.addWidget(format_group)

        # --- 2. 正则规则 ---
        regex_group = QGroupBox("正则替换规则 (应用于新文件名)")
        regex_layout = QVBoxLayout()
        self.regex_rules_edit = QPlainTextEdit()
        self.regex_rules_edit.setPlaceholderText("例如: (?i) unwanted => replacement")
        regex_layout.addWidget(self.regex_rules_edit)
        regex_group.setLayout(regex_layout)
        self.layout.addWidget(regex_group)

        # --- 3. 算法管理 ---
        algo_group = QGroupBox("核心算法库管理 (anime-matcher-main)")
        algo_layout = QVBoxLayout()
        self.algo_status_label = QLabel("状态检查中...")
        
        btn_h = QHBoxLayout()
        self.download_btn = QPushButton("自动下载/更新 (GitHub)")
        self.download_btn.clicked.connect(self.download_core_algorithm)
        self.manual_btn = QPushButton("手动部署指引")
        self.manual_btn.clicked.connect(self.show_manual_instructions)
        btn_h.addWidget(self.download_btn)
        btn_h.addWidget(self.manual_btn)
        
        algo_layout.addWidget(self.algo_status_label)
        algo_layout.addLayout(btn_h)
        algo_group.setLayout(algo_layout)
        self.layout.addWidget(algo_group)

        # --- 4. 全局保存 ---
        self.save_btn = QPushButton("保存配置并生效")
        self.save_btn.setFixedHeight(40)
        self.save_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_settings)
        self.layout.addWidget(self.save_btn)
        
        self.layout.addStretch(1)
        self.check_algo_status()

    def check_algo_status(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        core_path = os.path.join(root_dir, "anime-matcher-main")
        if os.path.exists(core_path):
            self.algo_status_label.setText("核心算法状态: <font color='green'>已就绪</font>")
        else:
            self.algo_status_label.setText("核心算法状态: <font color='red'>未找到</font>")

    def download_core_algorithm(self):
        url = "https://github.com/pipi20xx/anime-matcher/archive/refs/heads/main.zip"
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        target_dir = os.path.join(root_dir, "anime-matcher-main")
        
        self.download_btn.setEnabled(False)
        self.dl_worker = DownloadWorker(url, target_dir)
        self.dl_worker.log_signal.connect(lambda m: print(f"[DL] {m}")) # 这里可以连接主窗口日志
        self.dl_worker.finished_signal.connect(self.on_download_finished)
        self.dl_worker.start()

    def on_download_finished(self, success, message):
        self.download_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "成功", message)
            self.check_algo_status()
        else:
            QMessageBox.warning(self, "失败", message)

    def show_placeholder_help(self):
        msg = (
            "<b>可用占位符说明 (全字段对齐):</b><br><br>"
            "<b>基础信息:</b> {title}, {season}, {season_int}, {episode}, {year}, {tmdb_id}<br>"
            "<b>技术规格:</b> {team}, {resolution}, {video_encode}, {video_effect}, {audio_encode}, {subtitle}<br>"
            "<b>高级属性:</b> {source}, {platform}, {category}, {origin_country}, {vote_average}<br>"
            "<b>程序字段:</b> {filename}, {duration}"
        )
        QMessageBox.information(self, "占位符说明", msg)

    def show_manual_instructions(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        msg = f"请手动从 GitHub 下载 ZIP，重命名文件夹为 <b>anime-matcher-main</b> 并放置在以下路径：<br><br><code>{root_dir}</code>"
        QMessageBox.information(self, "手动部署指南", msg)

    def load_settings(self):
        self.rename_format_combo.setCurrentText(config.get_value("rename_format", "{title} - S{season}E{episode} - {filename}"))
        self.folder_format_input.setText(config.get_value("folder_format", "({year}){title}[tmdbid={tmdbid}]"))
        self.season_format_input.setText(config.get_value("season_format", "Season {season_int}"))
        self.regex_rules_edit.setPlainText(config.get_value("regex_rules", ""))

    def save_settings(self):
        config.set_value("rename_format", self.rename_format_combo.currentText())
        config.set_value("folder_format", self.folder_format_input.text())
        config.set_value("season_format", self.season_format_input.text())
        config.set_value("regex_rules", self.regex_rules_edit.toPlainText())
        QMessageBox.information(self, "成功", "设置已保存至本地 SQLite 配置文件。")

    def get_config_data(self):
        """提供给 MainTab 的配置快照"""
        return {
            'rename_format': self.rename_format_combo.currentText(),
            'folder_format': self.folder_format_input.text(),
            'season_format': self.season_format_input.text(),
            'regex_rules': self.parse_regex_rules()
        }

    def parse_regex_rules(self):
        rules = []
        for line in self.regex_rules_edit.toPlainText().splitlines():
            if '=>' in line:
                p, r = line.split('=>', 1)
                rules.append((p.strip(), r.strip()))
        return rules
