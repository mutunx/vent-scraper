import os
import json
import logging
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
import requests
import time
import random
from utils.storage_utils import save_weekly_data, update_source_index

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """
    爬虫基础类，定义通用接口和方法
    所有特定网站的爬虫都应继承此类
    """
    
    def __init__(self):
        self.source_id = self.get_source_id()
        self.source_name = self.get_source_name()
        self.session = requests.Session()
        self.session.headers.update(self.get_headers())
        
    @abstractmethod
    def get_source_id(self):
        """返回源标识符，如'jandan', 'v2ex'等"""
        pass
    
    @abstractmethod
    def get_source_name(self):
        """返回源名称，用于显示"""
        pass
    
    def get_headers(self):
        """返回请求头"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0'
        ]
        
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def fetch_page(self, url, max_retries=3, delay=(1, 3)):
        """获取页面内容，带重试机制"""
        for attempt in range(max_retries):
            try:
                # 随机延迟，避免被反爬
                time.sleep(random.uniform(delay[0], delay[1]))
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.warning(f"获取页面失败 (尝试 {attempt+1}/{max_retries}): {url}, 错误: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"获取页面失败: {url}, 错误: {str(e)}")
        return None
    
    def post_request(self, url, data=None, json_data=None, max_retries=3, delay=(1, 3)):
        """发送POST请求，带重试机制"""
        for attempt in range(max_retries):
            try:
                time.sleep(random.uniform(delay[0], delay[1]))
                if json_data:
                    response = self.session.post(url, json=json_data, timeout=10)
                else:
                    response = self.session.post(url, data=data, timeout=10)
                response.raise_for_status()
                return response
            except Exception as e:
                logger.warning(f"POST请求失败 (尝试 {attempt+1}/{max_retries}): {url}, 错误: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"POST请求失败: {url}, 错误: {str(e)}")
        return None
    
    def generate_id(self, prefix, text):
        """生成唯一ID"""
        return hashlib.md5(f"{prefix}_{text}".encode()).hexdigest()
    
    def save_data(self, data, date=None):
        """保存数据（以周为单位进行增量更新）
        
        Args:
            data (dict): 要保存的数据
            date (str): 日期字符串，格式为YYYY-MM-DD，默认为当天
            
        Returns:
            str: 保存的文件路径
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # 增加数据源图标（如果未提供）
        if 'meta' in data and 'icon' not in data['meta']:
            data['meta']['icon'] = f"{self.source_id}.png"
        
        # 使用周存储并增量更新
        filepath = save_weekly_data(self.source_id, data, date)
        
        logger.info(f"数据已保存到 {filepath}")
        return filepath
    
    @abstractmethod
    def scrape(self):
        """执行爬取操作，由子类实现"""
        pass
    
    def run(self):
        """运行爬虫并保存数据"""
        logger.info(f"开始爬取 {self.source_name}")
        data = self.scrape()
        
        if data:
            date = datetime.now().strftime("%Y-%m-%d")
            self.save_data(data, date)
            logger.info(f"成功爬取 {self.source_name} 的数据")
            return data
        else:
            logger.error(f"爬取 {self.source_name} 失败")
            return None