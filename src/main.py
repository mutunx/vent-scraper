import argparse
import logging
import sys
import os
from datetime import datetime
from scrapers.registry import get_available_scrapers, run_scraper, run_all_scrapers
from utils.storage_utils import get_data_by_source_and_date, list_available_weeks, list_all_sources, archive_old_data

# 首先创建必要的目录，确保日志目录存在
def create_directories():
    """创建必要的目录"""
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("icons", exist_ok=True)  # 新增图标目录

# 在配置日志之前创建目录
create_directories()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join("logs", f"scraper_{datetime.now().strftime('%Y%m%d')}.log"), encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

def run(args):
    """运行爬虫"""
    if args.source == "all":
        logger.info("运行所有爬虫")
        results = run_all_scrapers()
        success_count = sum(1 for r in results.values() if r is not None)
        logger.info(f"完成: {success_count}/{len(results)} 个爬虫成功运行")
    else:
        logger.info(f"运行爬虫: {args.source}")
        result = run_scraper(args.source)
        if result:
            logger.info(f"爬虫 {args.source} 成功运行")
        else:
            logger.error(f"爬虫 {args.source} 运行失败")

def list_sources(args):
    """列出所有可用的爬虫源"""
    available_scrapers = get_available_scrapers()
    existing_sources = list_all_sources()
    
    print("可用的爬虫源:")
    for source in available_scrapers:
        status = "已抓取数据" if source in existing_sources else "未抓取数据"
        print(f"- {source} ({status})")

def list_weeks(args):
    """列出指定源的所有可用周"""
    weeks = list_available_weeks(args.source)
    if not weeks:
        print(f"无可用周数据，源: {args.source}")
        return
    
    print(f"源 {args.source} 的可用周数据:")
    for week in weeks:
        print(f"- {week} (周数据)")

def get_data(args):
    """获取指定源和日期的数据"""
    data = get_data_by_source_and_date(args.source, args.date)
    if data:
        print(f"获取数据成功: {args.source}/{args.date}")
        if args.output:
            import json
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"数据已保存到: {args.output}")
        elif args.view:
            import json
            print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"获取数据失败: {args.source}/{args.date}")

def archive(args):
    """归档旧数据"""
    if args.source == "all":
        logger.info("归档所有源的旧数据")
        sources = list_all_sources()
        for source in sources:
            result = archive_old_data(source, args.weeks)
            status = "成功" if result else "无需归档"
            logger.info(f"源 {source} 归档 {status}")
    else:
        logger.info(f"归档源 {args.source} 的旧数据")
        result = archive_old_data(args.source, args.weeks)
        status = "成功" if result else "无需归档"
        logger.info(f"源 {args.source} 归档 {status}")

def upload_icon(args):
    """上传或更新数据源图标"""
    source_id = args.source
    
    # 确保图标目录存在
    icons_dir = os.path.join("icons")
    os.makedirs(icons_dir, exist_ok=True)
    
    # 目标文件路径
    target_path = os.path.join(icons_dir, f"{source_id}.png")
    
    # 复制图标文件
    try:
        import shutil
        shutil.copy2(args.icon_file, target_path)
        print(f"图标已更新: {target_path}")
    except Exception as e:
        print(f"上传图标失败: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="网站爬虫工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 运行爬虫
    run_parser = subparsers.add_parser("run", help="运行爬虫")
    run_parser.add_argument("source", choices=get_available_scrapers() + ["all"], help="爬虫源ID")
    
    # 列出源
    list_sources_parser = subparsers.add_parser("list-sources", help="列出所有可用的爬虫源")
    
    # 列出周
    list_weeks_parser = subparsers.add_parser("list-weeks", help="列出指定源的所有可用周数据")
    list_weeks_parser.add_argument("source", help="源ID")
    
    # 获取数据
    get_data_parser = subparsers.add_parser("get-data", help="获取指定源和日期的数据")
    get_data_parser.add_argument("source", help="源ID")
    get_data_parser.add_argument("date", help="日期 (YYYY-MM-DD)")
    get_data_parser.add_argument("--output", "-o", help="输出文件路径")
    get_data_parser.add_argument("--view", "-v", action="store_true", help="显示数据内容")
    
    # 归档
    archive_parser = subparsers.add_parser("archive", help="归档旧数据")
    archive_parser.add_argument("source", nargs="?", default="all", help="源ID (默认: all)")
    archive_parser.add_argument("--weeks", "-w", type=int, default=12, help="保留最近几周的数据 (默认: 12)")
    
    # 上传图标
    icon_parser = subparsers.add_parser("upload-icon", help="上传或更新数据源图标")
    icon_parser.add_argument("source", help="源ID")
    icon_parser.add_argument("icon_file", help="图标文件路径 (PNG格式)")
    
    args = parser.parse_args()
    
    if args.command == "run":
        run(args)
    elif args.command == "list-sources":
        list_sources(args)
    elif args.command == "list-weeks":
        list_weeks(args)
    elif args.command == "get-data":
        get_data(args)
    elif args.command == "archive":
        archive(args)
    elif args.command == "upload-icon":
        upload_icon(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()