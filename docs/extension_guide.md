# 扩展指南

本文档提供了如何扩展Vent-Scraper项目功能的详细指南，包括添加新爬虫、自定义数据处理、扩展存储方法等。

## 目录

1. [添加新爬虫](#1-添加新爬虫)
2. [自定义数据处理](#2-自定义数据处理)
3. [扩展存储方法](#3-扩展存储方法)
4. [添加新命令](#4-添加新命令)
5. [高级扩展](#5-高级扩展)

## 1. 添加新爬虫

### 1.1 创建新爬虫类

在`src/scrapers`目录中创建一个新的Python文件，命名为`<source_id>_scraper.py`。实现一个继承自`BaseScraper`的新爬虫类：

```python
from scrapers.base_scraper import BaseScraper
from utils.logger import get_logger
from datetime import datetime

logger = get_logger("new_scraper")

class NewScraper(BaseScraper):
    """新网站爬虫"""
    
    def get_source_id(self):
        """返回源标识符"""
        return "new_source"
    
    def get_source_name(self):
        """返回源名称"""
        return "新数据源"
    
    def scrape(self):
        """执行爬取操作"""
        try:
            # 1. 获取数据页面
            url = "https://example.com/data"
            html_content = self.fetch_page(url)
            if not html_content:
                logger.error("无法获取页面内容")
                return None
            
            # 2. 解析数据（使用适当的解析库，如BeautifulSoup或re）
            # 以下为示例代码
            data_items = []
            # ... 解析逻辑 ...
            
            # 3. 构建结果数据
            result = {
                "meta": {
                    "source_id": self.get_source_id(),
                    "source_name": self.get_source_name(),
                    "timestamp": datetime.now().isoformat(),
                    "version": "1.0"
                },
                "data": data_items
            }
            
            return result
            
        except Exception as e:
            logger.error(f"爬取过程中发生错误: {str(e)}", exc_info=True)
            return None
```

### 1.2 添加源图标

为新爬虫源准备一个图标文件（推荐PNG格式，尺寸为128x128像素），并使用上传图标命令添加：

```bash
python src/main.py upload-icon new_source path/to/icon.png
```

### 1.3 注册爬虫

爬虫注册中心会自动搜索并注册符合条件的爬虫类，只要满足以下条件：

1. 文件位于`src/scrapers`目录中
2. 文件名以`_scraper.py`结尾
3. 文件中包含一个继承自`BaseScraper`的类

您无需手动注册爬虫，系统会自动发现您的新爬虫。

### 1.4 测试新爬虫

使用命令行工具测试新爬虫：

```bash
# 运行新爬虫
python src/main.py run new_source

# 验证数据保存情况
python src/main.py list-weeks new_source
```

## 2. 自定义数据处理

### 2.1 重写`save_data`方法

您可以在爬虫类中重写`save_data`方法，自定义数据保存逻辑：

```python
def save_data(self, data, date=None):
    """自定义数据保存逻辑"""
    # 0. 调用父类方法保存标准格式数据
    filepath = super().save_data(data, date)
    
    # 1. 执行额外的数据处理
    # 例如：生成数据分析报告
    self._generate_report(data, filepath)
    
    return filepath

def _generate_report(self, data, filepath):
    """生成数据分析报告"""
    # 报告生成逻辑
    report_path = filepath.replace('.json', '_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"数据分析报告\n")
        f.write(f"源：{data['meta']['source_name']}\n")
        f.write(f"时间：{data['meta']['timestamp']}\n")
        f.write(f"数据条目：{len(data['data'])}\n")
        # 添加更多分析内容
```

### 2.2 添加数据分析功能

您可以在爬虫类中添加数据分析方法：

```python
def analyze_data(self, date=None):
    """分析特定日期（所在周）的数据"""
    from utils.storage_utils import get_data_by_source_and_date
    
    # 获取数据
    date = date or datetime.now().strftime("%Y-%m-%d")
    data = get_data_by_source_and_date(self.get_source_id(), date)
    if not data:
        logger.error(f"无法获取日期 {date} 的数据")
        return None
    
    # 执行分析
    analysis_result = {
        "total_items": len(data.get("data", [])),
        "unique_authors": len(set(item.get("author") for item in data.get("data", []))),
        "average_comments": sum(len(item.get("comments", [])) for item in data.get("data", [])) / len(data.get("data", [])) if data.get("data") else 0
    }
    
    return analysis_result
```

## 3. 扩展存储方法

### 3.1 保存到数据库

您可以扩展`storage_utils.py`或创建一个新模块，实现将数据保存到数据库的功能：

```python
# src/utils/db_storage.py
import sqlite3
from datetime import datetime
from config import DATA_DIR
import os
import json

def save_to_db(source_id, data, db_path=None):
    """将数据保存到SQLite数据库"""
    db_path = db_path or os.path.join(DATA_DIR, f"{source_id}.db")
    
    # 创建连接
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建表（如果不存在）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS posts (
        id TEXT PRIMARY KEY,
        title TEXT,
        content TEXT,
        author TEXT,
        date TEXT,
        url TEXT,
        score INTEGER,
        comments_json TEXT,
        last_updated TEXT
    )
    ''')
    
    # 插入或更新数据
    for item in data.get("data", []):
        # 将评论转换为JSON字符串
        comments_json = json.dumps(item.get("comments", []))
        
        # 准备SQL语句和参数
        sql = '''
        INSERT OR REPLACE INTO posts 
        (id, title, content, author, date, url, score, comments_json, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            item.get("id"),
            item.get("title"),
            item.get("content"),
            item.get("author"),
            item.get("date"),
            item.get("url"),
            item.get("score", 0),
            comments_json,
            datetime.now().isoformat()
        )
        
        # 执行SQL
        cursor.execute(sql, params)
    
    # 提交并关闭
    conn.commit()
    conn.close()
    
    return db_path
```

### 3.2 导出数据为各种格式

添加函数将数据导出为不同格式：

```python
# src/utils/export_utils.py
import csv
import json
import yaml
import os
from utils.storage_utils import get_data_by_source_and_date
from datetime import datetime

def export_as_json(source_id, date=None, output_path=None):
    """导出数据为JSON格式"""
    # 获取数据
    data = get_data_by_source_and_date(source_id, date)
    if not data:
        return None
    
    # 设置输出路径
    output_path = output_path or f"{source_id}_{date or datetime.now().strftime('%Y-%m-%d')}.json"
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return output_path

def export_as_csv(source_id, date=None, output_path=None):
    """导出数据为CSV格式"""
    # 获取数据
    data = get_data_by_source_and_date(source_id, date)
    if not data:
        return None
    
    # 设置输出路径
    output_path = output_path or f"{source_id}_{date or datetime.now().strftime('%Y-%m-%d')}.csv"
    
    # 确定字段
    all_fields = set()
    for item in data.get("data", []):
        all_fields.update(item.keys())
    fields = sorted(list(all_fields))
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in data.get("data", []):
            # 对于复杂类型，转换为字符串
            row = {}
            for k, v in item.items():
                if isinstance(v, (list, dict)):
                    row[k] = json.dumps(v, ensure_ascii=False)
                else:
                    row[k] = v
            writer.writerow(row)
    
    return output_path

def export_as_yaml(source_id, date=None, output_path=None):
    """导出数据为YAML格式"""
    # 获取数据
    data = get_data_by_source_and_date(source_id, date)
    if not data:
        return None
    
    # 设置输出路径
    output_path = output_path or f"{source_id}_{date or datetime.now().strftime('%Y-%m-%d')}.yaml"
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True)
    
    return output_path
```

## 4. 添加新命令

### 4.1 添加导出命令

在`src/main.py`中添加新的命令行选项：

```python
def export_data(args):
    """导出数据为指定格式"""
    from utils.export_utils import export_as_json, export_as_csv, export_as_yaml
    
    # 检查参数
    source_id = args.source_id
    date = args.date
    fmt = args.format.lower()
    output = args.output
    
    # 根据格式选择导出函数
    if fmt == 'json':
        export_func = export_as_json
    elif fmt == 'csv':
        export_func = export_as_csv
    elif fmt == 'yaml':
        export_func = export_as_yaml
    else:
        print(f"不支持的格式: {fmt}")
        return
    
    # 执行导出
    output_path = export_func(source_id, date, output)
    if output_path:
        print(f"数据已导出到: {output_path}")
    else:
        print(f"导出失败：找不到源 {source_id} 的数据")

# 在 main() 函数中添加此命令
def main():
    # ...现有代码...
    
    # 添加导出命令
    export_parser = subparsers.add_parser('export', help='导出数据为指定格式')
    export_parser.add_argument('source_id', help='爬虫源 ID')
    export_parser.add_argument('--date', help='数据日期（默认为当前日期）')
    export_parser.add_argument('--format', choices=['json', 'csv', 'yaml'], default='json', help='导出格式')
    export_parser.add_argument('--output', help='输出文件路径')
    export_parser.set_defaults(func=export_data)
    
    # ...现有代码...
```

### 4.2 添加分析命令

添加一个数据分析命令：

```python
def analyze_data(args):
    """分析指定源的数据"""
    from scrapers.registry import get_scraper
    
    # 获取爬虫实例
    try:
        scraper = get_scraper(args.source_id)
    except ValueError as e:
        print(f"错误: {str(e)}")
        return
    
    # 检查爬虫是否实现了分析方法
    if not hasattr(scraper, 'analyze_data'):
        print(f"错误: 爬虫 {args.source_id} 没有实现分析功能")
        return
    
    # 执行分析
    result = scraper.analyze_data(args.date)
    if result:
        print(f"\n{scraper.get_source_name()} 数据分析结果:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        print(f"分析失败：无法获取或处理数据")

# 在 main() 函数中添加此命令
def main():
    # ...现有代码...
    
    # 添加分析命令
    analyze_parser = subparsers.add_parser('analyze', help='分析指定源的数据')
    analyze_parser.add_argument('source_id', help='爬虫源 ID')
    analyze_parser.add_argument('--date', help='数据日期（默认为当前日期）')
    analyze_parser.set_defaults(func=analyze_data)
    
    # ...现有代码...
```

## 5. 高级扩展

### 5.1 添加代理支持

扩展HTTP工具以支持代理：

```python
# 在 src/utils/http_utils.py 中添加代理支持

def create_client_with_proxy(proxy_url=None, use_cache=True, cache_dir=None, cache_ttl=None):
    """创建带代理的HTTP客户端"""
    import requests
    from requests_cache import CachedSession
    
    # 设置代理
    proxies = None
    if proxy_url:
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
    
    # 创建带缓存的会话
    if use_cache:
        # 设置缓存
        from config import HTTP_CACHE_DIR, HTTP_CACHE_TTL
        cache_dir = cache_dir or HTTP_CACHE_DIR
        cache_ttl = cache_ttl or HTTP_CACHE_TTL
        session = CachedSession(
            cache_name=cache_dir,
            expire_after=cache_ttl
        )
    else:
        session = requests.Session()
    
    # 设置代理
    if proxies:
        session.proxies.update(proxies)
    
    # 扩展客户端类
    class ProxyHttpClient:
        def __init__(self, session):
            self.session = session
            self.proxies = proxies
        
        def get(self, url, **kwargs):
            # ...实现与原HttpClient类似...
            pass
        
        def post(self, url, data=None, json_data=None, **kwargs):
            # ...实现与原HttpClient类似...
            pass
    
    return ProxyHttpClient(session)
```

### 5.2 并发爬取支持

添加并发爬取能力：

```python
# 创建 src/utils/concurrent_utils.py

import concurrent.futures
from typing import List, Callable, Any
from utils.logger import get_logger

logger = get_logger("concurrent")

def parallel_execute(func: Callable, items: List[Any], max_workers=5, timeout=120) -> List[Any]:
    """并行执行函数，返回结果列表"""
    results = []
    
    # 创建线程池
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交任务
        future_to_item = {executor.submit(func, item): item for item in items}
        
        # 收集结果
        for future in concurrent.futures.as_completed(future_to_item, timeout=timeout):
            item = future_to_item[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"处理 {item} 时发生错误: {str(e)}", exc_info=True)
    
    return results
```

在爬虫中使用：

```python
from utils.concurrent_utils import parallel_execute

def scrape(self):
    """使用并发爬取数据"""
    # 1. 获取页面列表
    page_urls = [f"https://example.com/page/{i}" for i in range(1, 11)]
    
    # 2. 定义页面处理函数
    def process_page(url):
        html = self.fetch_page(url)
        # 解析逻辑...
        return items  # 返回该页面的数据项
    
    # 3. 并行处理所有页面
    all_items = []
    page_results = parallel_execute(process_page, page_urls, max_workers=3)
    for items in page_results:
        if items:
            all_items.extend(items)
    
    # 4. 构建结果数据
    result = {
        "meta": {
            "source_id": self.get_source_id(),
            "source_name": self.get_source_name(),
            "timestamp": datetime.now().isoformat(),
            "version": "1.0"
        },
        "data": all_items
    }
    
    return result
```

### 5.3 增量更新实现

Vent-Scraper现已支持增量更新数据。要实现自定义增量更新逻辑，可以重写爬虫的`save_data`方法：

```python
def save_data(self, data, date=None):
    """实现自定义的增量更新逻辑"""
    from utils.storage_utils import get_data_by_source_and_date, save_weekly_data, merge_data
    
    # 1. 获取现有数据
    existing_data = get_data_by_source_and_date(self.get_source_id(), date)
    
    # 2. 如果没有现有数据，直接保存
    if not existing_data:
        return super().save_data(data, date)
    
    # 3. 自定义合并逻辑
    merged_data = {
        "meta": data["meta"],  # 使用新的元数据
        "data": []
    }
    
    # 4. 创建ID到数据项的映射
    existing_items = {item.get("id"): item for item in existing_data.get("data", [])}
    new_items = {item.get("id"): item for item in data.get("data", [])}
    
    # 5. 合并所有ID
    all_ids = set(existing_items.keys()) | set(new_items.keys())
    
    # 6. 合并数据项
    for item_id in all_ids:
        if item_id in new_items and item_id in existing_items:
            # 项目存在于两者中，合并内容
            merged_item = existing_items[item_id].copy()
            
            # 更新可能变化的字段，但保留某些历史数据
            for field in ["title", "content", "score", "updated_at"]:
                if field in new_items[item_id]:
                    merged_item[field] = new_items[item_id][field]
            
            # 特殊处理评论 - 保留所有评论
            if "comments" in new_items[item_id]:
                existing_comments = {c.get("id"): c for c in merged_item.get("comments", [])}
                for comment in new_items[item_id].get("comments", []):
                    existing_comments[comment.get("id")] = comment
                merged_item["comments"] = list(existing_comments.values())
            
            merged_data["data"].append(merged_item)
        elif item_id in new_items:
            # 仅存在于新数据中
            merged_data["data"].append(new_items[item_id])
        else:
            # 仅存在于现有数据中
            merged_data["data"].append(existing_items[item_id])
    
    # 7. 保存合并后的数据
    return save_weekly_data(self.get_source_id(), merged_data, date)
```

### 5.4 添加Web UI

您可以为Vent-Scraper添加一个简单的Web UI，用于浏览和管理数据：

```python
# src/web_ui.py
from flask import Flask, render_template, jsonify, request, redirect, url_for
from utils.storage_utils import (
    list_all_sources, 
    list_available_weeks,
    get_data_by_source_and_date
)
from scrapers.registry import get_available_scrapers, run_scraper
import os
from config import DATA_DIR, ICONS_DIR
import json

app = Flask(__name__)

@app.route('/')
def home():
    """首页，显示所有数据源"""
    sources = list_all_sources()
    return render_template('index.html', sources=sources)

@app.route('/source/<source_id>')
def source_detail(source_id):
    """数据源详情页，显示所有可用周"""
    weeks = list_available_weeks(source_id)
    return render_template('source.html', source_id=source_id, weeks=weeks)

@app.route('/source/<source_id>/<week>')
def week_data(source_id, week):
    """周数据页，显示指定周的数据"""
    data = get_data_by_source_and_date(source_id, week)
    return render_template('data.html', source_id=source_id, week=week, data=data)

@app.route('/api/sources')
def api_sources():
    """API: 获取所有数据源"""
    return jsonify(list_all_sources())

@app.route('/api/source/<source_id>/weeks')
def api_weeks(source_id):
    """API: 获取源的所有可用周"""
    return jsonify(list_available_weeks(source_id))

@app.route('/api/source/<source_id>/<week>')
def api_data(source_id, week):
    """API: 获取指定周的数据"""
    data = get_data_by_source_and_date(source_id, week)
    return jsonify(data)

@app.route('/run/<source_id>', methods=['POST'])
def run_source(source_id):
    """运行指定源的爬虫"""
    if source_id == 'all':
        # TODO: 实现运行所有爬虫
        pass
    else:
        run_scraper(source_id)
    return redirect(url_for('source_detail', source_id=source_id))

def main():
    """启动Web UI"""
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
```

要使用此Web UI，需要安装Flask并创建必要的模板：

```bash
pip install flask
```

然后创建模板文件（templates/index.html, templates/source.html, templates/data.html），实现Web界面。

### 5.5 数据导出为RSS/Atom订阅

您可以添加将数据导出为RSS或Atom订阅的功能：

```python
# src/utils/rss_utils.py
from feedgenerator import Rss201rev2Feed, Atom1Feed
from utils.storage_utils import get_data_by_source_and_date
from datetime import datetime
import os
from config import DATA_DIR

def generate_rss(source_id, date=None, output_path=None):
    """生成RSS订阅"""
    # 获取数据
    data = get_data_by_source_and_date(source_id, date)
    if not data:
        return None
    
    # 设置输出路径
    output_path = output_path or os.path.join(DATA_DIR, f"{source_id}/rss.xml")
    
    # 创建Feed
    feed = Rss201rev2Feed(
        title=data.get("meta", {}).get("source_name", source_id),
        link=f"https://example.com/feed/{source_id}",  # 替换为实际的网站URL
        description=f"{data.get('meta', {}).get('source_name', source_id)}的最新数据",
        language="zh-cn"
    )
    
    # 添加条目
    for item in data.get("data", []):
        feed.add_item(
            title=item.get("title", "无标题"),
            link=item.get("url", ""),
            description=item.get("content", ""),
            pubdate=datetime.fromisoformat(item.get("date", datetime.now().isoformat())),
            unique_id=str(item.get("id", "")),
            author_name=item.get("author", "")
        )
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        feed.write(f, 'utf-8')
    
    return output_path
```

在命令行界面中添加RSS导出命令：

```python
def export_rss(args):
    """将数据导出为RSS订阅"""
    from utils.rss_utils import generate_rss
    
    output_path = generate_rss(args.source_id, args.date, args.output)
    if output_path:
        print(f"RSS订阅已生成: {output_path}")
    else:
        print(f"生成RSS失败：找不到源 {args.source_id} 的数据")

# 在 main() 函数中添加此命令
def main():
    # ...现有代码...
    
    # 添加RSS导出命令
    rss_parser = subparsers.add_parser('export-rss', help='导出数据为RSS订阅')
    rss_parser.add_argument('source_id', help='爬虫源 ID')
    rss_parser.add_argument('--date', help='数据日期（默认为当前日期）')
    rss_parser.add_argument('--output', help='输出文件路径')
    rss_parser.set_defaults(func=export_rss)
    
    # ...现有代码...
``` 