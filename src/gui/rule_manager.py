import os
import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QGroupBox, QPlainTextEdit, QScrollArea, QLabel, 
                             QMessageBox, QFrame)
from PyQt6.QtCore import Qt
from src.utils.database import LocalRule, RemoteSubscription, SubscriptionCache, db
from src.core.rules import RuleManager

class RuleSection(QGroupBox):
    def __init__(self, title, category, parent=None):
        super().__init__(title, parent)
        self.category = category.strip().lower()
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 15, 10, 10)
        self.main_layout.setSpacing(10)

        # 左侧：本地
        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.local_edit = QPlainTextEdit()
        self.local_edit.setPlaceholderText("本地规则 (每行一条)...")
        self.local_edit.setMinimumHeight(150)
        self.left_layout.addWidget(QLabel("<b>本地规则</b>:"))
        self.left_layout.addWidget(self.local_edit)
        self.main_layout.addWidget(self.left_container, 2) 

        # 右侧：远程
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.remote_edit = QPlainTextEdit()
        self.remote_edit.setPlaceholderText("订阅 URL (每行一个)...")
        self.remote_edit.setMinimumHeight(150)
        self.sync_btn = QPushButton("同步该类订阅")
        self.sync_btn.clicked.connect(self.sync_this_category)
        self.right_layout.addWidget(QLabel("<b>远程订阅</b>:"))
        self.right_layout.addWidget(self.remote_edit)
        self.right_layout.addWidget(self.sync_btn)
        self.main_layout.addWidget(self.right_container, 1) 

        self.main_layout.setStretch(0, 2)
        self.main_layout.setStretch(1, 1)

    def sync_this_category(self):
        self.save_data()
        subs = RemoteSubscription.select().where(RemoteSubscription.category == self.category)
        if not subs.exists():
            QMessageBox.warning(self, "提示", "请先填入订阅地址")
            return
        success = 0
        for s in subs:
            ok, _ = RuleManager.sync_subscription(s.id)
            if ok: success += 1
        QMessageBox.information(self, "同步完成", f"已成功同步 {success} 个源。")
        self.load_data()

    def load_data(self):
        rule = LocalRule.get_or_none(category=self.category)
        if rule: self.local_edit.setPlainText(rule.content)
        
        subs = RemoteSubscription.select().where(RemoteSubscription.category == self.category)
        self.remote_edit.setPlainText("\n".join([s.url for s in subs]))

    def save_data(self):
        """增量保存逻辑，防止缓存被误删"""
        local_text = self.local_edit.toPlainText().strip()
        new_urls = [line.strip() for line in self.remote_edit.toPlainText().splitlines() if line.strip()]
        
        with db.atomic():
            # 1. 本地规则
            rule, _ = LocalRule.get_or_create(category=self.category)
            rule.content = local_text
            rule.updated_at = datetime.datetime.now()
            rule.save()
            
            # 2. 远程订阅：增量处理
            existing_subs = {s.url: s for s in RemoteSubscription.select().where(RemoteSubscription.category == self.category)}
            
            # 删除不再需要的
            for url, sub_obj in existing_subs.items():
                if url not in new_urls:
                    sub_obj.delete_instance(recursive=True)
            
            # 添加新增的
            for url in new_urls:
                if url not in existing_subs:
                    RemoteSubscription.create(name=f"{self.category}_sub", url=url, category=self.category)
        
        print(f"[DEBUG] 分类 {self.category} 已保存。")

class RuleManagerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        self.scroll_layout = QVBoxLayout(content_widget)

        self.sections = [
            RuleSection("1. 自定义识别词 (Noise)", "noise"),
            RuleSection("2. 自定义制作组 (Group)", "group"),
            RuleSection("3. 自定义特权规则 (Privileged)", "privileged"),
            RuleSection("4. 自定义渲染规则 (Render)", "render")
        ]

        for sec in self.sections:
            self.scroll_layout.addWidget(sec)
            sec.load_data()

        scroll.setWidget(content_widget)
        self.main_layout.addWidget(scroll)

        self.save_all_btn = QPushButton("保存所有规则配置")
        self.save_all_btn.setFixedHeight(50)
        self.save_all_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.save_all_btn.clicked.connect(self.save_all_action)
        self.main_layout.addWidget(self.save_all_btn)

    def save_all_action(self):
        for sec in self.sections:
            sec.save_data()
        QMessageBox.information(self, "成功", "设置已保存。如果添加了新订阅，请点击各分类下的“同步”按钮。")
