import os
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_week_start_date(date_str=None):
    """获取指定日期所在周的周一日期
    
    Args:
        date_str (str, optional): 日期字符串 (YYYY-MM-DD)，如不指定则使用当前日期
        
    Returns:
        str: 周一的日期 (YYYY-MM-DD)
    """
    if date_str:
        date = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        date = datetime.now()
    
    # 获取周一 (0是周一，6是周日)
    days_to_subtract = date.weekday()
    monday = date - timedelta(days=days_to_subtract)
    return monday.strftime("%Y-%m-%d")

def get_data_by_source_and_date(source_id, date):
    """通过源ID和日期获取数据
    
    Args:
        source_id (str): 源ID
        date (str): 日期字符串，格式为YYYY-MM-DD
        
    Returns:
        dict: 数据对象，失败时返回None
    """
    # 获取对应周的周一日期
    week_start = get_week_start_date(date)
    
    filepath = os.path.join("data", source_id, f"week_{week_start}.json")
    
    if not os.path.exists(filepath):
        logger.warning(f"找不到数据文件: {filepath}")
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"解析JSON失败: {filepath}, 错误: {str(e)}")
            return None

def list_available_weeks(source_id):
    """列出指定源的所有可用周"""
    base_path = os.path.join("data", source_id)
    if not os.path.exists(base_path):
        return []
    
    weeks = []
    for filename in os.listdir(base_path):
        if filename.startswith('week_') and filename.endswith('.json'):
            week_date = filename.replace('week_', '').replace('.json', '')
            if is_valid_date_format(week_date):
                weeks.append(week_date)
    
    return sorted(weeks, reverse=True)

def is_valid_date_format(date_str):
    """检查日期格式是否有效 (YYYY-MM-DD)"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def get_current_week_file(source_id):
    """获取当前周的文件路径
    
    Args:
        source_id (str): 源ID
        
    Returns:
        str: 文件路径
    """
    current_week = get_week_start_date()
    return os.path.join("data", source_id, f"week_{current_week}.json")

def list_all_sources():
    """列出所有可用的数据源"""
    sources_file = os.path.join("data", "sources.json")
    if not os.path.exists(sources_file):
        return []
    
    with open(sources_file, 'r', encoding='utf-8') as f:
        try:
            sources = json.load(f)
            return list(sources.keys())
        except json.JSONDecodeError:
            return []

def get_source_info(source_id=None):
    """获取源信息"""
    sources_file = os.path.join("data", "sources.json")
    if not os.path.exists(sources_file):
        return {} if source_id else {}
    
    with open(sources_file, 'r', encoding='utf-8') as f:
        try:
            sources = json.load(f)
            if source_id:
                return sources.get(source_id, {})
            else:
                return sources
        except json.JSONDecodeError:
            return {} if source_id else {}

def merge_data(source_id, new_data, date=None):
    """合并新数据到现有数据，实现增量更新
    
    Args:
        source_id (str): 源ID
        new_data (dict): 新爬取的数据
        date (str, optional): 日期字符串，不指定则使用当前日期
    
    Returns:
        list: 合并后的数据数组
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    week_start = get_week_start_date(date)
    filepath = os.path.join("data", source_id, f"week_{week_start}.json")
    
    # 如果文件不存在，确保以数组形式存储新数据
    if not os.path.exists(filepath):
        # 确保新数据是一个对象而不是数组，如果是数组则直接使用它
        if isinstance(new_data, list):
            return new_data
        else:
            return [new_data]
    
    # 读取现有数据
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            existing_data = json.load(f)
        except json.JSONDecodeError:
            logger.error(f"解析JSON失败: {filepath}")
            # 确保新数据是一个对象而不是数组，如果是数组则直接使用它
            if isinstance(new_data, list):
                return new_data
            else:
                return [new_data]
    
    # 确保现有数据是数组
    if not isinstance(existing_data, list):
        logger.warning(f"数据格式错误: {filepath}，预期是数组")
        existing_data = []
    
    # 检查并递归展平嵌套数组，确保是扁平的一维数组
    def flatten_array(data):
        flattened = []
        for item in data:
            if isinstance(item, list):
                # 如果是嵌套数组，递归展平
                flattened.extend(flatten_array(item))
            else:
                flattened.append(item)
        return flattened
    
    flattened_data = flatten_array(existing_data)
    
    # 添加新数据，确保正确处理数组类型的新数据
    if isinstance(new_data, list):
        flattened_data.extend(new_data)
    else:
        flattened_data.append(new_data)
    
    # 写回文件
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(flattened_data, f, ensure_ascii=False, indent=4)
    
    return flattened_data

def save_weekly_data(source_id, data, date=None):
    """保存数据到周文件
    
    Args:
        source_id (str): 源ID
        data (dict): 要保存的数据
        date (str, optional): 日期字符串，不指定则使用当前日期
    
    Returns:
        str: 保存的文件路径
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # 获取该日期所在周的周一
    week_start = get_week_start_date(date)
    
    # 确保目录存在
    base_path = os.path.join("data", source_id)
    os.makedirs(base_path, exist_ok=True)
    
    # 合并数据
    merged_data = merge_data(source_id, data, date)
    
    # 保存文件
    filepath = os.path.join(base_path, f"week_{week_start}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)
    
    # 更新源索引
    update_source_index(source_id)
    
    logger.info(f"数据已保存到 {filepath}")
    return filepath

def update_source_index(source_id):
    """更新数据源索引"""
    sources_file = os.path.join("data", "sources.json")
    sources = {}
    
    # 读取现有索引
    if os.path.exists(sources_file):
        with open(sources_file, 'r', encoding='utf-8') as f:
            try:
                sources = json.load(f)
            except json.JSONDecodeError:
                sources = {}
    
    # 获取该源的所有数据文件
    source_path = os.path.join("data", source_id)
    if os.path.exists(source_path):
        data_files = [f for f in os.listdir(source_path) if f.startswith('week_') and f.endswith('.json')]
        data_files.sort(reverse=True)  # 最新的排在前面
    else:
        data_files = []
    
    # 获取源名称
    source_name = source_id
    for file in data_files:
        try:
            with open(os.path.join(source_path, file), 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'meta' in data and 'source_name' in data['meta']:
                    source_name = data['meta']['source_name']
                    break
        except:
            continue
    
    # 更新源信息
    sources[source_id] = {
        "id": source_id,
        "name": source_name,
        "files": data_files,
        "last_updated": datetime.now().isoformat(),
        "file_count": len(data_files)
    }
    
    # 保存索引
    with open(sources_file, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    
    logger.info(f"已更新源索引: {source_id}")

def archive_old_data(source_id, weeks_to_keep=12):
    """归档旧数据
    
    Args:
        source_id (str): 源ID
        weeks_to_keep (int): 保留最近几周的数据
        
    Returns:
        bool: 是否进行了归档操作
    """
    import shutil
    
    # 获取所有数据文件
    source_path = os.path.join("data", source_id)
    if not os.path.exists(source_path):
        return False
    
    # 创建归档目录
    archive_path = os.path.join(source_path, "archive")
    os.makedirs(archive_path, exist_ok=True)
    
    # 列出所有周文件并排序
    week_files = [f for f in os.listdir(source_path) if f.startswith('week_') and f.endswith('.json')]
    week_files.sort(reverse=True)  # 最新的排在前面
    
    # 保留最近N周的数据
    keep_files = week_files[:weeks_to_keep]
    archive_files = week_files[weeks_to_keep:]
    
    archived = False
    for filename in archive_files:
        src_file = os.path.join(source_path, filename)
        dst_file = os.path.join(archive_path, filename)
        shutil.move(src_file, dst_file)
        logger.info(f"已将 {filename} 归档")
        archived = True
    
    return archived