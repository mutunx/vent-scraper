"""
爬虫注册中心，用于管理和获取所有可用的爬虫
"""

from .jandan_scraper import JandanScraper

# 注册所有可用的爬虫
SCRAPERS = {
    "jandan": JandanScraper,
    # 后续可以添加更多爬虫
    # "v2ex": V2EXScraper,
    # "baidu": BaiduScraper,
}

def get_available_scrapers():
    """获取所有可用的爬虫列表"""
    return list(SCRAPERS.keys())

def get_scraper(source_id):
    """根据源ID获取爬虫实例"""
    if source_id in SCRAPERS:
        return SCRAPERS[source_id]()
    else:
        raise ValueError(f"未知的爬虫源: {source_id}")

def run_scraper(source_id):
    """运行指定的爬虫"""
    scraper = get_scraper(source_id)
    return scraper.run()

def run_all_scrapers():
    """运行所有注册的爬虫"""
    results = {}
    for source_id in SCRAPERS:
        try:
            scraper = get_scraper(source_id)
            results[source_id] = scraper.run()
        except Exception as e:
            # 记录错误日志
            import traceback
            import logging
            logging.error(f"运行爬虫 {source_id} 时出错: {str(e)}")
            logging.error(f"堆栈信息: {traceback.format_exc()}")
            results[source_id] = None
    return results