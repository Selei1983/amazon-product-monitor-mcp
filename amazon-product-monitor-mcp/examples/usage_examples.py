#!/usr/bin/env python3
"""
Amazon Product Monitor MCP Server 使用示例

本文件展示了如何使用 Amazon 商品监控 MCP 服务器的各种功能。
"""

import asyncio
import json
from datetime import datetime
from fastmcp import Client
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent.parent))

from server import mcp


async def example_basic_search():
    """基本商品搜索示例"""
    print("✨ 基本商品搜索示例")
    print("=" * 50)
    
    async with Client(mcp) as client:
        # 搜索游戏笔记本
        print("🔍 正在搜索 'gaming laptop'...")
        result = await client.call_tool(
            "search_amazon_products",
            {
                "keyword": "gaming laptop",
                "category": "Electronics",
                "max_pages": 2
            }
        )
        
        print(f"✅ 搜索完成！找到 {result.content[0].get('total_products', 0)} 个商品")
        
        # 显示前 3 个商品
        products = result.content[0].get('products', [])
        for i, product in enumerate(products[:3], 1):
            print(f"\n{i}. {product.get('title', 'N/A')[:80]}...")
            print(f"   💰 价格: ${product.get('price', 'N/A')}")
            print(f"   ⭐ 评分: {product.get('rating', 'N/A')}/5.0")
            print(f"   💬 评论: {product.get('review_count', 'N/A')}")
        
        return result.content[0]


async def example_product_analysis(products_data):
    """商品分析示例"""
    print("\n\n📊 商品分析示例")
    print("=" * 50)
    
    async with Client(mcp) as client:
        # 分析商品数据
        print("🤖 正在分析商品数据...")
        result = await client.call_tool(
            "analyze_products",
            {"products_data": json.dumps(products_data)}
        )
        
        analysis = result.content[0]
        print(f"✅ 分析完成！")
        
        # 显示分析结果
        print(f"\n📊 分析摘要:")
        print(f"   总商品数: {analysis.get('total_products', 0)}")
        print(f"   有效商品数: {analysis.get('valid_products', 0)}")
        
        # 最佳评分商品
        best_rated = analysis.get('best_rated')
        if best_rated:
            print(f"\n⭐ 最佳评分商品:")
            print(f"   {best_rated.get('title', 'N/A')[:60]}...")
            print(f"   评分: {best_rated.get('rating', 'N/A')}/5.0")
            print(f"   评论数: {best_rated.get('review_count', 'N/A')}")
        
        # 最高折扣商品
        most_discounted = analysis.get('most_discounted')
        if most_discounted:
            print(f"\n💰 最高折扣商品:")
            print(f"   {most_discounted.get('title', 'N/A')[:60]}...")
            print(f"   价格: ${most_discounted.get('price', 'N/A')}")
            print(f"   估计折扣: {most_discounted.get('discount_percentage', 0):.1f}%")
        
        # 最佳销量商品
        best_seller = analysis.get('best_seller')
        if best_seller:
            print(f"\n🔥 最佳销量商品:")
            print(f"   {best_seller.get('title', 'N/A')[:60]}...")
            print(f"   评论数: {best_seller.get('review_count', 'N/A')}")
            print(f"   评分: {best_seller.get('rating', 'N/A')}/5.0")
        
        return analysis


async def example_markdown_report(analysis_data):
    """生成 Markdown 报告示例"""
    print("\n\n📝 Markdown 报告生成示例")
    print("=" * 50)
    
    async with Client(mcp) as client:
        # 生成 Markdown 报告
        print("📜 正在生成 Markdown 报告...")
        result = await client.call_tool(
            "generate_markdown_report",
            {
                "analysis_result": json.dumps(analysis_data),
                "keyword": "gaming laptop"
            }
        )
        
        print("✅ Markdown 报告生成完成！")
        
        # 保存报告到文件
        report_path = Path("examples/sample_report.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(result.content)
        
        print(f"💾 报告已保存到: {report_path}")
        
        # 显示报告片段
        lines = result.content.split('\n')
        print("\n👀 报告预览 (前 15 行):")
        for line in lines[:15]:
            print(f"   {line}")
        print("   ...")
        
        return result.content


async def example_complete_analysis():
    """完整分析流程示例"""
    print("\n\n🚀 完整分析流程示例")
    print("=" * 50)
    
    async with Client(mcp) as client:
        # 一键运行完整分析
        print("🎆 正在运行完整分析流程...")
        result = await client.call_tool(
            "run_complete_analysis",
            {
                "keyword": "wireless headphones",
                "category": "Electronics",
                "max_pages": 2
            }
        )
        
        if result.content[0].get('success'):
            print("✅ 完整分析流程成功！")
            
            search_result = result.content[0]['search_result']
            analysis_result = result.content[0]['analysis_result']
            
            print(f"\n📊 结果概览:")
            print(f"   搜索关键词: {search_result.get('keyword')}")
            print(f"   找到商品: {search_result.get('total_products', 0)} 个")
            print(f"   有效商品: {analysis_result.get('valid_products', 0)} 个")
            
            # 显示简要分析
            summary = analysis_result.get('analysis_summary', '')
            if summary:
                print(f"\n📈 分析摘要:")
                for line in summary.split('\n')[:3]:  # 只显示前 3 行
                    if line.strip():
                        print(f"   {line.strip()}")
            
            return result.content[0]
        else:
            print(f"❌ 完整分析失败: {result.content[0].get('error')}")
            return None


async def example_monitor_management():
    """监控管理示例"""
    print("\n\n⏰ 监控管理示例")
    print("=" * 50)
    
    async with Client(mcp) as client:
        # 创建监控任务
        print("🎆 创建新的监控任务...")
        create_result = await client.call_tool(
            "create_product_monitor",
            {
                "keyword": "mechanical keyboard",
                "category": "Electronics",
                "email": "user@example.com",
                "frequency": "daily"
            }
        )
        
        if create_result.content[0].get('success'):
            monitor_id = create_result.content[0]['monitor_id']
            print(f"✅ 监控任务创建成功！ID: {monitor_id}")
            
            # 列出所有监控
            print("\n📜 列出所有监控任务...")
            list_result = await client.call_tool("list_product_monitors", {})
            
            monitors = list_result.content[0].get('monitors', [])
            print(f"✅ 找到 {len(monitors)} 个监控任务")
            
            for i, monitor in enumerate(monitors[-3:], 1):  # 显示最后 3 个
                print(f"\n   {i}. 监控 ID: {monitor.get('id')}")
                print(f"      关键词: {monitor.get('keyword')}")
                print(f"      类别: {monitor.get('category')}")
                print(f"      频率: {monitor.get('frequency')}")
                print(f"      状态: {'\u2705 活跃' if monitor.get('active') else '\u274c 禁用'}")
            
            # 模拟运行监控（不发送邮件）
            print(f"\n🏃 正在运行监控任务 {monitor_id}...")
            run_result = await client.call_tool(
                "run_product_monitor",
                {
                    "monitor_id": monitor_id,
                    "sender_email": "",  # 不发送邮件
                    "sender_password": ""
                }
            )
            
            if run_result.content[0].get('success'):
                print(f"✅ 监控运行成功！")
                result = run_result.content[0]
                print(f"   搜索关键词: {result.get('keyword')}")
                print(f"   找到商品: {result.get('products_found', 0)} 个")
                print(f"   邮件发送: {'\u2705 成功' if result.get('email_sent') else '\u274c 未发送'}")
            else:
                print(f"❌ 监控运行失败: {run_result.content[0].get('error')}")
            
            # 清理测试监控
            print(f"\n🧹 清理测试监控...")
            remove_result = await client.call_tool(
                "remove_product_monitor",
                {"monitor_id": monitor_id}
            )
            
            if remove_result.content[0].get('success'):
                print(f"✅ 监控任务删除成功")
            
            return monitors
        else:
            print(f"❌ 监控创建失败: {create_result.content[0].get('error')}")
            return []


async def example_email_simulation():
    """邮件发送模拟示例（不实际发送）"""
    print("\n\n📧 邮件发送模拟示例")
    print("=" * 50)
    
    # 创建模拟分析数据
    mock_analysis = {
        'total_products': 25,
        'valid_products': 20,
        'best_rated': {
            'title': 'Apple MacBook Pro 16-inch M3 Max Chip',
            'price': 2499.00,
            'rating': 4.8,
            'review_count': 1250,
            'product_url': 'https://amazon.com/dp/example1'
        },
        'most_discounted': {
            'title': 'ASUS Gaming Laptop ROG Strix G15',
            'price': 899.99,
            'discount_percentage': 25.5,
            'rating': 4.5,
            'review_count': 680,
            'product_url': 'https://amazon.com/dp/example2'
        },
        'best_seller': {
            'title': 'Lenovo ThinkPad E15 Business Laptop',
            'price': 649.99,
            'rating': 4.3,
            'review_count': 2150,
            'product_url': 'https://amazon.com/dp/example3'
        },
        'analysis_summary': '最佳评分商品: Apple MacBook Pro 评分 4.8/5.0\n最高折扣商品: ASUS ROG Strix 折扣 25.5%\n最佳销量商品: Lenovo ThinkPad 评论数 2150',
        'analysis_time': datetime.now().isoformat()
    }
    
    async with Client(mcp) as client:
        # 生成 HTML 邮件内容（模拟）
        print("📨 正在模拟邮件内容生成...")
        
        # 注意：这里不实际发送邮件，只是模拟流程
        print("ℹ️  注意：这是模拟示例，不会实际发送邮件")
        print(f"\n📊 邮件内容模拟:")
        print(f"   收件人: user@example.com")
        print(f"   主题: Amazon 商品监控报告 - laptop")
        print(f"   内容类型: HTML 格式")
        print(f"   包含商品: {mock_analysis['total_products']} 个")
        
        # 显示邮件内容片段
        print(f"\n👀 邮件内容片段:")
        print(f"   ⭐ 最佳评分: {mock_analysis['best_rated']['title'][:40]}...")
        print(f"   💰 最高折扣: {mock_analysis['most_discounted']['title'][:40]}...")
        print(f"   🔥 最佳销量: {mock_analysis['best_seller']['title'][:40]}...")
        
        print("\n✅ 邮件内容模拟完成！")
        print("📌 实际使用时，请配置 SENDER_EMAIL 和 SENDER_PASSWORD 环境变量")
        
        return mock_analysis


async def main():
    """主函数 - 运行所有示例"""
    print("🎉 Amazon Product Monitor MCP Server 使用示例")
    print("=" * 80)
    print("📝 本示例将展示 MCP 服务器的各种功能")
    print("ℹ️  注意：由于网络环境限制，部分功能将使用模拟数据")
    print()
    
    try:
        # 1. 基本搜索示例
        products_data = await example_basic_search()
        
        # 2. 商品分析示例
        if products_data and products_data.get('products'):
            analysis_data = await example_product_analysis(products_data)
            
            # 3. Markdown 报告示例
            if analysis_data:
                await example_markdown_report(analysis_data)
        
        # 4. 完整分析示例
        await example_complete_analysis()
        
        # 5. 监控管理示例
        await example_monitor_management()
        
        # 6. 邮件模拟示例
        await example_email_simulation()
        
        print("\n\n🎆 所有示例运行完成！")
        print("=" * 80)
        print("📚 更多信息请参阅 README.md 文档")
        print("🚀 开始使用 MCP 服务器吧！")
        
    except Exception as e:
        print(f"\n❌ 示例运行失败: {e}")
        print("🛠️ 请检查网络连接和环境配置")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
