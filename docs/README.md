# Vent-Scraper

Vent-Scraper是一个灵活的网络爬虫框架，用于自动收集、处理和存储网络信息。

## 项目概述

该项目提供了一个模块化架构，支持添加多种不同网站的爬虫，通过统一的接口和数据格式将结果保存到本地文件系统。目前已实现对煎蛋网热门评论的爬取。

## 主要功能

- **自动数据爬取**：支持按计划自动爬取各种网站的数据
- **数据标准化**：将不同来源的数据转换为统一格式存储
- **历史数据管理**：提供历史数据的存储和归档机制
- **灵活的扩展性**：可通过添加新的爬虫类轻松支持更多数据源
- **命令行界面**：提供简单易用的命令行工具管理爬虫任务

## 快速开始

### 安装依赖

```bash
pip install requests beautifulsoup4 lxml
```

### 运行爬虫

```bash
# 运行所有爬虫
python src/main.py run all

# 运行特定爬虫
python src/main.py run jandan
```

### 查看数据

```bash
# 列出所有可用的爬虫源
python src/main.py list-sources

# 列出特定源的可用日期
python src/main.py list-dates jandan

# 获取并查看特定源和日期的数据
python src/main.py get-data jandan 2023-05-15 --view
```

## 自动化部署

本项目通过GitHub Actions实现每日自动爬取数据：

- 每天UTC时间2点（北京时间10点）自动运行爬虫
- 自动归档30天以前的旧数据
- 自动提交变更到仓库

## 文档索引

- [系统架构](architecture.md)
- [模块详解](modules.md)
- [爬虫实现](scrapers.md)
- [API参考](api_reference.md)
- [扩展指南](extension_guide.md)

## 许可证

MIT 