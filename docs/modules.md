# 模块文档

本文档详细介绍Vent-Scraper项目的核心模块及其功能。

## 目录

1. [主程序模块](#1-主程序模块)
2. [爬虫模块](#2-爬虫模块)
3. [工具模块](#3-工具模块)
4. [配置模块](#4-配置模块)

## 1. 主程序模块

主程序模块是项目的入口点，处理命令行参数并执行相应操作。

### 1.1 `src/main.py`

这是项目的主要入口点，提供命令行接口以执行各种操作：

- **运行爬虫**: 执行特定或所有爬虫
- **列出爬虫源**: 显示所有可用的爬虫源
- **列出周数据**: 显示指定源的所有可用周数据
- **获取数据**: 获取并显示或保存特定源和日期的数据
- **归档数据**: 归档指定源的旧数据，保留最近的指定周数
- **上传图标**: 为数据源上传或更新图标

```python
# 示例命令：
python src/main.py run jandan            # 运行jandan爬虫
python src/main.py list-sources           # 列出所有爬虫源
python src/main.py list-weeks jandan      # 列出jandan爬虫的所有可用周数据
python src/main.py get-data jandan 2023-05-15 --view  # 查看数据
python src/main.py archive jandan --weeks 12  # 归档jandan的旧数据，保留最近12周
python src/main.py upload-icon jandan path/to/icon.png  # 上传jandan源的图标
```

## 2. 爬虫模块

爬虫模块包含爬虫注册中心和各种实现的爬虫类。

### 2.1 `src/scrapers/registry.py`

爬虫注册中心负责管理所有爬虫，提供以下功能：

- **注册爬虫**: 自动搜索并注册所有符合条件的爬虫类
- **获取爬虫**: 通过ID获取爬虫实例
- **运行爬虫**: 执行特定ID的爬虫
- **运行所有爬虫**: 执行所有注册的爬虫

```python
from scrapers.registry import (
    get_available_scrapers, 
    get_scraper, 
    run_scraper, 
    run_all_scrapers
)

# 获取所有可用爬虫ID
scraper_ids = get_available_scrapers()
print(scraper_ids)  # ['jandan', 'new_source', ...]

# 运行特定爬虫
result = run_scraper('jandan')
if result:
    print("爬取成功")
else:
    print("爬取失败")
```

### 2.2 `src/scrapers/base_scraper.py`

爬虫基类定义了所有爬虫的通用接口和基本功能：

- **获取源信息**: 提供源ID和名称
- **网络请求**: 获取页面内容和发送POST请求
- **数据保存**: 将爬取的数据保存到周文件中，支持增量更新

```python
class BaseScraper:
    """爬虫基类，定义爬虫的通用接口和基本功能"""
    
    def get_source_id(self):
        """返回源标识符"""
        raise NotImplementedError
    
    def get_source_name(self):
        """返回源名称"""
        raise NotImplementedError
    
    def scrape(self):
        """执行爬取操作"""
        raise NotImplementedError
    
    def fetch_page(self, url, max_retries=3, delay=(1, 3)):
        """获取页面内容"""
        # 实现内容省略
    
    def save_data(self, data, date=None):
        """保存数据到周文件，支持增量更新"""
        # 实现内容省略
```

### 2.3 各爬虫实现

项目包含多个爬虫实现，每个爬虫负责抓取特定网站的数据：

1. **`src/scrapers/jandan_scraper.py`**: 煎蛋网爬虫，用于抓取煎蛋网的热门内容
2. **`src/scrapers/example_scraper.py`**: 示例爬虫，用于展示爬虫实现的基本结构

## 3. 工具模块

工具模块提供了爬虫和主程序使用的工具函数。

### 3.1 `src/utils/storage_utils.py`

存储工具模块，提供数据存储和检索功能：

- **获取周起始日期**: 计算指定日期所在周的起始日期（周一）
- **数据检索**: 根据源ID和日期获取数据
- **列出可用周**: 列出特定源的所有可用周数据
- **数据合并**: 将新数据与现有数据合并，实现增量更新
- **保存周数据**: 将数据保存到适当的周文件中
- **索引更新**: 维护源索引
- **归档旧数据**: 将旧数据移动到归档目录

```python
from utils.storage_utils import (
    get_week_start_date,
    get_data_by_source_and_date,
    list_available_weeks,
    merge_data,
    save_weekly_data,
    archive_old_data
)

# 获取周起始日期
start_date = get_week_start_date("2023-05-15")
print(f"2023-05-15所在周的起始日期: {start_date}")  # 2023-05-15

# 获取数据
data = get_data_by_source_and_date("jandan", "2023-05-15")

# 列出可用周
weeks = list_available_weeks("jandan")
print(f"可用周: {weeks}")
```

### 3.2 `src/utils/http_utils.py`

HTTP工具模块，提供网络请求功能：

- **创建客户端**: 创建带缓存的HTTP客户端
- **GET请求**: 发送GET请求获取数据
- **POST请求**: 发送POST请求提交数据
- **请求限流**: 控制请求频率，避免过度请求

```python
from utils.http_utils import HttpUtils, RequestThrottler

# 创建HTTP客户端
http_client = HttpUtils.create_client(use_cache=True, cache_ttl=3600)

# 发送GET请求
response = http_client.get("https://example.com/api")

# 使用限流器控制请求频率
throttler = RequestThrottler(min_interval=2.0)
throttler.wait_if_needed("https://example.com/api")
```

### 3.3 `src/utils/logger.py`

日志工具模块，提供日志记录功能：

- **配置日志**: 设置日志输出格式和级别
- **获取日志器**: 获取特定名称的日志器

```python
from utils.logger import get_logger

# 获取日志器
logger = get_logger("my_module")

# 记录日志
logger.info("操作成功")
logger.error("操作失败", exc_info=True)
```

## 4. 配置模块

配置模块管理项目全局配置。

### 4.1 `src/config.py`

配置模块定义项目全局配置：

- **数据目录**: 存储数据文件的目录
- **图标目录**: 存储数据源图标的目录
- **日志目录**: 存储日志文件的目录
- **缓存配置**: HTTP请求缓存设置
- **请求设置**: 请求超时和重试设置

```python
from config import (
    DATA_DIR, 
    ICONS_DIR,
    LOG_DIR, 
    HTTP_CACHE_TTL, 
    REQUEST_TIMEOUT
)

# 使用配置
print(f"数据目录: {DATA_DIR}")
print(f"图标目录: {ICONS_DIR}")
print(f"HTTP缓存过期时间: {HTTP_CACHE_TTL}秒")
``` 