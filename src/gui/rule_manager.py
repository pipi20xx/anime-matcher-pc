import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QGroupBox, QPlainTextEdit, QScrollArea, QLabel, 
                             QMessageBox, QFrame)
from PyQt6.QtCore import Qt
from src.utils.database import LocalRule, RemoteSubscription
from src.core.rules import RuleManager

class RuleSection(QGroupBox):
    """
    左右结构的规则配置组件。
    左侧：本地规则文本框。
    右侧：远程订阅 URL 文本框。
    """
    def __init__(self, title, category, parent=None):
        super().__init__(title, parent)
        self.category = category
        # 显式设置 QGroupBox 的布局
        self.main_layout = QHBoxLayout(self)

        # --- 左侧：本地规则 ---
        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 5, 0)
        
        self.label_l = QLabel("<b>本地规则</b> (每行一条):")
        self.local_edit = QPlainTextEdit()
        self.local_edit.setPlaceholderText("例如: [Airota]\n关键词1")
        self.local_edit.setMinimumHeight(120)
        
        self.left_layout.addWidget(self.label_l)
        self.left_layout.addWidget(self.local_edit)
        self.main_layout.addWidget(self.left_container, 2) # 权重 2

        # --- 右侧：远程订阅 ---
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(5, 0, 0, 0)
        
        self.label_r = QLabel("<b>远程订阅 URL</b> (每行一个):")
        self.remote_edit = QPlainTextEdit()
        self.remote_edit.setPlaceholderText("https://example.com/rules.txt")
        self.remote_edit.setMinimumHeight(120)
        
        self.sync_btn = QPushButton("同步该类订阅")
        self.sync_btn.setFixedHeight(30)
        self.sync_btn.clicked.connect(self.sync_this_category)
        
        self.right_layout.addWidget(self.label_r)
        self.right_layout.addWidget(self.remote_edit)
        self.right_layout.addWidget(self.sync_btn)
        self.main_layout.addWidget(self.right_container, 1) # 权重 1

    def sync_this_category(self):
        """保存当前分类数据并执行同步"""
        self.save_data()
        subs = RemoteSubscription.select().where(RemoteSubscription.category == self.category)
        if not subs.exists():
            QMessageBox.warning(self, "提示", "请先在右侧填写订阅 URL 地址")
            return
            
        success = 0
        for s in subs:
            ok, _ = RuleManager.sync_subscription(s.id)
            if ok: success += 1
        
        QMessageBox.information(self, "同步完成", f"分类 [{self.category}] 已成功从网络同步 {success} 个源。")

    def load_data(self):
        """从 SQLite 加载数据"""
        # 加载本地
        rule = LocalRule.get_or_none(LocalRule.category == self.category)
        if rule:
            self.local_edit.setPlainText(rule.content)
        
        # 加载远程
        subs = RemoteSubscription.select().where(RemoteSubscription.category == self.category)
        urls = [s.url for s in subs]
        self.remote_edit.setPlainText("\n".join(urls))

    def save_data(self):
        """安全保存数据，修复 NOT NULL 报错"""
        # 1. 保存本地规则
        content = self.local_edit.toPlainText().strip()
        # 使用 defaults 避免 IntegrityError
        rule, created = LocalRule.get_or_create(
            category=self.category, 
            defaults={'content': content}
        )
        if not created:
            rule.content = content
            rule.save()
        
        # 2. 保存远程订阅 URL
        RemoteSubscription.delete().where(RemoteSubscription.category == self.category).execute()
        urls = [line.strip() for line in self.remote_edit.toPlainText().splitlines() if line.strip()]
        for url in urls:
            RemoteSubscription.create(
                name=f"{self.category}_sub", 
                url=url, 
                category=self.category
            )

class RuleManagerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        self.scroll_layout = QVBoxLayout(content_widget)

        # 核心分类：Noise, Group, Privileged, Render
        self.sections = [
            RuleSection("1. 自定义识别词 · 本地与远程 (Noise Filter)", "noise"),
            RuleSection("2. 自定义制作组 · 本地与远程 (Groups Filter)", "group"),
            RuleSection("3. 自定义特权规则 · 本地与远程 (Privileged Rules)", "privileged"),
            RuleSection("4. 自定义渲染规则 · 本地与远程 (Render Rules)", "render")
        ]

        for sec in self.sections:
            self.scroll_layout.addWidget(sec)
            sec.load_data()

        scroll.setWidget(content_widget)
        self.main_layout.addWidget(scroll)

        # 全局保存按钮
        self.save_all_btn = QPushButton("保存所有分类规则并生效")
        self.save_all_btn.setFixedHeight(45)
        self.save_all_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.save_all_btn.clicked.connect(self.save_all_action)
        self.main_layout.addWidget(self.save_all_btn)

    def save_all_action(self):
        for sec in self.sections:
            sec.save_data()
        QMessageBox.information(self, "成功", "所有规则已安全存入本地数据库。")
