#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import random
import logging
import requests
from urllib.parse import urlparse, urljoin
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from functools import lru_cache
import hashlib
import os
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 默认请求超时时间（秒）
DEFAULT_TIMEOUT = 10

# 默认重试配置
DEFAULT_RETRY_CONFIG = {
    'total': 3,  # 最大重试次数
    'backoff_factor': 0.5,  # 重试间隔增长因子
    'status_forcelist': [500, 502, 503, 504]  # 哪些HTTP状态码需要重试
}

# 默认随机延迟范围（秒）
DEFAULT_DELAY_RANGE = (1, 3)

# 默认用户代理列表
DEFAULT_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
]

class RequestThrottler:
    """请求限流器，防止频繁请求同一域名"""
    
    def __init__(self, min_interval=1.0):
        """初始化限流器
        
        Args:
            min_interval (float): 同一域名两次请求之间的最小间隔（秒）
        """
        self.min_interval = min_interval
        self.last_request_time = {}
    
    def wait_if_needed(self, url):
        """如果需要，等待适当的时间再请求
        
        Args:
            url (str): 请求URL
        """
        domain = urlparse(url).netloc
        current_time = time.time()
        
        if domain in self.last_request_time:
            elapsed = current_time - self.last_request_time[domain]
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                logger.debug(f"限流: 等待 {sleep_time:.2f} 秒后再请求 {domain}")
                time.sleep(sleep_time)
        
        self.last_request_time[domain] = time.time()


class HttpClient:
    """HTTP客户端，封装请求相关功能"""
    
    def __init__(self, retry_config=None, 
                 timeout=DEFAULT_TIMEOUT, 
                 delay_range=DEFAULT_DELAY_RANGE,
                 user_agents=None,
                 use_cache=True,
                 cache_dir='.cache',
                 cache_ttl=3600):
        """初始化HTTP客户端
        
        Args:
            retry_config (dict): 重试配置
            timeout (int): 请求超时时间（秒）
            delay_range (tuple): 随机延迟范围（最小秒数, 最大秒数）
            user_agents (list): 用户代理列表
            use_cache (bool): 是否使用请求缓存
            cache_dir (str): 缓存目录
            cache_ttl (int): 缓存过期时间（秒）
        """
        self.retry_config = retry_config or DEFAULT_RETRY_CONFIG
        self.timeout = timeout
        self.delay_range = delay_range
        self.user_agents = user_agents or DEFAULT_USER_AGENTS
        self.throttler = RequestThrottler()
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        
        if self.use_cache and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        self.session = self._create_session()
    
    def _create_session(self):
        """创建配置好的会话对象"""
        session = requests.Session()
        
        # 配置重试机制
        retry = Retry(
            total=self.retry_config['total'],
            backoff_factor=self.retry_config['backoff_factor'],
            status_forcelist=self.retry_config['status_forcelist'],
            allowed_methods=None  # 允许所有方法重试
        )
        
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def _get_random_user_agent(self):
        """获取随机用户代理"""
        return random.choice(self.user_agents)
    
    def _add_random_delay(self):
        """添加随机延迟"""
        delay = random.uniform(*self.delay_range)
        logger.debug(f"随机延迟 {delay:.2f} 秒")
        time.sleep(delay)
    
    def _get_cache_path(self, url, method, data=None):
        """获取缓存文件路径"""
        # 根据请求参数生成缓存键
        cache_key = f"{method.lower()}:{url}"
        if data:
            if isinstance(data, dict):
                cache_key += ":" + json.dumps(data, sort_keys=True)
            else:
                cache_key += ":" + str(data)
        
        # 生成缓存文件名
        filename = hashlib.md5(cache_key.encode()).hexdigest() + ".json"
        return os.path.join(self.cache_dir, filename)
    
    def _get_from_cache(self, url, method, data=None):
        """从缓存获取响应"""
        if not self.use_cache:
            return None
        
        cache_path = self._get_cache_path(url, method, data)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查缓存是否过期
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cache_time > timedelta(seconds=self.cache_ttl):
                logger.debug(f"缓存已过期: {url}")
                return None
            
            logger.debug(f"从缓存获取: {url}")
            return cache_data['response']
            
        except Exception as e:
            logger.warning(f"读取缓存出错: {str(e)}")
            return None
    
    def _save_to_cache(self, url, method, response, data=None):
        """保存响应到缓存"""
        if not self.use_cache:
            return
        
        cache_path = self._get_cache_path(url, method, data)
        
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'method': method,
                'response': response
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False)
                
            logger.debug(f"保存到缓存: {url}")
            
        except Exception as e:
            logger.warning(f"保存缓存出错: {str(e)}")
    
    def request(self, method, url, **kwargs):
        """发送HTTP请求
        
        Args:
            method (str): 请求方法 (GET, POST, etc.)
            url (str): 请求URL
            **kwargs: requests库的其他参数
        
        Returns:
            dict: 包含状态码、响应内容等信息的字典
        """
        method = method.upper()
        data = kwargs.get('data') or kwargs.get('json')
        
        # 尝试从缓存获取
        cached_response = self._get_from_cache(url, method, data)
        if cached_response:
            return cached_response
        
        # 限流控制
        self.throttler.wait_if_needed(url)
        
        # 随机延迟
        self._add_random_delay()
        
        # 设置随机用户代理
        headers = kwargs.get('headers', {})
        headers['User-Agent'] = headers.get('User-Agent', self._get_random_user_agent())
        kwargs['headers'] = headers
        
        # 设置超时
        kwargs['timeout'] = kwargs.get('timeout', self.timeout)
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            # 处理响应
            result = {
                'success': True,
                'status_code': response.status_code,
                'url': response.url,
                'headers': dict(response.headers),
                'content_type': response.headers.get('Content-Type', ''),
                'text': response.text,
            }
            
            # 如果是JSON响应，解析JSON
            if 'application/json' in response.headers.get('Content-Type', '').lower():
                result['json'] = response.json()
            
            # 保存到缓存
            self._save_to_cache(url, method, result, data)
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {url}, 错误: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'url': url
            }
    
    def get(self, url, **kwargs):
        """发送GET请求"""
        return self.request('GET', url, **kwargs)
    
    def post(self, url, **kwargs):
        """发送POST请求"""
        return self.request('POST', url, **kwargs)
    
    def put(self, url, **kwargs):
        """发送PUT请求"""
        return self.request('PUT', url, **kwargs)
    
    def delete(self, url, **kwargs):
        """发送DELETE请求"""
        return self.request('DELETE', url, **kwargs)
    
    def head(self, url, **kwargs):
        """发送HEAD请求"""
        return self.request('HEAD', url, **kwargs)


class ProxyManager:
    """代理管理器"""
    
    def __init__(self, proxies=None, proxy_api=None, test_url='https://httpbin.org/ip'):
        """初始化代理管理器
        
        Args:
            proxies (list): 初始代理列表
            proxy_api (str): 代理API地址
            test_url (str): 测试代理有效性的URL
        """
        self.proxies = proxies or []
        self.proxy_api = proxy_api
        self.test_url = test_url
        self.working_proxies = []
        self.failed_proxies = {}  # {proxy: fail_count}
        self.max_fails = 3
        self.current_index = 0
    
    def add_proxy(self, proxy):
        """添加代理
        
        Args:
            proxy (str): 代理地址，格式为 http://ip:port 或 http://user:pass@ip:port
        """
        if proxy not in self.proxies:
            self.proxies.append(proxy)
    
    def get_proxy(self):
        """获取一个可用代理"""
        if not self.working_proxies:
            self.test_proxies()
        
        if not self.working_proxies:
            logger.warning("没有可用代理")
            return None
        
        # 轮询方式获取代理
        proxy = self.working_proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.working_proxies)
        return proxy
    
    def fetch_proxies_from_api(self):
        """从API获取代理列表"""
        if not self.proxy_api:
            return
        
        try:
            response = requests.get(self.proxy_api, timeout=10)
            response.raise_for_status()
            new_proxies = response.text.strip().split('\n')
            
            # 格式化代理
            for proxy in new_proxies:
                proxy = proxy.strip()
                if proxy:
                    if not proxy.startswith('http'):
                        proxy = 'http://' + proxy
                    self.add_proxy(proxy)
                    
            logger.info(f"从API获取了 {len(new_proxies)} 个代理")
            
        except Exception as e:
            logger.error(f"从API获取代理失败: {str(e)}")
    
    def test_proxy(self, proxy):
        """测试单个代理是否可用"""
        try:
            proxies = {
                'http': proxy,
                'https': proxy
            }
            
            response = requests.get(
                self.test_url, 
                proxies=proxies,
                timeout=5
            )
            response.raise_for_status()
            return True
        except Exception:
            return False
    
    def test_proxies(self):
        """测试所有代理，保留可用的"""
        import concurrent.futures
        
        # 如果代理列表为空，先从API获取
        if not self.proxies and self.proxy_api:
            self.fetch_proxies_from_api()
        
        if not self.proxies:
            return
        
        logger.info(f"测试 {len(self.proxies)} 个代理")
        self.working_proxies = []
        
        # 使用线程池并行测试代理
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_proxy = {executor.submit(self.test_proxy, proxy): proxy for proxy in self.proxies}
            for future in concurrent.futures.as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                try:
                    if future.result():
                        self.working_proxies.append(proxy)
                        logger.debug(f"代理可用: {proxy}")
                    else:
                        logger.debug(f"代理不可用: {proxy}")
                except Exception as e:
                    logger.error(f"测试代理出错: {proxy}, {str(e)}")
        
        logger.info(f"测试完成，找到 {len(self.working_proxies)} 个可用代理")
    
    def report_failure(self, proxy):
        """报告代理失败"""
        if proxy in self.failed_proxies:
            self.failed_proxies[proxy] += 1
        else:
            self.failed_proxies[proxy] = 1
        
        # 达到最大失败次数，从工作代理列表中移除
        if self.failed_proxies[proxy] >= self.max_fails:
            if proxy in self.working_proxies:
                self.working_proxies.remove(proxy)
            logger.info(f"移除不可用代理: {proxy}")


class HttpUtils:
    """HTTP工具类，提供静态方法"""
    
    @staticmethod
    def create_client(use_cache=True, use_proxy=False, **kwargs):
        """创建HTTP客户端
        
        Args:
            use_cache (bool): 是否使用缓存
            use_proxy (bool): 是否使用代理
            **kwargs: 其他参数
        
        Returns:
            HttpClient: 配置好的HTTP客户端
        """
        client = HttpClient(use_cache=use_cache, **kwargs)
        
        if use_proxy:
            proxy_api = kwargs.get('proxy_api')
            proxy_list = kwargs.get('proxies')
            proxy_manager = ProxyManager(proxies=proxy_list, proxy_api=proxy_api)
            
            # 测试并获取可用代理
            proxy = proxy_manager.get_proxy()
            if proxy:
                client.session.proxies = {
                    'http': proxy,
                    'https': proxy
                }
        
        return client
    
    @staticmethod
    def parse_url(url, base_url=None):
        """解析URL，如果是相对URL则与base_url合并
        
        Args:
            url (str): 要解析的URL
            base_url (str): 基础URL
        
        Returns:
            str: 解析后的URL
        """
        if base_url and not urlparse(url).netloc:
            return urljoin(base_url, url)
        return url
    
    @staticmethod
    @lru_cache(maxsize=128)
    def is_valid_url(url):
        """检查URL是否有效
        
        Args:
            url (str): URL
        
        Returns:
            bool: 是否有效
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @staticmethod
    def normalize_url(url):
        """标准化URL
        
        Args:
            url (str): 输入URL
        
        Returns:
            str: 标准化后的URL
        """
        parsed = urlparse(url)
        # 确保有协议
        scheme = parsed.scheme or 'http'
        # 移除尾部斜杠
        path = parsed.path
        if path.endswith('/') and path != '/':
            path = path[:-1]
        # 重构URL
        return f"{scheme}://{parsed.netloc}{path}{parsed.params}{parsed.query}"


# 导出默认HTTP客户端实例，方便直接使用
default_client = HttpClient()
get = default_client.get
post = default_client.post
put = default_client.put
delete = default_client.delete
head = default_client.head