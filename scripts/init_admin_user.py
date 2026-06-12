#!/usr/bin/env python3
"""
直接在MongoDB中创建默认管理员用户
"""

import hashlib
from datetime import datetime
from pymongo import MongoClient
import os

def hash_password(password: str) -> str:
    """哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin_user():
    """创建管理员用户"""
    # 从环境变量获取MongoDB连接信息
    mongo_host = os.environ.get("MONGODB_HOST", "mongodb")
    mongo_port = int(os.environ.get("MONGODB_PORT", 27017))
    mongo_user = os.environ.get("MONGODB_USERNAME", "admin")
    mongo_pass = os.environ.get("MONGODB_PASSWORD", "tradingagents123")
    mongo_db = os.environ.get("MONGODB_DATABASE", "tradingagentscn")

    # 连接MongoDB
    mongo_uri = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}/?authSource=admin"
    print(f"📍 连接MongoDB: {mongo_host}:{mongo_port}")

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✅ MongoDB连接成功")
    except Exception as e:
        print(f"❌ MongoDB连接失败: {e}")
        return False

    db = client[mongo_db]
    users_collection = db["users"]

    # 定义默认用户
    default_users = [
        {
            "username": "admin",
            "email": "admin@tradingagents.cn",
            "password": "admin123",
            "is_admin": True
        },
        {
            "username": "user",
            "email": "user@tradingagents.cn",
            "password": "user123",
            "is_admin": False
        }
    ]

    created_count = 0
    for user_info in default_users:
        # 检查用户是否已存在
        existing = users_collection.find_one({"username": user_info["username"]})
        if existing:
            print(f"⚠️  用户 {user_info['username']} 已存在，跳过")
            continue

        # 创建用户文档
        user_doc = {
            "username": user_info["username"],
            "email": user_info["email"],
            "hashed_password": hash_password(user_info["password"]),
            "is_active": True,
            "is_verified": True,
            "is_admin": user_info["is_admin"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None,
            "preferences": {
                "default_market": "A股",
                "default_depth": "3",
                "default_analysts": ["市场分析师", "基本面分析师"],
                "auto_refresh": True,
                "refresh_interval": 30,
                "ui_theme": "light",
                "sidebar_width": 240,
                "language": "zh-CN",
                "notifications_enabled": True,
                "email_notifications": False,
                "desktop_notifications": True,
                "analysis_complete_notification": True,
                "system_maintenance_notification": True
            },
            "daily_quota": 1000,
            "concurrent_limit": 3,
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "favorite_stocks": []
        }

        result = users_collection.insert_one(user_doc)
        print(f"✅ 用户 {user_info['username']} 创建成功 (ID: {result.inserted_id})")
        created_count += 1

    print(f"\n🎉 完成！共创建 {created_count} 个用户")
    if created_count > 0:
        print("\n📋 默认用户信息:")
        print("   - admin / admin123 (管理员)")
        print("   - user / user123 (普通用户)")

    return True

if __name__ == "__main__":
    create_admin_user()
