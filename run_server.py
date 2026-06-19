#!/usr/bin/env python3
"""
服务器启动脚本
必须在 uvicorn 创建事件循环之前应用 nest_asyncio
"""

# 🔧 关键：必须在导入 uvicorn 之前应用 nest_asyncio
# 因为 uvicorn 会在导入时就准备事件循环相关的代码
import nest_asyncio
nest_asyncio.apply()

import uvicorn
import os

if __name__ == "__main__":
    # 从环境变量读取配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    print(f"🚀 Starting server with nest_asyncio applied...")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Debug: {debug}")

    # Docker 容器中不使用 reload，避免无限重载循环
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
