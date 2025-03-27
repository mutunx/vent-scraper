# 爬虫文档

本文档提供了Vent-Scraper项目中已实现的爬虫详细信息，包括它们的功能、工作原理以及如何使用它们。

## 目录

1. [爬虫概述](#1-爬虫概述)
2. [基本爬虫架构](#2-基本爬虫架构)
3. [已实现爬虫](#3-已实现爬虫)
4. [添加新爬虫](#4-添加新爬虫)

## 1. 爬虫概述

Vent-Scraper项目采用模块化的爬虫架构，每个爬虫负责抓取一个特定网站的数据。所有爬虫都继承自基本爬虫类（`BaseScraper`），确保一致的接口和行为。

爬虫的核心功能包括：

- **数据抓取**: 从指定网站获取数据
- **数据解析**: 将网页内容解析为结构化数据
- **数据处理**: 对数据进行清洗、标准化和丰富
- **数据存储**: 将数据保存到周数据文件中，支持增量更新

## 2. 基本爬虫架构

所有爬虫都必须实现以下接口：

```python
class BaseScraper:
    def get_source_id(self):
        """返回源标识符，用于保存和检索数据"""
        pass
    
    def get_source_name(self):
        """返回源的人类可读名称"""
        pass
    
    def scrape(self):
        """执行实际的爬取操作，返回爬取的数据"""
        pass
```

每个爬虫应该返回以下格式的数据：

```json
{
  "meta": {
    "source_id": "jandan",
    "source_name": "煎蛋网",
    "timestamp": "2023-05-15T12:34:56.789Z",
    "version": "1.0",
    "icon": "jandan.png"
  },
  "data": [
    {
      "id": "unique_id_1",
      "title": "文章标题",
      "content": "文章内容",
      "author": "作者名称",
      "date": "2023-05-15T10:30:00Z",
      "url": "https://example.com/article/1",
      "score": 42,
      "comments": [
        {
          "id": "comment_1",
          "author": "评论作者",
          "content": "评论内容",
          "date": "2023-05-15T11:00:00Z",
          "votes": 10
        }
      ]
    }
  ]
}
```

所有爬虫数据都将组织在以下目录结构中：

```
data/
  ├── jandan/
  │   ├── week_2023-05-15.json  # 包含2023-05-15所在周的数据
  │   ├── week_2023-05-08.json  # 包含2023-05-08所在周的数据
  │   ├── archive/             # 归档的旧数据
  │   │   ├── week_2023-01-02.json
  │   │   └── ...
  │   └── index.json           # 源索引文件
  └── another_source/
      └── ...
icons/
  ├── jandan.png               # 数据源图标
  └── another_source.png       # 另一个数据源的图标
```

## 3. 已实现爬虫

### 3.1 煎蛋网爬虫 (jandan)

**源ID**: `jandan`  
**源名称**: 煎蛋网  
**数据类型**: 网络趣味内容  

#### 3.1.1 功能

煎蛋网爬虫从煎蛋网抓取趣味内容，包括文章和评论。它支持：

- 抓取热门文章
- 收集评论及其投票信息
- 跟踪内容评分变化

#### 3.1.2 数据结构

```json
{
  "id": "post_12345",
  "title": "有趣的标题",
  "content": "文章内容...",
  "author": "发布者",
  "date": "2023-05-15T10:30:00Z",
  "url": "https://jandan.net/p/12345",
  "score": 42,
  "comments": [
    {
      "id": "comment_67890",
      "author": "评论者",
      "content": "评论内容...",
      "date": "2023-05-15T11:00:00Z",
      "votes": {
        "support": 10,
        "oppose": 2
      }
    }
  ]
}
```

#### 3.1.3 使用方法

```bash
# 运行煎蛋网爬虫
python src/main.py run jandan

# 查看最近一周数据
python src/main.py get-data jandan --view

# 查看历史数据
python src/main.py list-weeks jandan
python src/main.py get-data jandan 2023-05-08 --view
```

### 3.2 示例爬虫 (example)

**源ID**: `example`  
**源名称**: 示例源  
**数据类型**: 示例数据  

#### 3.2.1 功能

示例爬虫演示了创建新爬虫的基本结构和工作流程。它不从实际网站抓取数据，而是生成示例数据。

#### 3.2.2 数据结构

```json
{
  "id": "example_1",
  "title": "示例标题",
  "content": "示例内容...",
  "author": "示例作者",
  "date": "2023-05-15T10:30:00Z",
  "url": "https://example.com/1",
  "score": 0,
  "comments": []
}
```

#### 3.2.3 使用方法

```bash
# 运行示例爬虫
python src/main.py run example

# 查看数据
python src/main.py get-data example --view
```

## 4. 添加新爬虫

要添加新爬虫，请按照以下步骤操作：

### 4.1 创建爬虫类文件

在`src/scrapers`目录中创建一个新文件，命名为`<source_id>_scraper.py`：

```python
from scrapers.base_scraper import BaseScraper
from utils.logger import get_logger
from datetime import datetime
import re
import json

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
            
            # 2. 解析数据
            data_items = []
            # ... 实现解析逻辑 ...
            
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

### 4.2 添加源图标

为新爬虫准备一个图标文件（推荐PNG格式，尺寸为128x128像素），并使用上传图标命令添加：

```bash
python src/main.py upload-icon new_source path/to/icon.png
```

图标将被复制到`icons/`目录并在数据文件中引用。

### 4.3 实现数据解析逻辑

根据目标网站的结构，实现数据解析逻辑。可以使用以下工具：

- **BeautifulSoup**: 用于HTML解析
- **re**: 用于正则表达式匹配
- **json**: 用于解析JSON API响应

示例HTML解析代码：

```python
from bs4 import BeautifulSoup

def scrape(self):
    # ... 前面的代码 ...
    
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找所有文章元素
    articles = soup.select('div.article')
    
    data_items = []
    for article in articles:
        # 提取文章信息
        item = {
            "id": article.get('id', ''),
            "title": article.select_one('h2.title').text.strip(),
            "content": article.select_one('div.content').text.strip(),
            "author": article.select_one('span.author').text.strip(),
            "date": article.select_one('time').get('datetime', ''),
            "url": article.select_one('a.link').get('href', ''),
            "score": int(article.select_one('span.score').text.strip()),
            "comments": []
        }
        
        # 提取评论
        comment_elements = article.select('div.comment')
        for comment in comment_elements:
            comment_item = {
                "id": comment.get('id', ''),
                "author": comment.select_one('span.comment-author').text.strip(),
                "content": comment.select_one('div.comment-content').text.strip(),
                "date": comment.select_one('time').get('datetime', ''),
                "votes": int(comment.select_one('span.votes').text.strip())
            }
            item["comments"].append(comment_item)
        
        data_items.append(item)
    
    # ... 后面的代码 ...
```

### 4.4 处理增量更新

Vent-Scraper现在支持增量更新，这意味着您可以只更新现有内容的部分字段（例如评论）而不是覆盖整个数据。默认实现已经处理了：

1. 将数据保存到周数据文件中，而不是每天一个文件
2. 自动合并新数据和现有数据，保留所有帖子并更新评论

如果您需要自定义增量更新逻辑，可以重写`save_data`方法：

```python
def save_data(self, data, date=None):
    """自定义数据保存逻辑"""
    # 调用基类方法以保存数据并处理增量更新
    filepath = super().save_data(data, date)
    
    # 执行额外操作
    logger.info(f"数据已保存到: {filepath}")
    
    return filepath
```

### 4.5 测试新爬虫

爬虫完成后，使用以下命令进行测试：

```bash
# 运行爬虫
python src/main.py run new_source

# 验证数据保存情况
python src/main.py list-weeks new_source
python src/main.py get-data new_source --view
``` 