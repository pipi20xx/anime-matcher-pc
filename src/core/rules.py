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
            # 使用内容更新缓存
            cache, created = SubscriptionCache.get_or_create(subscription=sub)
            headers = {'User-Agent': 'Mozilla/5.0 (AnimeMatcher-PC)'}
            response = requests.get(sub.url, headers=headers, timeout=15)
            response.raise_for_status()
            
            cache.content = response.text
            cache.updated_at = datetime.datetime.now()
            cache.save()
            
            sub.last_updated = datetime.datetime.now()
            sub.save()
            return True, "同步成功"
        except Exception as e:
            return False, f"同步错误: {str(e)}"

    @staticmethod
    def get_merged_rules(category: str):
        """
        根据分类加载所有本地规则和远程缓存规则并合并。
        返回去重并清理后的列表。
        """
        rules = []
        
        # 1. 加载本地启用规则
        local_rule = LocalRule.get_or_none(LocalRule.category == category, LocalRule.enabled == True)
        if local_rule:
            lines = [line.strip() for line in local_rule.content.splitlines() if line.strip()]
            rules.extend(lines)
            
        # 2. 加载所有该分类下的远程订阅缓存
        subs = RemoteSubscription.select().where(RemoteSubscription.category == category, RemoteSubscription.enabled == True)
        for sub in subs:
            cache = SubscriptionCache.get_or_none(SubscriptionCache.subscription == sub)
            if cache:
                lines = [line.strip() for line in cache.content.splitlines() if line.strip()]
                rules.extend(lines)
        
        # 去重并保持顺序
        return sorted(list(set(rules)))
