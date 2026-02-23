import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, 
                             QLineEdit, QComboBox, QPlainTextEdit, QPushButton, 
                             QLabel, QMessageBox, QHBoxLayout, QCheckBox, QScrollArea, QFrame)
from PyQt6.QtCore import Qt
from src.utils.config import config
from src.utils.downloader import DownloadWorker

class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.main_layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self.layout = QVBoxLayout(content)
        
        self.init_ui()
        self.load_settings()
        
        scroll.setWidget(content)
        self.main_layout.addWidget(scroll)

    def init_ui(self):
        # --- 1. 重命名格式 ---
        format_group = QGroupBox("重命名格式设置")
        format_layout = QFormLayout()
        self.rename_format_combo = QComboBox()
        self.rename_format_combo.addItems([
            "[{team}] {title} - S{season}E{episode} [{resolution}][{video_encode}][{subtitle}]",
            "{title} ({year}) - S{season}E{episode} [{resolution}]",
            "{title} - S{season}E{episode} - {filename}"
        ])
        self.rename_format_combo.setEditable(True)
        format_layout.addRow("文件名格式:", self.rename_format_combo)
        self.folder_format_input = QLineEdit()
        format_layout.addRow("主文件夹格式:", self.folder_format_input)
        self.season_format_input = QLineEdit()
        format_layout.addRow("季文件夹格式:", self.season_format_input)
        format_group.setLayout(format_layout)
        self.layout.addWidget(format_group)

        # --- 2. 联网匹配设置 (L2 Cloud) ---
        net_group = QGroupBox("联网匹配设置 (TMDB / Bangumi)")
        net_layout = QFormLayout()
        
        self.with_cloud_cb = QCheckBox("开启云端联动 (从网络获取标准标题)")
        self.with_cloud_cb.setChecked(True)
        net_layout.addRow(self.with_cloud_cb)
        
        # TMDB
        self.tmdb_api_key_input = QLineEdit()
        self.tmdb_api_key_input.setPlaceholderText("TMDB API Key (v3)")
        net_layout.addRow("TMDB API Key:", self.tmdb_api_key_input)
        
        self.tmdb_proxy_input = QLineEdit()
        self.tmdb_proxy_input.setPlaceholderText("例如: http://127.0.0.1:7890")
        net_layout.addRow("TMDB 代理地址:", self.tmdb_proxy_input)

        # Bangumi
        self.bangumi_token_input = QLineEdit()
        self.bangumi_token_input.setPlaceholderText("Bangumi 个人访问令牌 (可选)")
        net_layout.addRow("Bangumi Token:", self.bangumi_token_input)

        self.bangumi_proxy_input = QLineEdit()
        self.bangumi_proxy_input.setPlaceholderText("例如: http://127.0.0.1:7890")
        net_layout.addRow("Bangumi 代理:", self.bangumi_proxy_input)
        
        self.use_storage_cb = QCheckBox("开启智能记忆 (基于指纹自动锁定 ID)")
        self.use_storage_cb.setChecked(True)
        net_layout.addRow(self.use_storage_cb)
        
        strat_layout = QHBoxLayout()
        self.anime_priority_cb = QCheckBox("动漫优化")
        self.bgm_failover_cb = QCheckBox("Bgm 故障转移")
        strat_layout.addWidget(self.anime_priority_cb)
        strat_layout.addWidget(self.bgm_failover_cb)
        net_layout.addRow("匹配策略:", strat_layout)
        
        net_group.setLayout(net_layout)
        self.layout.addWidget(net_group)

        # --- 3. 缓存与数据库管理 ---
        db_group = QGroupBox("缓存与持久化管理")
        db_layout = QVBoxLayout()
        
        db_info_label = QLabel("管理核心算法生成的本地缓存与识别记忆 (matcher_storage.db)")
        db_layout.addWidget(db_info_label)
        
        db_btn_layout = QHBoxLayout()
        self.clear_cache_btn = QPushButton("清理元数据缓存")
        self.clear_cache_btn.clicked.connect(lambda: self.clear_core_db_table("metadata_cache"))
        self.clear_memory_btn = QPushButton("清理识别指纹记忆")
        self.clear_memory_btn.clicked.connect(lambda: self.clear_core_db_table("recognition_memory"))
        db_btn_layout.addWidget(self.clear_cache_btn)
        db_btn_layout.addWidget(self.clear_memory_btn)
        db_layout.addLayout(db_btn_layout)
        
        db_group.setLayout(db_layout)
        self.layout.addWidget(db_group)

        # --- 4. 正则规则 ---
        regex_group = QGroupBox("路径噪声清洗 (正则替换)")
        regex_layout = QVBoxLayout()
        self.regex_rules_edit = QPlainTextEdit()
        self.regex_rules_edit.setPlaceholderText("(?i) unwanted => replacement")
        regex_layout.addWidget(self.regex_rules_edit)
        regex_group.setLayout(regex_layout)
        self.layout.addWidget(regex_group)

        # --- 5. 算法库 ---
        algo_group = QGroupBox("算法内核管理")
        algo_layout = QVBoxLayout()
        self.algo_status_label = QLabel("检查中...")
        btn_h = QHBoxLayout()
        self.download_btn = QPushButton("下载/更新内核"); self.download_btn.clicked.connect(self.download_core_algorithm)
        self.help_btn = QPushButton("占位符帮助"); self.help_btn.clicked.connect(self.show_placeholder_help)
        btn_h.addWidget(self.download_btn); btn_h.addWidget(self.help_btn)
        algo_layout.addWidget(self.algo_status_label); algo_layout.addLayout(btn_h)
        algo_group.setLayout(algo_layout)
        self.layout.addWidget(algo_group)

        # 全局保存
        self.save_btn = QPushButton("保存配置并应用")
        self.save_btn.setFixedHeight(45)
        self.save_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_settings)
        self.layout.addWidget(self.save_btn)
        
        self.check_algo_status()

    def clear_core_db_table(self, table_name):
        """定位核心算法数据库并执行清理"""
        import sqlite3
        # 1. 定位项目根目录 (从 src/gui/tabs/ 向上跳 4 层)
        # settings_tab.py -> tabs -> gui -> src -> root
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_path = os.path.join(root_dir, "data", "matcher_storage.db")
        
        # 调试日志，方便在控制台确认路径
        print(f"[DEBUG] 尝试清理数据库路径: {db_path}")
        
        if not os.path.exists(db_path):
            QMessageBox.warning(self, "提示", f"数据库文件尚未生成或不存在:\n{db_path}")
            return

        reply = QMessageBox.question(self, '确认清理', f"确定要永久删除核心数据库中 {table_name} 表的所有数据吗？",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {table_name}")
                conn.commit()
                conn.close()
                QMessageBox.information(self, "成功", f"核心缓存表 [{table_name}] 已清空。")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"清理失败: {str(e)}")

    def check_algo_status(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if os.path.exists(os.path.join(root_dir, "anime-matcher-main")):
            self.algo_status_label.setText("核心算法状态: <font color='green'>已就绪</font>")
        else:
            self.algo_status_label.setText("核心算法状态: <font color='red'>未找到</font>")

    def download_core_algorithm(self):
        url = "https://github.com/pipi20xx/anime-matcher/archive/refs/heads/main.zip"
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        target_dir = os.path.join(root_dir, "anime-matcher-main")
        self.download_btn.setEnabled(False)
        self.dl_worker = DownloadWorker(url, target_dir)
        self.dl_worker.finished_signal.connect(self.on_download_finished)
        self.dl_worker.start()

    def on_download_finished(self, success, message):
        self.download_btn.setEnabled(True)
        if success: self.check_algo_status()
        QMessageBox.information(self, "下载结果", message)

    def show_placeholder_help(self):
        msg = "<b>常用占位符:</b> {title}, {season}, {episode}, {year}, {team}, {resolution}, {video_encode}, {subtitle}"
        QMessageBox.information(self, "帮助", msg)

    def load_settings(self):
        self.rename_format_combo.setCurrentText(config.get_value("rename_format", "[{team}] {title} - S{season}E{episode}"))
        self.folder_format_input.setText(config.get_value("folder_format", "({year}){title}[tmdbid={tmdbid}]"))
        self.season_format_input.setText(config.get_value("season_format", "Season {season_int}"))
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
        
        QMessageBox.information(self, "成功", "设置已保存并同步。")

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
                p, r = line.split('=>', 1)
                rules.append((p.strip(), r.strip()))
        return rules
