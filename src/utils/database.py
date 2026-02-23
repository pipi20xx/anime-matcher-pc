import os
import datetime
from peewee import *
from src.utils.paths import DB_PATH

db = SqliteDatabase(DB_PATH)

class BaseModel(Model):
    class Meta: database = db

class LocalRule(BaseModel):
    category = CharField(index=True)
    content = TextField()
    enabled = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.now)

class RemoteSubscription(BaseModel):
    name = CharField(); url = CharField(); category = CharField()
    enabled = BooleanField(default=True); last_updated = DateTimeField(null=True)

class SubscriptionCache(BaseModel):
    subscription = ForeignKeyField(RemoteSubscription, backref='caches', on_delete='CASCADE')
    content = TextField(); updated_at = DateTimeField(default=datetime.datetime.now)

def init_db():
    db.connect(reuse_if_open=True)
    db.create_tables([LocalRule, RemoteSubscription, SubscriptionCache])

init_db()
