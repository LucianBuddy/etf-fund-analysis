#!/usr/bin/env python3
"""文件缓存系统。按分类TTL自动过期。"""

import os
import json
import time
import hashlib

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
TTL_CONFIG = {
    "quote": 300,        # 行情: 5分钟
    "fund_data": 3600,   # 基金数据: 1小时
    "holdings": 86400,   # 持仓: 24小时
    "fees": 86400,       # 费率: 24小时
}


def cache_get(key, category="default", ttl=None):
    if ttl is None:
        ttl = TTL_CONFIG.get(category, 600)
    h = hashlib.md5(key.encode()).hexdigest()
    path = os.path.join(CACHE_DIR, category, f"{h}.json")
    try:
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        if time.time() - data.get("ts", 0) > ttl:
            return None
        return data.get("data")
    except:
        return None


def cache_set(key, data, category="default"):
    h = hashlib.md5(key.encode()).hexdigest()
    path = os.path.join(CACHE_DIR, category, f"{h}.json")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"ts": time.time(), "data": data}, f, ensure_ascii=False)
    except:
        pass


def cache_clear(category=None):
    """清除缓存。不传category则清除所有。"""
    if category:
        path = os.path.join(CACHE_DIR, category)
        if os.path.exists(path):
            import shutil
            shutil.rmtree(path)
    else:
        if os.path.exists(CACHE_DIR):
            import shutil
            shutil.rmtree(CACHE_DIR)
