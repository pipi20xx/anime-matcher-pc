import os
import datetime
from peewee import *

# 确定数据库路径，放在项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.path.join(ROOT_DIR, "VideoRenamer.db")
db = SqliteDatabase(db_path)

class BaseModel(Model):
    class Meta:
        database = db

class LocalRule(BaseModel):
    """本地自定义规则"""
    # category: 'noise' (屏蔽词), 'group' (制作组), 'render' (渲染重定向)
    category = CharField(index=True)
    content = TextField() # 存储用户输入的多行文本
    enabled = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.now)

class RemoteSubscription(BaseModel):
    """远程订阅源 (例如 GitHub Raw URL)"""
    name = CharField()
    url = CharField()
    category = CharField() # noise, group, render
    enabled = BooleanField(default=True)
    last_updated = DateTimeField(null=True)

class SubscriptionCache(BaseModel):
    """远程订阅内容的本地快照，用于离线加载性能"""
    subscription = ForeignKeyField(RemoteSubscription, backref='caches', on_delete='CASCADE')
    content = TextField() # 存储抓取到的换行符分隔的规则
    updated_at = DateTimeField(default=datetime.datetime.now)

def init_db():
    db.connect()
    db.create_tables([LocalRule, RemoteSubscription, SubscriptionCache])

# 自动初始化
if __name__ == "__main__":
    init_db()
else:
    # 确保在导入时如果表不存在则创建
    db.connect(reuse_if_open=True)
    db.create_tables([LocalRule, RemoteSubscription, SubscriptionCache])
