"""Amazon Product Monitor MCP Tools

提供 Amazon 商品监控、分析和邮件通知的核心工具。
"""

import json
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Amazon 联盟 ID
AFFILIATE_ID = "joweaipmclub-20"

def add_affiliate_id_to_url(url: str, affiliate_id: str = AFFILIATE_ID) -> str:
    """为 Amazon URL 添加联盟 ID
    
    Args:
        url: 原始 Amazon 商品 URL
        affiliate_id: Amazon 联盟 ID
        
    Returns:
        包含联盟 ID 的 URL
    """
    if not url or not affiliate_id:
        return url
    
    try:
        # 解析 URL
        parsed = urlparse(url)
        
        # 确保是 Amazon 域名
        if 'amazon.com' not in parsed.netloc:
            return url
        
        # 解析查询参数
        query_params = parse_qs(parsed.query)
        
        # 添加或更新 tag 参数
        query_params['tag'] = [affiliate_id]
        
        # 重新构建查询字符串
        new_query = urlencode(query_params, doseq=True)
        
        # 重新构建 URL
        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        return new_url
        
    except Exception as e:
        logger.warning(f"添加联盟 ID 失败: {e}")
        return url


@dataclass
class ProductInfo:
    """商品信息数据类"""
    title: str
    price: Optional[float]
    original_price: Optional[float]
    rating: Optional[float]
    review_count: Optional[int]
    discount_percentage: Optional[float]
    availability: str
    image_url: Optional[str]
    product_url: str
    sales_rank: Optional[int]
    category: Optional[str]
    asin: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'title': self.title,
            'price': self.price,
            'original_price': self.original_price,
            'rating': self.rating,
            'review_count': self.review_count,
            'discount_percentage': self.discount_percentage,
            'availability': self.availability,
            'image_url': self.image_url,
            'product_url': add_affiliate_id_to_url(self.product_url),  # 添加联盟 ID
            'sales_rank': self.sales_rank,
            'category': self.category,
            'asin': self.asin
        }


class AmazonScraper:
    """Amazon 商品抓取器"""
    
    def __init__(self, headless: bool = True, wait_timeout: int = 10):
        self.headless = headless
        self.wait_timeout = wait_timeout
        self.driver = None
        self.session = requests.Session()
        
        # 设置请求头模拟真实浏览器
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def _setup_driver(self) -> webdriver.Chrome:
        """初始化 Chrome WebDriver"""
        if self.driver is None:
            options = Options()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            try:
                self.driver = webdriver.Chrome(options=options)
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception as e:
                logger.warning(f"无法启动 Chrome WebDriver: {e}. 将使用 requests 方式")
                self.driver = None
        
        return self.driver
    
    def search_products(self, keyword: str, category: str = "All", max_pages: int = 3) -> List[ProductInfo]:
        """搜索 Amazon 商品
        
        Args:
            keyword: 搜索关键词
            category: 商品类别
            max_pages: 最大搜索页数
            
        Returns:
            商品信息列表
        """
        products = []
        
        for page in range(1, max_pages + 1):
            try:
                page_products = self._search_page(keyword, category, page)
                products.extend(page_products)
                
                # 避免请求过于频繁
                if page < max_pages:
                    import time
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"搜索第 {page} 页时出错: {e}")
                continue
        
        return products
    
    def _search_page(self, keyword: str, category: str, page: int) -> List[ProductInfo]:
        """搜索单页商品"""
        # 构建搜索 URL
        base_url = "https://www.amazon.com/s"
        params = {
            'k': keyword,
            'page': page
        }
        
        if category != "All":
            params['rh'] = f'n:{self._get_category_id(category)}'
        
        # 尝试使用 Selenium
        driver = self._setup_driver()
        if driver:
            return self._search_with_selenium(base_url, params)
        else:
            return self._search_with_requests(base_url, params)
    
    def _search_with_selenium(self, base_url: str, params: Dict) -> List[ProductInfo]:
        """使用 Selenium 搜索"""
        try:
            # 构建完整 URL
            url = base_url + '?' + '&'.join([f'{k}={v}' for k, v in params.items()])
            
            self.driver.get(url)
            
            # 等待搜索结果加载
            wait = WebDriverWait(self.driver, self.wait_timeout)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-component-type="s-search-result"]')))
            
            # 解析商品信息
            products = []
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-component-type="s-search-result"]')
            
            for element in product_elements[:20]:  # 限制每页最多 20 个商品
                try:
                    product = self._parse_product_element_selenium(element)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning(f"解析商品元素时出错: {e}")
                    continue
            
            return products
            
        except TimeoutException:
            logger.error("页面加载超时")
            return []
        except WebDriverException as e:
            logger.error(f"WebDriver 错误: {e}")
            return []
    
    def _search_with_requests(self, base_url: str, params: Dict) -> List[ProductInfo]:
        """使用 requests 搜索（备用方案）"""
        try:
            url = base_url + '?' + '&'.join([f'{k}={v}' for k, v in params.items()])
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            products = []
            
            # 查找商品元素
            product_elements = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            for element in product_elements[:20]:  # 限制每页最多 20 个商品
                try:
                    product = self._parse_product_element_bs4(element)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning(f"解析商品元素时出错: {e}")
                    continue
            
            return products
            
        except Exception as e:
            logger.error(f"请求搜索页面失败: {e}")
            return []
    
    def _parse_product_element_selenium(self, element) -> Optional[ProductInfo]:
        """使用 Selenium 解析商品元素"""
        try:
            # 获取标题
            title_elem = element.find_element(By.CSS_SELECTOR, 'h2 a span')
            title = title_elem.text.strip() if title_elem else None
            
            # 获取链接和 ASIN
            link_elem = element.find_element(By.CSS_SELECTOR, 'h2 a')
            product_url = link_elem.get_attribute('href') if link_elem else None
            asin = self._extract_asin_from_url(product_url) if product_url else None
            
            # 获取价格
            price = None
            original_price = None
            try:
                price_elem = element.find_element(By.CSS_SELECTOR, '.a-price-whole')
                price_text = price_elem.text.replace(',', '') if price_elem else None
                if price_text and price_text.isdigit():
                    price = float(price_text)
            except:
                pass
            
            # 获取评分
            rating = None
            try:
                rating_elem = element.find_element(By.CSS_SELECTOR, '[aria-label*="stars"]')
                rating_text = rating_elem.get_attribute('aria-label')
                if rating_text and 'out of' in rating_text:
                    rating = float(rating_text.split()[0])
            except:
                pass
            
            # 获取评论数
            review_count = None
            try:
                review_elem = element.find_element(By.CSS_SELECTOR, 'a[href*="#customerReviews"]')
                review_text = review_elem.text.replace(',', '')
                if review_text.isdigit():
                    review_count = int(review_text)
            except:
                pass
            
            # 获取图片
            image_url = None
            try:
                img_elem = element.find_element(By.CSS_SELECTOR, 'img')
                image_url = img_elem.get_attribute('src')
            except:
                pass
            
            if not title:
                return None
            
            return ProductInfo(
                title=title,
                price=price,
                original_price=original_price,
                rating=rating,
                review_count=review_count,
                discount_percentage=None,
                availability="Unknown",
                image_url=image_url,
                product_url=product_url or "",
                sales_rank=None,
                category=None,
                asin=asin
            )
            
        except Exception as e:
            logger.warning(f"解析商品元素失败: {e}")
            return None
    
    def _parse_product_element_bs4(self, element) -> Optional[ProductInfo]:
        """使用 BeautifulSoup 解析商品元素"""
        try:
            # 获取标题
            title_elem = element.find('h2')
            title = title_elem.get_text().strip() if title_elem else None
            
            # 获取链接和 ASIN
            link_elem = element.find('h2').find('a') if element.find('h2') else None
            product_url = 'https://www.amazon.com' + link_elem.get('href') if link_elem else None
            asin = self._extract_asin_from_url(product_url) if product_url else None
            
            # 获取价格
            price = None
            price_elem = element.find('span', class_='a-price-whole')
            if price_elem:
                price_text = price_elem.get_text().replace(',', '')
                if price_text.isdigit():
                    price = float(price_text)
            
            # 获取评分
            rating = None
            rating_elem = element.find('span', {'aria-label': True})
            if rating_elem and 'out of' in rating_elem.get('aria-label', ''):
                try:
                    rating_text = rating_elem.get('aria-label')
                    rating = float(rating_text.split()[0])
                except:
                    pass
            
            # 获取评论数
            review_count = None
            review_elem = element.find('a', href=lambda x: x and '#customerReviews' in x)
            if review_elem:
                review_text = review_elem.get_text().replace(',', '')
                if review_text.isdigit():
                    review_count = int(review_text)
            
            # 获取图片
            image_url = None
            img_elem = element.find('img')
            if img_elem:
                image_url = img_elem.get('src')
            
            if not title:
                return None
            
            return ProductInfo(
                title=title,
                price=price,
                original_price=None,
                rating=rating,
                review_count=review_count,
                discount_percentage=None,
                availability="Unknown",
                image_url=image_url,
                product_url=product_url or "",
                sales_rank=None,
                category=None,
                asin=asin
            )
            
        except Exception as e:
            logger.warning(f"解析商品元素失败: {e}")
            return None
    
    def _extract_asin_from_url(self, url: str) -> Optional[str]:
        """从 URL 中提取 ASIN"""
        try:
            import re
            match = re.search(r'/dp/([A-Z0-9]{10})', url)
            return match.group(1) if match else None
        except:
            return None
    
    def _get_category_id(self, category: str) -> str:
        """获取类别 ID（简化版本）"""
        category_mapping = {
            'Electronics': '172282',
            'Books': '283155',
            'Clothing': '7141123011',
            'Home': '1055398',
            'Sports': '3375251',
            'Toys': '165793011'
        }
        return category_mapping.get(category, '')
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None


class ProductAnalyzer:
    """商品分析器"""
    
    def analyze_products(self, products: List[ProductInfo]) -> Dict[str, Any]:
        """分析商品列表，返回最佳商品
        
        Args:
            products: 商品信息列表
            
        Returns:
            包含分析结果的字典
        """
        if not products:
            return {
                'total_products': 0,
                'best_rated': None,
                'most_discounted': None,
                'best_seller': None,
                'analysis_summary': '未找到商品数据'
            }
        
        # 过滤有效商品
        valid_products = [p for p in products if p.title and p.price and p.price > 0]
        
        if not valid_products:
            return {
                'total_products': len(products),
                'best_rated': None,
                'most_discounted': None,
                'best_seller': None,
                'analysis_summary': '未找到有效的商品价格数据'
            }
        
        # 找到评分最高的商品
        best_rated = self._find_best_rated(valid_products)
        
        # 找到折扣最大的商品
        most_discounted = self._find_most_discounted(valid_products)
        
        # 找到最佳销量商品（基于评论数）
        best_seller = self._find_best_seller(valid_products)
        
        return {
            'total_products': len(products),
            'valid_products': len(valid_products),
            'best_rated': best_rated.to_dict() if best_rated else None,
            'most_discounted': most_discounted.to_dict() if most_discounted else None,
            'best_seller': best_seller.to_dict() if best_seller else None,
            'analysis_summary': self._generate_summary(best_rated, most_discounted, best_seller),
            'analysis_time': datetime.now().isoformat()
        }
    
    def _find_best_rated(self, products: List[ProductInfo]) -> Optional[ProductInfo]:
        """找到评分最高的商品"""
        rated_products = [p for p in products if p.rating is not None and p.review_count and p.review_count > 5]
        
        if not rated_products:
            return None
        
        # 综合评分和评论数量来判断最佳评分商品
        def rating_score(product):
            return product.rating * min(1.0, product.review_count / 100) * 100
        
        return max(rated_products, key=rating_score)
    
    def _find_most_discounted(self, products: List[ProductInfo]) -> Optional[ProductInfo]:
        """找到折扣最大的商品（基于价格范围估算）"""
        # 由于 Amazon 搜索页面通常不显示原价，我们基于价格分布来估算折扣
        if len(products) < 3:
            return None
        
        # 计算价格中位数作为基准
        prices = [p.price for p in products if p.price]
        if not prices:
            return None
        
        prices.sort()
        median_price = prices[len(prices) // 2]
        
        # 找到价格明显低于中位数的商品（可能是折扣商品）
        discounted_products = []
        for product in products:
            if product.price and product.price < median_price * 0.7:  # 价格低于中位数 70%
                discount_estimate = (median_price - product.price) / median_price * 100
                product.discount_percentage = discount_estimate
                discounted_products.append(product)
        
        if not discounted_products:
            return None
        
        return max(discounted_products, key=lambda p: p.discount_percentage or 0)
    
    def _find_best_seller(self, products: List[ProductInfo]) -> Optional[ProductInfo]:
        """找到最佳销量商品（基于评论数）"""
        products_with_reviews = [p for p in products if p.review_count and p.review_count > 0]
        
        if not products_with_reviews:
            return None
        
        return max(products_with_reviews, key=lambda p: p.review_count)
    
    def _generate_summary(self, best_rated: Optional[ProductInfo], 
                         most_discounted: Optional[ProductInfo], 
                         best_seller: Optional[ProductInfo]) -> str:
        """生成分析摘要"""
        summary_parts = []
        
        if best_rated:
            summary_parts.append(f"最佳评分商品: {best_rated.title[:50]}... (评分: {best_rated.rating}/5.0, 评论数: {best_rated.review_count})")
        
        if most_discounted:
            summary_parts.append(f"最高折扣商品: {most_discounted.title[:50]}... (估计折扣: {most_discounted.discount_percentage:.1f}%)")
        
        if best_seller:
            summary_parts.append(f"最佳销量商品: {best_seller.title[:50]}... (评论数: {best_seller.review_count})")
        
        if not summary_parts:
            return "未找到符合条件的推荐商品"
        
        return "\n\n".join(summary_parts)


class EmailReporter:
    """邮件报告发送器"""
    
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
    
    def send_report(self, analysis_result: Dict[str, Any], 
                   recipient_email: str, sender_email: str, 
                   sender_password: str, keyword: str) -> bool:
        """发送分析报告邮件
        
        Args:
            analysis_result: 分析结果
            recipient_email: 收件人邮箱
            sender_email: 发送者邮箱
            sender_password: 发送者邮箱密码或应用密码
            keyword: 搜索关键词
            
        Returns:
            发送是否成功
        """
        try:
            # 生成邮件内容
            subject = f"Amazon 商品监控报告 - {keyword}"
            html_content = self._generate_html_report(analysis_result, keyword)
            
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = recipient_email
            
            # 添加 HTML 内容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            logger.info(f"邮件发送成功: {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def _generate_html_report(self, analysis_result: Dict[str, Any], keyword: str) -> str:
        """生成 HTML 格式的报告"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Amazon 商品监控报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background-color: #232f3e; color: white; padding: 20px; text-align: center; border-radius: 5px; margin-bottom: 20px; }}
        .product-card {{ border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 15px 0; background-color: #fafafa; }}
        .product-title {{ font-size: 16px; font-weight: bold; color: #0066c0; margin-bottom: 10px; }}
        .product-price {{ font-size: 18px; color: #B12704; font-weight: bold; }}
        .product-rating {{ color: #ff9900; }}
        .section-title {{ font-size: 20px; color: #232f3e; border-bottom: 2px solid #ff9900; padding-bottom: 5px; margin: 20px 0 10px 0; }}
        .summary {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
        .no-data {{ color: #666; font-style: italic; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛍️ Amazon 商品监控报告</h1>
            <p>搜索关键词: <strong>{keyword}</strong></p>
            <p>报告时间: {analysis_result.get('analysis_time', '未知')}</p>
        </div>
        
        <div class="summary">
            <h2>📊 分析摘要</h2>
            <p><strong>总商品数:</strong> {analysis_result.get('total_products', 0)}</p>
            <p><strong>有效商品数:</strong> {analysis_result.get('valid_products', 0)}</p>
            <p>{analysis_result.get('analysis_summary', '无分析数据')}</p>
        </div>
        """
        
        # 最佳评分商品
        best_rated = analysis_result.get('best_rated')
        html += '<div class="section-title">⭐ 最佳评分商品</div>'
        if best_rated:
            html += self._format_product_card(best_rated, "⭐")
        else:
            html += '<p class="no-data">未找到评分数据</p>'
        
        # 最高折扣商品
        most_discounted = analysis_result.get('most_discounted')
        html += '<div class="section-title">💰 最高折扣商品</div>'
        if most_discounted:
            html += self._format_product_card(most_discounted, "💰")
        else:
            html += '<p class="no-data">未找到折扣商品</p>'
        
        # 最佳销量商品
        best_seller = analysis_result.get('best_seller')
        html += '<div class="section-title">🔥 最佳销量商品</div>'
        if best_seller:
            html += self._format_product_card(best_seller, "🔥")
        else:
            html += '<p class="no-data">未找到销量数据</p>'
        
        html += """
        <div class="footer">
            <p>此报告由 Amazon 商品监控系统自动生成</p>
            <p>数据来源: Amazon.com | 生成时间: {}</p>
        </div>
    </div>
</body>
</html>
        """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        return html
    
    def _format_product_card(self, product: Dict[str, Any], icon: str) -> str:
        """格式化商品卡片"""
        title = product.get('title', '未知商品')[:100]
        price = product.get('price')
        rating = product.get('rating')
        review_count = product.get('review_count')
        discount = product.get('discount_percentage')
        url = add_affiliate_id_to_url(product.get('product_url', '#'))  # 添加联盟 ID
        
        price_text = f"${price:.2f}" if price else "价格未知"
        rating_text = f"{rating}/5.0" if rating else "无评分"
        review_text = f"({review_count} 评论)" if review_count else "(无评论)"
        discount_text = f"折扣: {discount:.1f}%" if discount else ""
        
        return f"""
        <div class="product-card">
            <div class="product-title">{icon} {title}</div>
            <p><span class="product-price">{price_text}</span> {discount_text}</p>
            <p><span class="product-rating">★ {rating_text}</span> {review_text}</p>
            <p><a href="{url}" target="_blank">查看商品详情</a></p>
        </div>
        """


class ProductMonitor:
    """商品监控管理器"""
    
    def __init__(self, data_file: str = "product_monitor_data.json"):
        self.data_file = Path(data_file)
        self.scraper = AmazonScraper()
        self.analyzer = ProductAnalyzer()
        self.reporter = EmailReporter()
        self.data = self._load_data()
    
    def _load_data(self) -> Dict[str, Any]:
        """加载监控数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载数据文件失败: {e}")
        
        return {
            'monitors': [],
            'history': [],
            'settings': {}
        }
    
    def _save_data(self):
        """保存监控数据"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存数据文件失败: {e}")
    
    def add_monitor(self, keyword: str, category: str = "All", 
                   email: str = "", frequency: str = "daily") -> str:
        """添加商品监控
        
        Args:
            keyword: 搜索关键词
            category: 商品类别
            email: 通知邮箱
            frequency: 监控频率 (daily, weekly, monthly)
            
        Returns:
            监控 ID
        """
        monitor_id = f"monitor_{len(self.data['monitors']) + 1}_{int(datetime.now().timestamp())}"
        
        monitor = {
            'id': monitor_id,
            'keyword': keyword,
            'category': category,
            'email': email,
            'frequency': frequency,
            'created_at': datetime.now().isoformat(),
            'last_run': None,
            'active': True
        }
        
        self.data['monitors'].append(monitor)
        self._save_data()
        
        logger.info(f"添加监控: {keyword} (ID: {monitor_id})")
        return monitor_id
    
    def run_monitor(self, monitor_id: str, sender_email: str = "", 
                   sender_password: str = "") -> Dict[str, Any]:
        """运行指定监控
        
        Args:
            monitor_id: 监控 ID
            sender_email: 发送者邮箱
            sender_password: 发送者邮箱密码
            
        Returns:
            运行结果
        """
        # 查找监控
        monitor = None
        for m in self.data['monitors']:
            if m['id'] == monitor_id:
                monitor = m
                break
        
        if not monitor:
            return {'success': False, 'error': '监控不存在'}
        
        if not monitor['active']:
            return {'success': False, 'error': '监控已禁用'}
        
        try:
            # 搜索商品
            logger.info(f"开始搜索商品: {monitor['keyword']}")
            products = self.scraper.search_products(monitor['keyword'], monitor['category'])
            
            # 分析商品
            logger.info(f"开始分析 {len(products)} 个商品")
            analysis_result = self.analyzer.analyze_products(products)
            
            # 记录历史
            history_entry = {
                'monitor_id': monitor_id,
                'keyword': monitor['keyword'],
                'timestamp': datetime.now().isoformat(),
                'analysis_result': analysis_result,
                'success': True
            }
            self.data['history'].append(history_entry)
            
            # 发送邮件（如果配置了邮箱）
            email_sent = False
            if monitor['email'] and sender_email and sender_password:
                logger.info(f"发送邮件报告到: {monitor['email']}")
                email_sent = self.reporter.send_report(
                    analysis_result, monitor['email'], 
                    sender_email, sender_password, monitor['keyword']
                )
            
            # 更新监控状态
            monitor['last_run'] = datetime.now().isoformat()
            self._save_data()
            
            return {
                'success': True,
                'monitor_id': monitor_id,
                'keyword': monitor['keyword'],
                'products_found': len(products),
                'analysis_result': analysis_result,
                'email_sent': email_sent
            }
            
        except Exception as e:
            logger.error(f"运行监控失败: {e}")
            
            # 记录失败历史
            history_entry = {
                'monitor_id': monitor_id,
                'keyword': monitor['keyword'],
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'success': False
            }
            self.data['history'].append(history_entry)
            self._save_data()
            
            return {'success': False, 'error': str(e)}
    
    def get_monitors(self) -> List[Dict[str, Any]]:
        """获取所有监控"""
        return self.data['monitors']
    
    def get_monitor_history(self, monitor_id: str = "") -> List[Dict[str, Any]]:
        """获取监控历史"""
        if monitor_id:
            return [h for h in self.data['history'] if h.get('monitor_id') == monitor_id]
        return self.data['history']
    
    def remove_monitor(self, monitor_id: str) -> bool:
        """删除监控"""
        original_length = len(self.data['monitors'])
        self.data['monitors'] = [m for m in self.data['monitors'] if m['id'] != monitor_id]
        
        if len(self.data['monitors']) < original_length:
            self._save_data()
            logger.info(f"删除监控: {monitor_id}")
            return True
        
        return False
    
    def close(self):
        """清理资源"""
        self.scraper.close()
