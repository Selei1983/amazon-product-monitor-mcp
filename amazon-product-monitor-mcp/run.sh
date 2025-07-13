#!/bin/sh
# Amazon Product Monitor MCP Server - STDIO 模式启动脚本
set -e

# 更改到脚本目录
cd "$(dirname "$0")"

# 创建独立虚拟环境（如果不存在）
if [ ! -d ".venv" ]; then
    echo "正在创建虚拟环境..." >&2
    uv venv
    echo "正在安装依赖..." >&2
    echo "注意：依赖安装可能需要几分钟时间，请耐心等待..." >&2
    uv sync
fi

# 检查必要的环境变量
if [ -n "$SENDER_EMAIL" ] && [ -n "$SENDER_PASSWORD" ]; then
    echo "检测到邮件配置，邮件功能已启用" >&2
else
    echo "警告：未设置 SENDER_EMAIL 和 SENDER_PASSWORD 环境变量" >&2
    echo "邮件发送功能将不可用，请在使用邮件功能前设置相关环境变量" >&2
fi

# 启动 STDIO 模式 MCP 服务器
echo "启动 Amazon Product Monitor MCP Server..." >&2
uv run server.py
