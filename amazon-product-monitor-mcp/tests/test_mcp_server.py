#!/usr/bin/env python3
"""
Amazon Product Monitor MCP Server 测试文件

测试 MCP 服务器的各种功能和工具。
"""

import asyncio
import json
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastmcp import Client
import sys

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent.parent))

from server import mcp
from src.amazon_monitor.tools import ProductInfo, ProductAnalyzer, ProductMonitor


class TestMCPServer:
    """测试 MCP 服务器功能"""
    
    @pytest.fixture
    def sample_products(self):
        """样本商品数据"""
        return [
            ProductInfo(
                title="Gaming Laptop ASUS ROG Strix G15",
                price=899.99,
                original_price=1199.99,
                rating=4.5,
                review_count=680,
                discount_percentage=25.0,
                availability="In Stock",
                image_url="https://example.com/image1.jpg",
                product_url="https://amazon.com/dp/B123456789",
                sales_rank=150,
                category="Electronics",
                asin="B123456789"
            ),
            ProductInfo(
                title="Apple MacBook Pro 16-inch M3",
                price=2499.00,
                original_price=None,
                rating=4.8,
                review_count=1250,
                discount_percentage=None,
                availability="In Stock",
                image_url="https://example.com/image2.jpg",
                product_url="https://amazon.com/dp/B987654321",
                sales_rank=25,
                category="Electronics",
                asin="B987654321"
            ),
            ProductInfo(
                title="Budget Laptop Lenovo ThinkPad E15",
                price=649.99,
                original_price=None,
                rating=4.3,
                review_count=2150,
                discount_percentage=None,
                availability="In Stock",
                image_url="https://example.com/image3.jpg",
                product_url="https://amazon.com/dp/B555444333",
                sales_rank=75,
                category="Electronics",
                asin="B555444333"
            )
        ]
    
    @pytest.fixture
    def sample_search_result(self, sample_products):
        """样本搜索结果"""
        return {
            'keyword': 'gaming laptop',
            'category': 'Electronics',
            'pages_searched': 2,
            'total_products': len(sample_products),
            'products': [product.to_dict() for product in sample_products],
            'search_time': '2025-07-13T15:00:00'
        }
    
    @pytest.mark.asyncio
    async def test_mcp_server_tools_available(self):
        """测试 MCP 服务器工具可用性"""
        async with Client(mcp) as client:
            # 获取可用工具
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]
            
            # 验证所有预期工具都存在
            expected_tools = [
                'search_amazon_products',
                'analyze_products',
                'send_email_report',
                'create_product_monitor',
                'run_product_monitor',
                'list_product_monitors',
                'get_monitor_history',
                'remove_product_monitor',
                'generate_markdown_report',
                'run_complete_analysis'
            ]
            
            for tool in expected_tools:
                assert tool in tool_names, f"工具 {tool} 不存在"
            
            print(f"✅ 所有 {len(expected_tools)} 个预期工具都可用")
    
    @pytest.mark.asyncio
    async def test_mcp_server_prompts_available(self):
        """测试 MCP 服务器提示可用性"""
        async with Client(mcp) as client:
            # 获取可用提示
            prompts = await client.list_prompts()
            prompt_names = [prompt.name for prompt in prompts]
            
            # 验证提示存在
            expected_prompts = [
                'amazon_product_analysis_prompt',
                'email_report_prompt'
            ]
            
            for prompt in expected_prompts:
                assert prompt in prompt_names, f"提示 {prompt} 不存在"
            
            print(f"✅ 所有 {len(expected_prompts)} 个预期提示都可用")
    
    @pytest.mark.asyncio
    async def test_mcp_server_resources_available(self):
        """测试 MCP 服务器资源可用性"""
        async with Client(mcp) as client:
            # 获取可用资源
            resources = await client.list_resources()
            resource_uris = [resource.uri for resource in resources]
            
            # 验证资源存在
            expected_resources = [
                'monitor_data_resource'
            ]
            
            # 至少应该有一个资源
            assert len(resources) >= 1, "应该至少有一个资源"
            
            print(f"✅ 找到 {len(resources)} 个资源")
    
    @pytest.mark.asyncio
    async def test_analyze_products_tool(self, sample_search_result):
        """测试商品分析工具"""
        async with Client(mcp) as client:
            # 测试分析工具
            result = await client.call_tool(
                "analyze_products",
                {"products_data": json.dumps(sample_search_result)}
            )
            
            # 验证结果
            analysis = result.content[0]
            assert 'total_products' in analysis
            assert 'valid_products' in analysis
            assert 'best_rated' in analysis
            assert 'most_discounted' in analysis
            assert 'best_seller' in analysis
            assert 'analysis_summary' in analysis
            
            # 验证数据正确性
            assert analysis['total_products'] == 3
            assert analysis['valid_products'] > 0
            
            # 验证最佳评分商品
            best_rated = analysis['best_rated']
            assert best_rated is not None
            assert 'Apple MacBook Pro' in best_rated['title']
            assert best_rated['rating'] == 4.8
            
            print(f"✅ 商品分析功能正常，分析了 {analysis['total_products']} 个商品")
    
    @pytest.mark.asyncio
    async def test_generate_markdown_report_tool(self, sample_search_result):
        """测试 Markdown 报告生成工具"""
        async with Client(mcp) as client:
            # 首先分析商品
            analysis_result = await client.call_tool(
                "analyze_products",
                {"products_data": json.dumps(sample_search_result)}
            )
            
            # 生成 Markdown 报告
            report_result = await client.call_tool(
                "generate_markdown_report",
                {
                    "analysis_result": json.dumps(analysis_result.content[0]),
                    "keyword": "gaming laptop"
                }
            )
            
            # 验证报告内容
            report = report_result.content
            assert isinstance(report, str)
            assert "# 🛒 Amazon 商品监控报告" in report
            assert "gaming laptop" in report
            assert "⭐ 最佳评分商品" in report
            assert "💰 最高折扣商品" in report
            assert "🔥 最佳销量商品" in report
            
            print(f"✅ Markdown 报告生成正常，长度: {len(report)} 字符")
    
    @pytest.mark.asyncio
    async def test_monitor_management_tools(self):
        """测试监控管理工具"""
        async with Client(mcp) as client:
            # 1. 创建监控
            create_result = await client.call_tool(
                "create_product_monitor",
                {
                    "keyword": "test laptop",
                    "category": "Electronics",
                    "email": "test@example.com",
                    "frequency": "daily"
                }
            )
            
            assert create_result.content[0]['success']
            monitor_id = create_result.content[0]['monitor_id']
            assert monitor_id.startswith('monitor_')
            
            # 2. 列出监控
            list_result = await client.call_tool("list_product_monitors", {})
            assert list_result.content[0]['success']
            monitors = list_result.content[0]['monitors']
            assert len(monitors) >= 1
            
            # 验证刚创建的监控在列表中
            monitor_ids = [m['id'] for m in monitors]
            assert monitor_id in monitor_ids
            
            # 3. 获取历史
            history_result = await client.call_tool(
                "get_monitor_history",
                {"monitor_id": monitor_id}
            )
            assert history_result.content[0]['success']
            
            # 4. 删除监控
            remove_result = await client.call_tool(
                "remove_product_monitor",
                {"monitor_id": monitor_id}
            )
            assert remove_result.content[0]['success']
            
            # 5. 验证删除成功
            list_result2 = await client.call_tool("list_product_monitors", {})
            monitors2 = list_result2.content[0]['monitors']
            monitor_ids2 = [m['id'] for m in monitors2]
            assert monitor_id not in monitor_ids2
            
            print(f"✅ 监控管理功能正常，创建并删除了监控 {monitor_id}")
    
    @pytest.mark.asyncio
    async def test_prompts_functionality(self):
        """测试提示功能"""
        async with Client(mcp) as client:
            # 测试商品分析提示
            prompt_result1 = await client.get_prompt(
                "amazon_product_analysis_prompt",
                {"keyword": "gaming laptop"}
            )
            
            prompt_content = prompt_result1.messages[0].content
            assert "gaming laptop" in prompt_content
            assert "search_amazon_products" in prompt_content
            assert "analyze_products" in prompt_content
            
            # 测试邮件报告提示
            prompt_result2 = await client.get_prompt(
                "email_report_prompt",
                {
                    "keyword": "smartphone",
                    "recipient_email": "user@example.com"
                }
            )
            
            prompt_content2 = prompt_result2.messages[0].content
            assert "smartphone" in prompt_content2
            assert "user@example.com" in prompt_content2
            assert "run_complete_analysis" in prompt_content2
            assert "send_email_report" in prompt_content2
            
            print(f"✅ 提示功能正常，生成了针对性提示")
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理"""
        async with Client(mcp) as client:
            # 测试无效的商品数据
            result = await client.call_tool(
                "analyze_products",
                {"products_data": "invalid json"}
            )
            
            # 验证错误处理
            assert 'error' in result.content[0]
            
            # 测试不存在的监控 ID
            result2 = await client.call_tool(
                "remove_product_monitor",
                {"monitor_id": "nonexistent_monitor"}
            )
            
            assert not result2.content[0]['success']
            
            print(f"✅ 错误处理功能正常")


class TestProductAnalyzer:
    """测试商品分析器"""
    
    def test_analyze_empty_products(self):
        """测试空商品列表分析"""
        analyzer = ProductAnalyzer()
        result = analyzer.analyze_products([])
        
        assert result['total_products'] == 0
        assert result['best_rated'] is None
        assert result['most_discounted'] is None
        assert result['best_seller'] is None
        print(f"✅ 空列表分析正常")
    
    def test_analyze_single_product(self):
        """测试单个商品分析"""
        analyzer = ProductAnalyzer()
        product = ProductInfo(
            title="Test Product",
            price=99.99,
            original_price=None,
            rating=4.5,
            review_count=100,
            discount_percentage=None,
            availability="In Stock",
            image_url="https://example.com/image.jpg",
            product_url="https://example.com/product",
            sales_rank=50,
            category="Electronics",
            asin="B123456789"
        )
        
        result = analyzer.analyze_products([product])
        
        assert result['total_products'] == 1
        assert result['valid_products'] == 1
        assert result['best_rated'] is not None
        assert result['best_rated']['title'] == "Test Product"
        print(f"✅ 单个商品分析正常")


def test_product_info_to_dict():
    """测试 ProductInfo 对象转字典"""
    product = ProductInfo(
        title="Test Product",
        price=99.99,
        original_price=129.99,
        rating=4.5,
        review_count=100,
        discount_percentage=23.1,
        availability="In Stock",
        image_url="https://example.com/image.jpg",
        product_url="https://example.com/product",
        sales_rank=50,
        category="Electronics",
        asin="B123456789"
    )
    
    result = product.to_dict()
    
    assert isinstance(result, dict)
    assert result['title'] == "Test Product"
    assert result['price'] == 99.99
    assert result['rating'] == 4.5
    assert result['review_count'] == 100
    print(f"✅ ProductInfo 转字典正常")


@pytest.mark.asyncio
async def test_mcp_server_complete_workflow():
    """测试 MCP 服务器完整工作流程"""
    # 模拟数据
    mock_products = {
        'keyword': 'headphones',
        'category': 'Electronics',
        'total_products': 2,
        'products': [
            {
                'title': 'Sony WH-1000XM4 Headphones',
                'price': 299.99,
                'rating': 4.7,
                'review_count': 5000,
                'product_url': 'https://example.com/sony'
            },
            {
                'title': 'Bose QuietComfort 35 II',
                'price': 249.99,
                'rating': 4.5,
                'review_count': 3000,
                'product_url': 'https://example.com/bose'
            }
        ]
    }
    
    async with Client(mcp) as client:
        # 1. 分析商品
        analysis_result = await client.call_tool(
            "analyze_products",
            {"products_data": json.dumps(mock_products)}
        )
        
        assert analysis_result.content[0]['total_products'] == 2
        
        # 2. 生成报告
        report_result = await client.call_tool(
            "generate_markdown_report",
            {
                "analysis_result": json.dumps(analysis_result.content[0]),
                "keyword": "headphones"
            }
        )
        
        assert "headphones" in report_result.content
        
        # 3. 创建监控
        monitor_result = await client.call_tool(
            "create_product_monitor",
            {
                "keyword": "test_workflow",
                "category": "Electronics",
                "frequency": "daily"
            }
        )
        
        assert monitor_result.content[0]['success']
        monitor_id = monitor_result.content[0]['monitor_id']
        
        # 4. 清理测试数据
        await client.call_tool(
            "remove_product_monitor",
            {"monitor_id": monitor_id}
        )
        
        print(f"✅ 完整工作流程测试通过")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
