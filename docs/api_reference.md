# API参考

本文档详细说明Vent-Scraper项目中各模块的API接口，便于开发者理解和使用。

## 目录

1. [命令行接口](#1-命令行接口)
2. [爬虫注册中心 API](#2-爬虫注册中心-api)
3. [爬虫基类 API](#3-爬虫基类-api)
4. [HTTP工具 API](#4-http工具-api)
5. [存储工具 API](#5-存储工具-api)

## 1. 命令行接口

Vent-Scraper提供了命令行接口，用于执行爬虫任务和管理数据。

### 1.1 运行爬虫

```bash
# 运行特定爬虫
python src/main.py run <source_id>

# 运行所有爬虫
python src/main.py run all
```

### 1.2 列出爬虫源

```bash
# 列出所有可用的爬虫源
python src/main.py list-sources
```

输出示例：
```
可用的爬虫源:
- jandan (已抓取数据)
- new_site (未抓取数据)
```

### 1.3 列出周数据

```bash
# 列出指定源的所有可用周数据
python src/main.py list-weeks <source_id>
```

输出示例：
```
源 jandan 的可用周数据:
- 2023-05-15 (周数据)
- 2023-05-08 (周数据)
- 2023-05-01 (周数据)
```

### 1.4 获取数据

```bash
# 获取并显示数据
python src/main.py get-data <source_id> <date> --view

# 获取并保存数据到文件
python src/main.py get-data <source_id> <date> --output <output_file>
```

### 1.5 归档数据

```bash
# 归档特定源的旧数据，保留最近12周
python src/main.py archive <source_id>

# 归档所有源的旧数据，保留最近指定周数
python src/main.py archive all --weeks 24
```

### 1.6 上传图标

```bash
# 上传或更新数据源的图标
python src/main.py upload-icon <source_id> <icon_file>
```

## 2. 爬虫注册中心 API

爬虫注册中心提供了管理和访问爬虫的接口。

### 2.1 获取可用爬虫列表

```python
from scrapers.registry import get_available_scrapers

# 获取所有注册的爬虫ID列表
scraper_ids = get_available_scrapers()
print(scraper_ids)  # ['jandan', 'new_site', ...]
```

### 2.2 获取爬虫实例

```python
from scrapers.registry import get_scraper

# 获取特定ID的爬虫实例
try:
    scraper = get_scraper('jandan')
    print(f"获取到爬虫: {scraper.get_source_name()}")
except ValueError as e:
    print(f"错误: {str(e)}")
```

### 2.3 运行特定爬虫

```python
from scrapers.registry import run_scraper

# 运行特定ID的爬虫
result = run_scraper('jandan')
if result:
    print("爬取成功")
else:
    print("爬取失败")
```

### 2.4 运行所有爬虫

```python
from scrapers.registry import run_all_scrapers

# 运行所有注册的爬虫
results = run_all_scrapers()
for source_id, result in results.items():
    status = "成功" if result else "失败"
    print(f"爬虫 {source_id}: {status}")
```

## 3. 爬虫基类 API

爬虫基类定义了所有爬虫共享的接口和基本功能。

### 3.1 创建新爬虫

```python
from scrapers.base_scraper import BaseScraper

class MyScraper(BaseScraper):
    """我的自定义爬虫"""
    
    def get_source_id(self):
        """返回源标识符"""
        return "my_source"
    
    def get_source_name(self):
        """返回源名称"""
        return "我的数据源"
    
    def scrape(self):
        """执行爬取操作"""
        # 实现爬取逻辑
        return {
            "meta": {
                "source_id": self.source_id,
                "source_name": self.source_name,
                "timestamp": datetime.now().isoformat(),
                "version": "1.0"
            },
            "data": []  # 爬取的数据
        }
```

### 3.2 获取页面内容

```python
# 在爬虫类中使用
html_content = self.fetch_page("https://example.com/page", max_retries=3, delay=(1, 3))
if html_content:
    # 处理页面内容
    pass
else:
    logger.error("获取页面失败")
```

### 3.3 发送POST请求

```python
# 在爬虫类中使用
data = {"username": "test", "password": "password"}
response = self.post_request("https://example.com/api", data=data)
if response:
    # 处理响应
    pass
else:
    logger.error("POST请求失败")
```

### 3.4 保存数据

```python
# 在爬虫类中使用
data = {
    "meta": {
        "source_id": self.source_id,
        "source_name": self.source_name,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0",
        "icon": f"{self.source_id}.png"  # 添加图标引用
    },
    "data": [...]  # 爬取的数据
}

# 保存到当前周的数据文件，如有现有数据会进行增量更新
filepath = self.save_data(data)
print(f"数据已保存到: {filepath}")

# 保存到指定日期所在周的数据文件
filepath = self.save_data(data, date="2023-05-15")
print(f"数据已保存到: {filepath}")
```

## 4. HTTP工具 API

HTTP工具提供了高级的HTTP请求功能。

### 4.1 创建HTTP客户端

```python
from utils.http_utils import HttpUtils

# 创建带缓存的HTTP客户端
http_client = HttpUtils.create_client(
    use_cache=True,
    cache_dir='.my_cache',
    cache_ttl=3600  # 缓存1小时
)
```

### 4.2 发送GET请求

```python
# 发送GET请求
response = http_client.get("https://example.com/api")
if response.get('success'):
    # 处理响应数据
    data = response.get('json')
    print(f"获取到数据: {data}")
else:
    print(f"请求失败: {response.get('error')}")
```

### 4.3 发送POST请求

```python
# 发送POST请求（表单数据）
form_data = {"username": "test", "password": "password"}
response = http_client.post("https://example.com/api", data=form_data)

# 发送POST请求（JSON数据）
json_data = {"query": "test", "limit": 10}
response = http_client.post("https://example.com/api", json_data=json_data)
```

### 4.4 请求限流器

```python
from utils.http_utils import RequestThrottler

# 创建限流器，同一域名两次请求间隔至少2秒
throttler = RequestThrottler(min_interval=2.0)

# 在请求前等待适当的时间
throttler.wait_if_needed("https://example.com/api")
```

## 5. 存储工具 API

存储工具提供了数据管理的接口。

### 5.1 获取特定数据

```python
from utils.storage_utils import get_data_by_source_and_date

# 获取特定源和日期的数据（会自动定位到该日期所在周的数据文件）
data = get_data_by_source_and_date("jandan", "2023-05-15")
if data:
    print(f"获取数据成功，包含 {len(data.get('data', []))} 条记录")
else:
    print("获取数据失败")
```

### 5.2 获取周起始日期

```python
from utils.storage_utils import get_week_start_date

# 获取当前日期所在周的周一日期
current_week_start = get_week_start_date()
print(f"当前周的起始日期: {current_week_start}")

# 获取指定日期所在周的周一日期
week_start = get_week_start_date("2023-05-15")
print(f"该日期所在周的起始日期: {week_start}")
```

### 5.3 列出可用周数据

```python
from utils.storage_utils import list_available_weeks

# 列出特定源的所有可用周数据
weeks = list_available_weeks("jandan")
print(f"源 jandan 有 {len(weeks)} 个可用周数据:")
for week in weeks:
    print(f"- {week}")
```

### 5.4 列出所有数据源

```python
from utils.storage_utils import list_all_sources

# 列出所有可用的数据源
sources = list_all_sources()
print(f"有 {len(sources)} 个可用数据源:")
for source in sources:
    print(f"- {source}")
```

### 5.5 合并和更新数据

```python
from utils.storage_utils import merge_data

# 获取现有数据
existing_data = get_data_by_source_and_date("jandan", "2023-05-15")

# 准备新数据
new_data = {
    "meta": {
        "source_id": "jandan",
        "source_name": "煎蛋网",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0"
    },
    "data": [...]  # 新爬取的数据
}

# 合并数据（实现增量更新）
merged_data = merge_data("jandan", new_data, "2023-05-15")
```

### 5.6 保存周数据

```python
from utils.storage_utils import save_weekly_data

# 保存数据到指定周（会进行增量更新）
filepath = save_weekly_data("jandan", data, "2023-05-15")
print(f"数据已保存到: {filepath}")
```

### 5.7 归档旧数据

```python
from utils.storage_utils import archive_old_data

# 归档特定源的旧数据，保留最近12周
result = archive_old_data("jandan", 12)
if result:
    print("归档成功")
else:
    print("没有需要归档的数据")
``` 