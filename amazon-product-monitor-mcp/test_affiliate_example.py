#!/usr/bin/env python3
"""
测试 Amazon 联盟 ID 功能
"""

import json
from src.amazon_monitor.tools import add_affiliate_id_to_url

# 测试联盟 URL 生成
def test_affiliate_url():
    print("🧪 测试 Amazon 联盟 ID 功能")
    print("=" * 50)
    
    test_urls = [
        "https://www.amazon.com/dp/B08N5WRWNW",
        "https://www.amazon.com/Apple-MacBook-13-inch-256GB-Storage/dp/B08N5M7S6K",
        "https://www.amazon.com/dp/B09G9FPHY6/ref=sr_1_3?keywords=laptop"
    ]
    
    for url in test_urls:
        affiliate_url = add_affiliate_id_to_url(url, "joweaipmclub-20")
        print(f"原始链接: {url}")
        print(f"联盟链接: {affiliate_url}")
        print()

def create_sample_markdown_report():
    """创建示例 Markdown 报告"""
    print("📝 生成包含联盟链接的示例 Markdown 报告")
    print("=" * 50)
    
    # 模拟分析数据
    sample_analysis = {
        'total_products': 15,
        'valid_products': 12,
        'best_rated': {
            'title': 'Apple AirPods Pro (2nd Generation)',
            'price': 249.00,
            'rating': 4.8,
            'review_count': 12450,
            'product_url': 'https://www.amazon.com/dp/B0BDHWDR12'
        },
        'most_discounted': {
            'title': 'Sony WH-1000XM4 Wireless Noise Cancelling Headphones',
            'price': 279.99,
            'discount_percentage': 22.2,
            'rating': 4.6,
            'review_count': 8900,
            'product_url': 'https://www.amazon.com/dp/B0863TXGM3'
        },
        'best_seller': {
            'title': 'JBL Tune 760NC Wireless Over-Ear Headphones',
            'price': 99.95,
            'rating': 4.4,
            'review_count': 15300,
            'product_url': 'https://www.amazon.com/dp/B08WM3LHVN'
        },
        'analysis_summary': '最佳评分商品: Apple AirPods Pro 评分 4.8/5.0\n最高折扣商品: Sony WH-1000XM4 折扣 22.2%\n最佳销量商品: JBL Tune 760NC 评论数 15300',
        'analysis_time': '2025-07-13T15:33:07'
    }
    
    # 生成 Markdown 报告
    from datetime import datetime
    keyword = "蓝牙耳机"
    
    markdown = f"""# 🛒 Amazon 商品监控报告

## 📊 搜索信息
- **关键词**: {keyword}
- **报告时间**: {sample_analysis.get('analysis_time', datetime.now().isoformat())}
- **总商品数**: {sample_analysis.get('total_products', 0)}
- **有效商品数**: {sample_analysis.get('valid_products', 0)}

## 📈 分析摘要
{sample_analysis.get('analysis_summary', '无分析数据')}

---

"""
    
    # 最佳评分商品
    best_rated = sample_analysis.get('best_rated')
    markdown += "## ⭐ 最佳评分商品\n\n"
    if best_rated:
        affiliate_url = add_affiliate_id_to_url(best_rated.get('product_url', '#'))
        markdown += f"""### {best_rated.get('title', '未知商品')}
- **价格**: ${best_rated.get('price', 0):.2f}
- **评分**: {best_rated.get('rating', 'N/A')}/5.0
- **评论数**: {best_rated.get('review_count', 0)}
- **🎯 联盟链接**: [查看商品 (含联盟 ID)]({affiliate_url})

"""
    
    # 最高折扣商品
    most_discounted = sample_analysis.get('most_discounted')
    markdown += "## 💰 最高折扣商品\n\n"
    if most_discounted:
        discount = most_discounted.get('discount_percentage', 0)
        affiliate_url = add_affiliate_id_to_url(most_discounted.get('product_url', '#'))
        markdown += f"""### {most_discounted.get('title', '未知商品')}
- **价格**: ${most_discounted.get('price', 0):.2f}
- **估计折扣**: {discount:.1f}%
- **评分**: {most_discounted.get('rating', 'N/A')}/5.0
- **🎯 联盟链接**: [查看商品 (含联盟 ID)]({affiliate_url})

"""
    
    # 最佳销量商品
    best_seller = sample_analysis.get('best_seller')
    markdown += "## 🔥 最佳销量商品\n\n"
    if best_seller:
        affiliate_url = add_affiliate_id_to_url(best_seller.get('product_url', '#'))
        markdown += f"""### {best_seller.get('title', '未知商品')}
- **价格**: ${best_seller.get('price', 0):.2f}
- **评论数**: {best_seller.get('review_count', 0)}
- **评分**: {best_seller.get('rating', 'N/A')}/5.0
- **🎯 联盟链接**: [查看商品 (含联盟 ID)]({affiliate_url})

"""
    
    markdown += """---

## 🎯 Amazon 联盟信息
- **联盟 ID**: `joweaipmclub-20`
- **追踪支持**: 所有商品链接均包含联盟标签
- **收益来源**: 通过报告链接产生的购买行为将被追踪

*此报告由 Amazon 商品监控系统自动生成*
"""
    
    # 保存报告
    with open('/workspace/amazon-product-monitor-mcp/sample_affiliate_report.md', 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print("✅ 示例 Markdown 报告已生成: sample_affiliate_report.md")
    print("\n📋 报告预览 (前 20 行):")
    lines = markdown.split('\n')
    for i, line in enumerate(lines[:20], 1):
        print(f"{i:2d}. {line}")
    print("   ...")

if __name__ == "__main__":
    test_affiliate_url()
    print()
    create_sample_markdown_report()
