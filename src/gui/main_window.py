import os
import sys
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QApplication
from PyQt6.QtCore import Qt
from src.gui.tabs.main_tab import MainTab
from src.gui.tabs.settings_tab import SettingsTab
from src.gui.rule_manager import RuleManagerWidget

class VideoRenamerGUI(QMainWindow):
    """
    主窗口 Shell。
    负责：页签组装、全局拖拽分发、窗口基础设置。
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("剧集视频重命名工具 (Anime-Matcher Core) - PyQt6")
        self.setGeometry(100, 100, 1400, 900)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 1. 初始化 Tab 容器
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        
        # 2. 实例化各个解耦后的组件
        self.main_tab = MainTab(self)
        self.rule_tab = RuleManagerWidget()
        self.settings_tab = SettingsTab(self)
        
        # 3. 添加页签
        self.tab_widget.addTab(self.main_tab, "主界面")
        self.tab_widget.addTab(self.rule_tab, "识别规则管理")
        self.tab_widget.addTab(self.settings_tab, "设置与算法")
        
        # 4. 开启全局拖拽接受
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = [u.toString() for u in event.mimeData().urls()]
            # 自动分发给主界面组件处理
            self.main_tab.add_paths_to_list(urls)
            # 自动跳转到主界面 Tab
            self.tab_widget.setCurrentIndex(0)
            event.acceptProposedAction()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoRenamerGUI()
    window.show()
    sys.exit(app.exec())
