#!/usr/bin/env python3
"""Amazon Product Monitor MCP Server

一个全功能的 Amazon 商品监控与邮件通知 MCP 服务器。
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastmcp import FastMCP
from src.amazon_monitor.tools import ProductMonitor, AmazonScraper, ProductAnalyzer, EmailReporter, add_affiliate_id_to_url

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 MCP 服务器实例
mcp = FastMCP("Amazon Product Monitor")

# 全局实例
product_monitor = ProductMonitor()
amazon_scraper = AmazonScraper()
product_analyzer = ProductAnalyzer()
email_reporter = EmailReporter()


@mcp.tool
def search_amazon_products(keyword: str, category: str = "All", max_pages: int = 2) -> Dict[str, Any]:
    """搜索 Amazon 商品
    
    Args:
        keyword: 搜索关键词，例如 "gaming laptop" 或 "智能手机"
        category: 商品类别，可选值: All, Electronics, Books, Clothing, Home, Sports, Toys
        max_pages: 最大搜索页数 (1-5)
        
    Returns:
        包含搜索结果的字典，包含商品列表和搜索统计信息
    """
    try:
        logger.info(f"开始搜索 Amazon 商品: {keyword}, 类别: {category}")
        
        # 限制页数范围
        max_pages = max(1, min(max_pages, 5))
        
        # 搜索商品
        products = amazon_scraper.search_products(keyword, category, max_pages)
        
        # 转换为字典格式
        product_list = [product.to_dict() for product in products]
        
        result = {
            'keyword': keyword,
            'category': category,
            'pages_searched': max_pages,
            'total_products': len(product_list),
            'products': product_list,
            'search_time': datetime.now().isoformat()
        }
        
        logger.info(f"搜索完成，找到 {len(product_list)} 个商品")
        return result
        
    except Exception as e:
        logger.error(f"搜索商品时出错: {e}")
        return {
            'error': str(e),
            'keyword': keyword,
            'category': category,
            'total_products': 0,
            'products': []
        }


@mcp.tool
def analyze_products(products_data: str) -> Dict[str, Any]:
    """分析商品数据，找出最佳商品
    
    Args:
        products_data: JSON 格式的商品数据字符串，来自 search_amazon_products 的结果
        
    Returns:
        包含分析结果的字典，包括最佳评分、最高折扣、最佳销量商品
    """
    try:
        # 解析产品数据
        if isinstance(products_data, str):
            data = json.loads(products_data)
        else:
            data = products_data
        
        products_list = data.get('products', [])
        
        if not products_list:
            return {
                'error': '没有产品数据可供分析',
                'total_products': 0,
                'analysis_result': None
            }
        
        # 转换为 ProductInfo 对象
        from src.amazon_monitor.tools import ProductInfo
        products = []
        for p in products_list:
            product = ProductInfo(
                title=p.get('title', ''),
                price=p.get('price'),
                original_price=p.get('original_price'),
                rating=p.get('rating'),
                review_count=p.get('review_count'),
                discount_percentage=p.get('discount_percentage'),
                availability=p.get('availability', 'Unknown'),
                image_url=p.get('image_url'),
                product_url=p.get('product_url', ''),
                sales_rank=p.get('sales_rank'),
                category=p.get('category'),
                asin=p.get('asin')
            )
            products.append(product)
        
        # 进行分析
        analysis_result = product_analyzer.analyze_products(products)
        
        logger.info(f"产品分析完成，分析了 {len(products)} 个商品")
        return analysis_result
        
    except Exception as e:
        logger.error(f"分析产品时出错: {e}")
        return {
            'error': str(e),
            'total_products': 0,
            'analysis_result': None
        }


@mcp.tool
def send_email_report(analysis_result: str, recipient_email: str, 
                     sender_email: str, sender_password: str, 
                     keyword: str = "Amazon 商品") -> Dict[str, Any]:
    """发送邮件报告
    
    Args:
        analysis_result: JSON 格式的分析结果字符串
        recipient_email: 收件人邮箱地址
        sender_email: 发送者邮箱地址 (推荐使用 Gmail)
        sender_password: 发送者邮箱密码或应用密码
        keyword: 搜索关键词，用于邮件标题
        
    Returns:
        包含发送结果的字典
    """
    try:
        # 解析分析结果
        if isinstance(analysis_result, str):
            data = json.loads(analysis_result)
        else:
            data = analysis_result
        
        # 发送邮件
        success = email_reporter.send_report(
            data, recipient_email, sender_email, sender_password, keyword
        )
        
        if success:
            logger.info(f"邮件报告发送成功: {recipient_email}")
            return {
                'success': True,
                'message': '邮件发送成功',
                'recipient': recipient_email,
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'error': '邮件发送失败，请检查邮箱配置',
                'recipient': recipient_email
            }
            
    except Exception as e:
        logger.error(f"发送邮件时出错: {e}")
        return {
            'success': False,
            'error': str(e),
            'recipient': recipient_email
        }


@mcp.tool
def create_product_monitor(keyword: str, category: str = "All", 
                          email: str = "", frequency: str = "daily") -> Dict[str, Any]:
    """创建商品监控任务
    
    Args:
        keyword: 监控的搜索关键词
        category: 商品类别，可选值: All, Electronics, Books, Clothing, Home, Sports, Toys
        email: 通知邮箱地址（可选）
        frequency: 监控频率，可选值: daily, weekly, monthly
        
    Returns:
        包含监控 ID 和创建信息的字典
    """
    try:
        monitor_id = product_monitor.add_monitor(keyword, category, email, frequency)
        
        logger.info(f"创建商品监控: {keyword} (ID: {monitor_id})")
        return {
            'success': True,
            'monitor_id': monitor_id,
            'keyword': keyword,
            'category': category,
            'email': email,
            'frequency': frequency,
            'created_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"创建监控时出错: {e}")
        return {
            'success': False,
            'error': str(e),
            'keyword': keyword
        }


@mcp.tool
def run_product_monitor(monitor_id: str, sender_email: str = "", 
                       sender_password: str = "") -> Dict[str, Any]:
    """运行商品监控任务
    
    Args:
        monitor_id: 监控任务 ID
        sender_email: 发送者邮箱地址（如果需要发送邮件）
        sender_password: 发送者邮箱密码（如果需要发送邮件）
        
    Returns:
        包含监控运行结果的字典
    """
    try:
        result = product_monitor.run_monitor(monitor_id, sender_email, sender_password)
        
        if result['success']:
            logger.info(f"监控运行成功: {monitor_id}")
        else:
            logger.error(f"监控运行失败: {result.get('error', '未知错误')}")
        
        return result
        
    except Exception as e:
        logger.error(f"运行监控时出错: {e}")
        return {
            'success': False,
            'error': str(e),
            'monitor_id': monitor_id
        }


@mcp.tool
def list_product_monitors() -> Dict[str, Any]:
    """列出所有商品监控任务
    
    Returns:
        包含所有监控任务的字典
    """
    try:
        monitors = product_monitor.get_monitors()
        
        return {
            'success': True,
            'total_monitors': len(monitors),
            'monitors': monitors,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取监控列表时出错: {e}")
        return {
            'success': False,
            'error': str(e),
            'monitors': []
        }


@mcp.tool
def get_monitor_history(monitor_id: str = "") -> Dict[str, Any]:
    """获取监控历史记录
    
    Args:
        monitor_id: 监控任务 ID（可选，如果不提供则返回所有历史记录）
        
    Returns:
        包含历史记录的字典
    """
    try:
        history = product_monitor.get_monitor_history(monitor_id)
        
        return {
            'success': True,
            'monitor_id': monitor_id or 'all',
            'total_records': len(history),
            'history': history,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取监控历史时出错: {e}")
        return {
            'success': False,
            'error': str(e),
            'history': []
        }


@mcp.tool
def remove_product_monitor(monitor_id: str) -> Dict[str, Any]:
    """删除商品监控任务
    
    Args:
        monitor_id: 要删除的监控任务 ID
        
    Returns:
        包含删除结果的字典
    """
    try:
        success = product_monitor.remove_monitor(monitor_id)
        
        if success:
            logger.info(f"删除监控成功: {monitor_id}")
            return {
                'success': True,
                'message': '监控任务删除成功',
                'monitor_id': monitor_id,
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'error': '监控任务不存在或删除失败',
                'monitor_id': monitor_id
            }
            
    except Exception as e:
        logger.error(f"删除监控时出错: {e}")
        return {
            'success': False,
            'error': str(e),
            'monitor_id': monitor_id
        }


@mcp.tool
def generate_markdown_report(analysis_result: str, keyword: str = "Amazon 商品") -> str:
    """生成 Markdown 格式的分析报告
    
    Args:
        analysis_result: JSON 格式的分析结果字符串
        keyword: 搜索关键词
        
    Returns:
        Markdown 格式的报告内容
    """
    try:
        # 解析分析结果
        if isinstance(analysis_result, str):
            data = json.loads(analysis_result)
        else:
            data = analysis_result
        
        # 生成 Markdown 报告
        markdown = f"""# 🛒 Amazon 商品监控报告

## 📊 搜索信息
- **关键词**: {keyword}
- **报告时间**: {data.get('analysis_time', datetime.now().isoformat())}
- **总商品数**: {data.get('total_products', 0)}
- **有效商品数**: {data.get('valid_products', 0)}

## 📈 分析摘要
{data.get('analysis_summary', '无分析数据')}

---

"""
        
        # 最佳评分商品
        best_rated = data.get('best_rated')
        markdown += "## ⭐ 最佳评分商品\n\n"
        if best_rated:
            affiliate_url = add_affiliate_id_to_url(best_rated.get('product_url', '#'))
            markdown += f"""### {best_rated.get('title', '未知商品')}
- **价格**: ${best_rated.get('price', 0):.2f}
- **评分**: {best_rated.get('rating', 'N/A')}/5.0
- **评论数**: {best_rated.get('review_count', 0)}
- **链接**: [查看商品]({affiliate_url})

"""
        else:
            markdown += "*未找到评分数据*\n\n"
        
        # 最高折扣商品
        most_discounted = data.get('most_discounted')
        markdown += "## 💰 最高折扣商品\n\n"
        if most_discounted:
            discount = most_discounted.get('discount_percentage', 0)
            affiliate_url = add_affiliate_id_to_url(most_discounted.get('product_url', '#'))
            markdown += f"""### {most_discounted.get('title', '未知商品')}
- **价格**: ${most_discounted.get('price', 0):.2f}
- **估计折扣**: {discount:.1f}%
- **评分**: {most_discounted.get('rating', 'N/A')}/5.0
- **链接**: [查看商品]({affiliate_url})

"""
        else:
            markdown += "*未找到折扣商品*\n\n"
        
        # 最佳销量商品
        best_seller = data.get('best_seller')
        markdown += "## 🔥 最佳销量商品\n\n"
        if best_seller:
            affiliate_url = add_affiliate_id_to_url(best_seller.get('product_url', '#'))
            markdown += f"""### {best_seller.get('title', '未知商品')}
- **价格**: ${best_seller.get('price', 0):.2f}
- **评论数**: {best_seller.get('review_count', 0)}
- **评分**: {best_seller.get('rating', 'N/A')}/5.0
- **链接**: [查看商品]({affiliate_url})

"""
        else:
            markdown += "*未找到销量数据*\n\n"
        
        markdown += "---\n\n*此报告由 Amazon 商品监控系统自动生成*"
        
        return markdown
        
    except Exception as e:
        logger.error(f"生成 Markdown 报告时出错: {e}")
        return f"生成报告时出错: {e}"


@mcp.tool
def run_complete_analysis(keyword: str, category: str = "All", 
                         max_pages: int = 2) -> Dict[str, Any]:
    """运行完整的商品分析流程
    
    Args:
        keyword: 搜索关键词
        category: 商品类别
        max_pages: 最大搜索页数
        
    Returns:
        包含搜索结果和分析结果的完整字典
    """
    try:
        logger.info(f"开始完整分析流程: {keyword}")
        
        # 步骤 1: 搜索商品
        search_result = search_amazon_products(keyword, category, max_pages)
        
        if search_result.get('error'):
            return {
                'success': False,
                'error': f"搜索失败: {search_result['error']}",
                'keyword': keyword
            }
        
        # 步骤 2: 分析商品
        analysis_result = analyze_products(search_result)
        
        if analysis_result.get('error'):
            return {
                'success': False,
                'error': f"分析失败: {analysis_result['error']}",
                'keyword': keyword,
                'search_result': search_result
            }
        
        # 步骤 3: 生成报告
        markdown_report = generate_markdown_report(analysis_result, keyword)
        
        logger.info(f"完整分析流程完成: {keyword}")
        return {
            'success': True,
            'keyword': keyword,
            'search_result': search_result,
            'analysis_result': analysis_result,
            'markdown_report': markdown_report,
            'completed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"完整分析流程出错: {e}")
        return {
            'success': False,
            'error': str(e),
            'keyword': keyword
        }


# Prompt 定义
@mcp.prompt
def amazon_product_analysis_prompt(keyword: str) -> str:
    """生成 Amazon 商品分析提示
    
    Args:
        keyword: 搜索关键词
        
    Returns:
        用于分析商品的提示文本
    """
    return f"""请帮我分析 Amazon 上关于 "{keyword}" 的商品。我需要您:

1. 使用 search_amazon_products 工具搜索相关商品
2. 使用 analyze_products 工具分析搜索结果
3. 找出以下三个维度的最佳商品：
   - 评分最高的商品（综合评分和评论数量）
   - 折扣最大的商品（价格优势明显）
   - 销量最好的商品（评论数量最多）
4. 使用 generate_markdown_report 生成详细的分析报告

请为每个推荐商品提供详细信息，包括价格、评分、评论数量和商品链接。"""


@mcp.prompt
def email_report_prompt(keyword: str, recipient_email: str) -> str:
    """生成邮件报告发送提示
    
    Args:
        keyword: 搜索关键词
        recipient_email: 收件人邮箱
        
    Returns:
        用于发送邮件报告的提示文本
    """
    return f"""请帮我为 "{keyword}" 的 Amazon 商品分析结果发送邮件报告到 {recipient_email}。

流程：
1. 首先运行 run_complete_analysis 获取完整分析结果
2. 然后使用 send_email_report 将分析结果以HTML格式发送给用户

注意：发送邮件需要配置发送者邮箱和密码，请确保提供正确的邮箱凭据。"""


# 资源定义
@mcp.resource("monitor://data")
def monitor_data_resource() -> str:
    """商品监控数据资源
    
    Returns:
        当前所有监控任务的 JSON 数据
    """
    try:
        monitors = product_monitor.get_monitors()
        history = product_monitor.get_monitor_history()
        
        data = {
            'monitors': monitors,
            'history': history,
            'last_updated': datetime.now().isoformat()
        }
        
        return json.dumps(data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


def cleanup():
    """清理资源"""
    try:
        product_monitor.close()
        amazon_scraper.close()
        logger.info("资源清理完成")
    except Exception as e:
        logger.error(f"清理资源时出错: {e}")


if __name__ == "__main__":
    import signal
    import sys
    
    # 注册清理函数
    def signal_handler(sig, frame):
        logger.info("接收到退出信号，正在清理资源...")
        cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("启动 Amazon Product Monitor MCP Server")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("用户中断，正在清理资源...")
    finally:
        cleanup()
