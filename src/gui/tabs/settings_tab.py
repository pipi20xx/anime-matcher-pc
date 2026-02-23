import os
import sqlite3
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, 
                             QLineEdit, QComboBox, QPlainTextEdit, QPushButton, 
                             QLabel, QMessageBox, QHBoxLayout, QCheckBox, QScrollArea, QFrame)
from PyQt6.QtCore import Qt
from src.utils.config import config
from src.utils.downloader import DownloadWorker
from src.utils.paths import APP_ROOT, CORE_ALGO_DIR, CORE_DB_PATH

class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.main_layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)
        
        self.init_ui()
        self.load_settings()
        
        scroll.setWidget(content_widget)
        self.main_layout.addWidget(scroll)

    def init_ui(self):
        # 1. 格式
        format_group = QGroupBox("重命名格式设置")
        format_layout = QFormLayout()
        self.rename_format_combo = QComboBox()
        self.rename_format_combo.addItems([
            "[{team}] {title} - S{season_02}E{episode_02} [{resolution}][{video_encode}][{subtitle}]",
            "{title} ({year}) - S{season_02}E{episode_02} [{resolution}]",
            "{title} - S{season_02}E{episode_02} - {filename}"
        ])
        self.rename_format_combo.setEditable(True)
        format_layout.addRow("文件名格式:", self.rename_format_combo)
        self.folder_format_input = QLineEdit()
        format_layout.addRow("主文件夹格式:", self.folder_format_input)
        self.season_format_input = QLineEdit()
        format_layout.addRow("季文件夹格式:", self.season_format_input)
        format_group.setLayout(format_layout)
        self.layout.addWidget(format_group)

        # 2. 联网
        net_group = QGroupBox("联网匹配设置 (TMDB / Bangumi)")
        net_layout = QFormLayout()
        self.with_cloud_cb = QCheckBox("开启云端联动 (获取准确官方标题)"); self.with_cloud_cb.setChecked(True)
        net_layout.addRow(self.with_cloud_cb)
        self.tmdb_api_key_input = QLineEdit(); net_layout.addRow("TMDB API Key:", self.tmdb_api_key_input)
        self.tmdb_proxy_input = QLineEdit(); net_layout.addRow("TMDB 代理:", self.tmdb_proxy_input)
        self.bangumi_token_input = QLineEdit(); net_layout.addRow("Bangumi Token:", self.bangumi_token_input)
        self.bangumi_proxy_input = QLineEdit(); net_layout.addRow("Bangumi 代理:", self.bangumi_proxy_input)
        self.use_storage_cb = QCheckBox("开启智能记忆 (SQLite 缓存)"); self.use_storage_cb.setChecked(True)
        net_layout.addRow(self.use_storage_cb)
        strat_layout = QHBoxLayout()
        self.anime_priority_cb = QCheckBox("动漫优化"); self.bgm_failover_cb = QCheckBox("Bgm 故障转移")
        strat_layout.addWidget(self.anime_priority_cb); strat_layout.addWidget(self.bgm_failover_cb)
        net_layout.addRow("匹配策略:", strat_layout)
        net_group.setLayout(net_layout)
        self.layout.addWidget(net_group)

        # 3. 数据库
        db_group = QGroupBox("缓存与持久化管理")
        db_layout = QHBoxLayout()
        self.clear_cache_btn = QPushButton("清理元数据缓存"); self.clear_cache_btn.clicked.connect(lambda: self.clear_core_db_table("metadata_cache"))
        self.clear_memory_btn = QPushButton("清理识别指纹记忆"); self.clear_memory_btn.clicked.connect(lambda: self.clear_core_db_table("recognition_memory"))
        db_layout.addWidget(self.clear_cache_btn); db_layout.addWidget(self.clear_memory_btn)
        db_group.setLayout(db_layout); self.layout.addWidget(db_group)

        # 4. 算法库管理
        algo_group = QGroupBox("核心算法库管理 (anime-matcher-main)")
        algo_layout = QVBoxLayout()
        self.algo_status_label = QLabel("正在检查状态...")
        btn_h = QHBoxLayout()
        self.download_btn = QPushButton("自动下载/更新 (GitHub)"); self.download_btn.clicked.connect(self.download_core_algorithm)
        self.manual_btn = QPushButton("手动部署指引"); self.manual_btn.clicked.connect(self.show_manual_instructions)
        btn_h.addWidget(self.download_btn); btn_h.addWidget(self.manual_btn)
        algo_layout.addWidget(self.algo_status_label); algo_layout.addLayout(btn_h)
        algo_group.setLayout(algo_layout)
        self.layout.addWidget(algo_group)

        # 5. 噪声规则
        regex_group = QGroupBox("路径噪声清洗 (正则替换)")
        r_layout = QVBoxLayout()
        self.regex_rules_edit = QPlainTextEdit(); self.regex_rules_edit.setPlaceholderText("(?i) unwanted => replacement")
        r_layout.addWidget(self.regex_rules_edit); regex_group.setLayout(r_layout)
        self.layout.addWidget(regex_group)

        # 6. 保存
        self.save_btn = QPushButton("保存所有配置并生效"); self.save_btn.setFixedHeight(45)
        self.save_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_settings)
        self.layout.addWidget(self.save_btn)
        
        self.check_algo_status()

    def check_algo_status(self):
        if os.path.exists(CORE_ALGO_DIR):
            self.algo_status_label.setText("核心算法状态: 已就绪")
            self.algo_status_label.setStyleSheet("color: white; background-color: green; font-weight: bold; border-radius: 3px; padding: 2px;")
        else:
            self.algo_status_label.setText("核心算法状态: 未找到")
            self.algo_status_label.setStyleSheet("color: white; background-color: red; font-weight: bold; border-radius: 3px; padding: 2px;")

    def show_manual_instructions(self):
        msg = (
            "<b>手动部署说明:</b><br><br>"
            "1. 访问 GitHub 项目页下载 ZIP。<br>"
            "2. 解压并重命名文件夹为 <b>anime-matcher-main</b>。<br>"
            "3. 将其移动到程序根目录：<br>"
            f"<code style='color:blue'>{APP_ROOT}</code>"
        )
        QMessageBox.information(self, "手动指引", msg)

    def download_core_algorithm(self):
        url = "https://github.com/pipi20xx/anime-matcher/archive/refs/heads/main.zip"
        self.download_btn.setEnabled(False)
        self.dl_worker = DownloadWorker(url, CORE_ALGO_DIR)
        self.dl_worker.finished_signal.connect(self.on_download_finished)
        self.dl_worker.start()

    def on_download_finished(self, success, message):
        self.download_btn.setEnabled(True)
        if success: self.check_algo_status()
        QMessageBox.information(self, "结果", message)

    def clear_core_db_table(self, table_name):
        if not os.path.exists(CORE_DB_PATH):
            QMessageBox.warning(self, "提示", "数据库文件尚未生成。")
            return
        if QMessageBox.question(self, '确认清理', f"确定清理核心缓存表 [{table_name}] 吗？") == QMessageBox.StandardButton.Yes:
            try:
                conn = sqlite3.connect(CORE_DB_PATH); cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {table_name}"); conn.commit(); conn.close()
                QMessageBox.information(self, "成功", "清理完成。")
            except Exception as e: QMessageBox.warning(self, "错误", str(e))

    def load_settings(self):
        self.rename_format_combo.setCurrentText(config.get_value("rename_format", "[{team}] {title} - S{season_02}E{episode_02}"))
        self.folder_format_input.setText(config.get_value("folder_format", "({year}){title}[tmdbid={tmdb_id}]"))
        self.season_format_input.setText(config.get_value("season_format", "Season {season}"))
        self.regex_rules_edit.setPlainText(config.get_value("regex_rules", ""))
        self.with_cloud_cb.setChecked(config.get_value("with_cloud", True, type=bool))
        self.tmdb_api_key_input.setText(config.get_value("tmdb_api_key", ""))
        self.tmdb_proxy_input.setText(config.get_value("tmdb_proxy", ""))
        self.bangumi_token_input.setText(config.get_value("bangumi_token", ""))
        self.bangumi_proxy_input.setText(config.get_value("bangumi_proxy", ""))
        self.use_storage_cb.setChecked(config.get_value("use_storage", True, type=bool))
        self.anime_priority_cb.setChecked(config.get_value("anime_priority", True, type=bool))
        self.bgm_failover_cb.setChecked(config.get_value("bgm_failover", True, type=bool))

    def save_settings(self):
        config.set_value("rename_format", self.rename_format_combo.currentText())
        config.set_value("folder_format", self.folder_format_input.text())
        config.set_value("season_format", self.season_format_input.text())
        config.set_value("regex_rules", self.regex_rules_edit.toPlainText())
        config.set_value("with_cloud", self.with_cloud_cb.isChecked())
        config.set_value("tmdb_api_key", self.tmdb_api_key_input.text().strip())
        config.set_value("tmdb_proxy", self.tmdb_proxy_input.text().strip())
        config.set_value("bangumi_token", self.bangumi_token_input.text().strip())
        config.set_value("bangumi_proxy", self.bangumi_proxy_input.text().strip())
        config.set_value("use_storage", self.use_storage_cb.isChecked())
        config.set_value("anime_priority", self.anime_priority_cb.isChecked())
        config.set_value("bgm_failover", self.bgm_failover_cb.isChecked())
        QMessageBox.information(self, "成功", "设置已保存。")

    def get_config_data(self):
        return {
            'rename_format': self.rename_format_combo.currentText(),
            'folder_format': self.folder_format_input.text(),
            'season_format': self.season_format_input.text(),
            'regex_rules': self.parse_regex_rules(),
            'with_cloud': self.with_cloud_cb.isChecked(),
            'tmdb_api_key': self.tmdb_api_key_input.text().strip(),
            'tmdb_proxy': self.tmdb_proxy_input.text().strip(),
            'bangumi_token': self.bangumi_token_input.text().strip(),
            'bangumi_proxy': self.bangumi_proxy_input.text().strip(),
            'use_storage': self.use_storage_cb.isChecked(),
            'anime_priority': self.anime_priority_cb.isChecked(),
            'bgm_failover': self.bgm_failover_cb.isChecked()
        }

    def parse_regex_rules(self):
        rules = []
        for line in self.regex_rules_edit.toPlainText().splitlines():
            if '=>' in line:
                p, r = line.split('=>', 1); rules.append((p.strip(), r.strip()))
        return rules
