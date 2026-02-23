import requests
import datetime
import traceback
from src.utils.database import LocalRule, RemoteSubscription, SubscriptionCache

class RuleManager:
    """管理规则的同步与合并逻辑"""
    @staticmethod
    def sync_subscription(sub_id):
        """同步指定的远程订阅源"""
        try:
            sub = RemoteSubscription.get_by_id(sub_id)
            headers = {'User-Agent': 'Mozilla/5.0 (AnimeMatcher-PC)'}
            
            # 先下载内容
            response = requests.get(sub.url, headers=headers, timeout=15)
            response.raise_for_status()
            content = response.text
            
            # 使用内容更新或创建缓存 (修复 NOT NULL 报错)
            cache, created = SubscriptionCache.get_or_create(
                subscription=sub,
                defaults={'content': content}
            )
            if not created:
                cache.content = content
                cache.updated_at = datetime.datetime.now()
                cache.save()
            
            sub.last_updated = datetime.datetime.now()
            sub.save()
            return True, "同步成功"
        except Exception as e:
            err_msg = str(e)
            return False, err_msg

    @staticmethod
    def get_merged_rules(category: str):
        """根据分类加载合并后的规则列表"""
        rules = []
        
        # 1. 加载本地规则
        local_rule = LocalRule.get_or_none(LocalRule.category == category, LocalRule.enabled == True)
        if local_rule:
            lines = [line.strip() for line in local_rule.content.splitlines() if line.strip()]
            rules.extend(lines)
            
        # 2. 加载该分类下所有远程缓存内容
        subs = RemoteSubscription.select().where(RemoteSubscription.category == category, RemoteSubscription.enabled == True)
        for sub in subs:
            cache = SubscriptionCache.get_or_none(SubscriptionCache.subscription == sub)
            if cache:
                lines = [line.strip() for line in cache.content.splitlines() if line.strip()]
                rules.extend(lines)
        
        return sorted(list(set(rules)))
