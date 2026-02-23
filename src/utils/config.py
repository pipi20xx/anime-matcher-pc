import os
import sys
from PyQt6.QtCore import QSettings

class ConfigManager:
    def __init__(self, filename='VideoRenamer_Qt6.ini'):
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        
        self.config_path = os.path.join(application_path, filename)
        self.settings = QSettings(self.config_path, QSettings.Format.IniFormat)

    def get_value(self, key, default=None, type=None):
        if type:
            return self.settings.value(key, default, type=type)
        return self.settings.value(key, default)

    def set_value(self, key, value):
        self.settings.setValue(key, value)
        self.settings.sync()

    def get_all_settings(self):
        return self.settings

# Global instance
config = ConfigManager()
