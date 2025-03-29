import re
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import json
from .base_scraper import BaseScraper
from utils.http_utils import HttpUtils

# 增加更详细的日志配置
logger = logging.getLogger(__name__)

class JandanScraper(BaseScraper):
    """煎蛋网评论热榜爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://jandan.net"
        self.top_comments_url = f"{self.base_url}/top-comments"
        self.api_tucao_url = f"{self.base_url}/api/tucao/list/"
        self.comment_index = {}  # 存储评论ID映射
        logger.info("JandanScraper初始化完成")
        
        # 创建HTTP客户端，带缓存功能
        self.http_client = HttpUtils.create_client(
            use_cache=True,
            cache_dir='.jandan_cache',
            cache_ttl=3600 * 24  # 缓存24小时
        )
        
    def get_source_id(self):
        return "jandan"
    
    def get_source_name(self):
        return "煎蛋网"
    
    def fetch_tucao(self, comment_id):
        """获取指定评论的吐槽内容"""
        url = f"{self.api_tucao_url}{comment_id}"
        logger.info(f"获取评论 {comment_id} 的吐槽内容: {url}")
        
        try:
            response = self.http_client.get(url)
            logger.debug(f"API返回响应类型: {type(response)}")
            
            if not response['success']:
                logger.error(f"获取吐槽失败: {comment_id}, 错误: {response.get('error')}")
                return {"tucao": [], "hot_tucao": []}
            
            # 记录响应中的键，以便调试
            logger.debug(f"响应包含的键: {list(response.keys())}")
            
            # 确保响应包含json数据
            if 'json' in response:
                result = response['json']
                logger.debug(f"JSON响应类型: {type(result)}")
                logger.debug(f"JSON响应键: {list(result.keys()) if isinstance(result, dict) else '非字典类型'}")
                
                # 记录获取到的吐槽数量
                hot_tucao = result.get('hot_tucao', [])
                tucao = result.get('tucao', [])
                
                logger.debug(f"hot_tucao类型: {type(hot_tucao)}, 长度: {len(hot_tucao) if hasattr(hot_tucao, '__len__') else '无法确定长度'}")
                logger.debug(f"tucao类型: {type(tucao)}, 长度: {len(tucao) if hasattr(tucao, '__len__') else '无法确定长度'}")
                
                if hot_tucao and len(hot_tucao) > 0:
                    logger.debug(f"第一条hot_tucao数据类型: {type(hot_tucao[0])}")
                    logger.debug(f"第一条hot_tucao数据内容: {json.dumps(hot_tucao[0], ensure_ascii=False)[:200] if isinstance(hot_tucao[0], dict) else str(hot_tucao[0])[:200]}")
                
                if tucao and len(tucao) > 0:
                    logger.debug(f"第一条tucao数据类型: {type(tucao[0])}")
                    logger.debug(f"第一条tucao数据内容: {json.dumps(tucao[0], ensure_ascii=False)[:200] if isinstance(tucao[0], dict) else str(tucao[0])[:200]}")
                
                hot_count = len(hot_tucao)
                normal_count = len(tucao)
                logger.info(f"评论 {comment_id} 获取到 {hot_count} 条热门吐槽, {normal_count} 条普通吐槽")
                
                return result
            else:
                # 尝试手动解析JSON
                try:
                    text_response = response.get('text', '{}')
                    logger.debug(f"手动解析JSON前的文本片段: {text_response[:200]}...")
                    result = json.loads(text_response)
                    logger.info(f"手动解析JSON成功: {comment_id}")
                    logger.debug(f"解析后的JSON类型: {type(result)}")
                    logger.debug(f"解析后的JSON键: {list(result.keys()) if isinstance(result, dict) else '非字典类型'}")
                    return result
                except json.JSONDecodeError as e:
                    logger.warning(f"吐槽响应不是有效的JSON格式: {comment_id}, 错误: {str(e)}")
                    return {"tucao": [], "hot_tucao": []}
        except Exception as e:
            logger.error(f"获取吐槽过程中出错: {str(e)}", exc_info=True)
            return {"tucao": [], "hot_tucao": []}
    
    def extract_quotes(self, content_html):
        """从HTML内容中提取引用信息"""
        logger.debug(f"开始提取引用, HTML内容长度: {len(content_html)}")
        quotes = []
        soup = BeautifulSoup(content_html, 'html.parser')
        
        # 查找所有引用链接
        for quote_link in soup.select('a.tucao-link'):
            try:
                quote_id = quote_link.get('data-id')
                quoted_user = quote_link.text.strip().replace('@', '')
                logger.debug(f"找到引用链接: ID={quote_id}, 用户={quoted_user}")
                quotes.append({
                    'quote_id': quote_id,
                    'quoted_user': quoted_user
                })
                logger.debug(f"提取到引用: 用户={quoted_user}, ID={quote_id}")
            except Exception as e:
                logger.warning(f"提取引用信息失败: {str(e)}", exc_info=True)
        
        # 获取去除HTML标签后的纯文本
        for a_tag in soup.find_all('a'):
            a_tag.replace_with(a_tag.text)
        plain_text = soup.get_text(strip=True)
        logger.debug(f"提取的纯文本长度: {len(plain_text)}")
        
        return plain_text, quotes
    
    def parse_comments(self, html_content):
        """解析页面中的评论内容"""
        if not html_content:
            logger.error("解析评论失败: HTML内容为空")
            return []
        
        logger.info(f"开始解析HTML内容, 长度: {len(html_content)}")
        soup = BeautifulSoup(html_content, 'html.parser')
        comments_list = soup.select('ol.commentlist > li')
        
        logger.info(f"找到 {len(comments_list)} 条热门评论")
        
        comments = []
        for idx, comment in enumerate(comments_list):
            try:
                # 提取评论ID
                comment_id = comment.get('id', '').replace('comment-', '')
                logger.info(f"开始处理第 {idx+1}/{len(comments_list)} 条评论, ID={comment_id}")
                
                # 提取作者信息
                author_elem = comment.select_one('.author strong')
                author = author_elem.text.strip() if author_elem else "匿名用户"
                
                # 提取时间
                time_elem = comment.select_one('.author small')
                time_text = time_elem.text.strip() if time_elem else ""
                logger.debug(f"评论 {comment_id} 原始时间文本: '{time_text}'")
                
                # 提取评论内容 - 保留原始HTML以便后续分析引用关系
                text_elem = comment.select_one('.text p')
                text_html = str(text_elem) if text_elem else ""
                logger.debug(f"评论 {comment_id} HTML内容长度: {len(text_html)}")
                
                # 提取评论类型(树洞/随手拍等)
                category_elem = comment.select_one('.text small b')
                category = category_elem.text.strip() if category_elem else ""
                logger.debug(f"评论 {comment_id} 类别: {category}")
                
                # 提取点赞/踩数
                oo_elem = comment.select_one('.jandan-vote .comment-like + span')
                oo_count = 0
                if oo_elem:
                    try:
                        oo_text = oo_elem.text.strip('[]')
                        logger.debug(f"评论 {comment_id} 点赞文本: '{oo_text}'")
                        oo_count = int(oo_text)
                    except ValueError as e:
                        logger.warning(f"解析点赞数失败: {str(e)}")
                
                xx_elem = comment.select_one('.jandan-vote .comment-unlike + span')
                xx_count = 0
                if xx_elem:
                    try:
                        xx_text = xx_elem.text.strip('[]')
                        logger.debug(f"评论 {comment_id} 踩数文本: '{xx_text}'")
                        xx_count = int(xx_text)
                    except ValueError as e:
                        logger.warning(f"解析踩数失败: {str(e)}")
                
                # 提取吐槽数 - 修复吐槽数量识别
                tucao_btn = comment.select_one('.tucao-btn')
                tucao_count = 0
                
                if tucao_btn:
                    tucao_text = tucao_btn.text.strip()
                    logger.debug(f"评论 {comment_id} 的吐槽按钮文本: '{tucao_text}'")
                    tucao_match = re.search(r'$$(\d+)$$', tucao_text)
                    if tucao_match:
                        tucao_count = int(tucao_match.group(1))
                        logger.debug(f"评论 {comment_id} 解析得到吐槽数: {tucao_count}")
                    else:
                        # 尝试更宽松的匹配
                        tucao_match = re.search(r'(\d+)', tucao_text)
                        if tucao_match:
                            tucao_count = int(tucao_match.group(1))
                            logger.debug(f"评论 {comment_id} 使用宽松匹配得到吐槽数: {tucao_count}")
                        else:
                            logger.warning(f"无法从文本 '{tucao_text}' 中提取吐槽数量")
                
                # 处理文本内容，提取引用关系
                logger.debug(f"开始从评论 {comment_id} 提取引用关系")
                plain_text, quotes = self.extract_quotes(text_html)
                logger.debug(f"评论 {comment_id} 提取到 {len(quotes)} 个引用")
                
                # 正确解析日期时间，使用timedelta处理相对时间
                created_at = datetime.now().isoformat()
                try:
                    if "小时" in time_text:
                        hours = int(time_text.split('小时')[0].strip())
                        created_at = (datetime.now() - timedelta(hours=hours)).isoformat()
                    elif "分钟" in time_text:
                        minutes = int(time_text.split('分钟')[0].strip())
                        created_at = (datetime.now() - timedelta(minutes=minutes)).isoformat()
                    elif "天" in time_text:
                        days = int(time_text.split('天')[0].strip())
                        created_at = (datetime.now() - timedelta(days=days)).isoformat()
                    logger.debug(f"评论 {comment_id} 解析时间: {created_at}")
                except Exception as e:
                    logger.warning(f"处理时间失败: {time_text}, 错误: {str(e)}")
                
                # 获取吐槽内容 
                tucao_data = []
                if tucao_count > 0:
                    logger.info(f"评论 {comment_id} 有 {tucao_count} 条吐槽，开始获取")
                    tucao_response = self.fetch_tucao(comment_id)
                    
                    # 记录响应类型及内容
                    logger.debug(f"吐槽API响应类型: {type(tucao_response)}")
                    if isinstance(tucao_response, dict):
                        logger.debug(f"吐槽API响应键: {list(tucao_response.keys())}")
                    
                    # 检查热门吐槽和普通吐槽的类型和内容
                    hot_tucao = tucao_response.get('hot_tucao', [])
                    normal_tucao = tucao_response.get('tucao', [])
                    
                    logger.debug(f"hot_tucao类型: {type(hot_tucao)}")
                    logger.debug(f"tucao类型: {type(normal_tucao)}")
                    
                    if not hot_tucao and not normal_tucao:
                        logger.warning(f"评论 {comment_id} 的吐槽API返回为空")
                    
                    # 合并热门吐槽和普通吐槽，去重
                    seen_ids = set()
                    all_tucao = []
                    
                    # 先处理热门吐槽
                    if hot_tucao:
                        logger.debug(f"处理 {len(hot_tucao)} 条热门吐槽")
                        if isinstance(hot_tucao, list):
                            all_tucao.extend(hot_tucao)
                        else:
                            logger.error(f"热门吐槽不是列表类型，而是 {type(hot_tucao)}")
                            # 尝试转换或处理非列表类型的情况
                            if isinstance(hot_tucao, dict):
                                logger.debug(f"热门吐槽是字典类型，包含键: {list(hot_tucao.keys())}")
                                # 可能需要从字典中提取列表
                                for key, value in hot_tucao.items():
                                    if isinstance(value, list):
                                        logger.debug(f"从键 {key} 中找到列表类型值")
                                        all_tucao.extend(value)
                                        break
                    
                    # 然后处理普通吐槽
                    if normal_tucao:
                        logger.debug(f"处理 {len(normal_tucao)} 条普通吐槽")
                        if isinstance(normal_tucao, list):
                            all_tucao.extend(normal_tucao)
                        else:
                            logger.error(f"普通吐槽不是列表类型，而是 {type(normal_tucao)}")
                            # 类似上面的处理逻辑
                            if isinstance(normal_tucao, dict):
                                logger.debug(f"普通吐槽是字典类型，包含键: {list(normal_tucao.keys())}")
                                for key, value in normal_tucao.items():
                                    if isinstance(value, list):
                                        logger.debug(f"从键 {key} 中找到列表类型值")
                                        all_tucao.extend(value)
                                        break
                    
                    # 处理合并后的吐槽数据
                    for tucao_item in all_tucao:
                        try:
                            logger.debug(f"处理吐槽项类型: {type(tucao_item)}")
                            
                            # 安全地获取吐槽ID
                            tucao_id = None
                            if isinstance(tucao_item, dict):
                                tucao_id = tucao_item.get('comment_ID')
                                logger.debug(f"从字典中获取吐槽ID: {tucao_id}")
                            elif isinstance(tucao_item, list) and len(tucao_item) > 0:
                                logger.debug(f"吐槽项是列表类型，长度: {len(tucao_item)}")
                                # 可能是一个数组，尝试从第一个元素获取ID
                                if isinstance(tucao_item[0], dict):
                                    tucao_id = tucao_item[0].get('comment_ID')
                                    logger.debug(f"从列表的第一个字典中获取吐槽ID: {tucao_id}")
                            else:
                                logger.warning(f"无法从吐槽项中获取ID，类型: {type(tucao_item)}")
                            
                            if tucao_id and tucao_id not in seen_ids:
                                seen_ids.add(tucao_id)
                                tucao_data.append(tucao_item)
                                logger.debug(f"添加吐槽ID: {tucao_id} 到结果列表")
                        except Exception as e:
                            logger.error(f"处理吐槽项时出错: {str(e)}", exc_info=True)
                    
                    logger.info(f"评论 {comment_id} 成功获取 {len(tucao_data)} 条吐槽")
                
                comment_hash_id = self.generate_id("jandan_comment", comment_id)
                
                # 添加到评论索引，便于后续处理引用关系
                self.comment_index[comment_id] = comment_hash_id
                
                # 提取评论中的媒体内容
                media = []
                soup_text = BeautifulSoup(text_html, 'html.parser')
                for img in soup_text.find_all('img'):
                    img_url = img.get('src', '')
                    img_alt = img.get('alt', '')
                    thumbnail = img.get('org_src', '') or img_url
                    
                    if img_url:
                        media.append({
                            "type": "image",
                            "url": img_url,
                            "description": img_alt,
                            "thumbnail": thumbnail
                        })
                        logger.debug(f"评论 {comment_id} 包含图片: {img_url}")
                
                logger.info(f"评论 {comment_id} 解析完成: 作者={author}, 类别={category}, 点赞={oo_count}, 踩={xx_count}, 吐槽数={tucao_count}")
                
                # 转换评论格式
                comment_data = {
                    "id": comment_hash_id,
                    "source_id": comment_id,
                    "author": {
                        "id": self.generate_id("jandan_user", author),
                        "source_id": "",
                        "username": author,
                        "avatar": "",
                        "role": "user",
                        "signature": ""
                    },
                    "content": {
                        "text": plain_text,
                        "format": "plaintext",
                        "html": text_html,
                        "media": media
                    },
                    "created_at": created_at,
                    "updated_at": created_at,
                    "category": category.replace("@", "").strip(),
                    "stats": {
                        "likes": oo_count,
                        "dislikes": xx_count,
                        "replies": tucao_count
                    },
                    "quotes": quotes,
                    "tucao": tucao_data,
                    "url": f"https://jandan.net/t/{comment_id}"
                }
                
                comments.append(comment_data)
            
            except Exception as e:
                logger.error(f"解析评论失败: {str(e)}", exc_info=True)
                continue
        
        return comments
    
    def transform_to_unified_format(self, comments):
        """将评论转换为统一的JSON格式"""
        logger.info(f"开始转换 {len(comments)} 条评论到统一格式")
        result = []
        
        for idx, comment in enumerate(comments):
            try:
                logger.info(f"转换第 {idx+1}/{len(comments)} 条评论: ID={comment['source_id']}")
                
                # 记录评论的结构
                logger.debug(f"评论数据类型: {type(comment)}")
                logger.debug(f"评论键: {list(comment.keys())}")
                logger.debug(f"quotes类型: {type(comment.get('quotes', []))}")
                
                # 处理引用关系
                quotes = comment.get('quotes', [])
                quote_id = ""
                
                # 如果有引用，使用第一个引用的ID
                if quotes:
                    logger.debug(f"评论 {comment['source_id']} 有 {len(quotes)} 个引用")
                    logger.debug(f"第一个引用类型: {type(quotes[0])}")
                    
                    # 安全地处理quotes[0]，确保它是字典类型
                    if isinstance(quotes[0], dict):
                        source_quote_id = quotes[0].get('quote_id')
                        logger.debug(f"从字典中获取引用ID: {source_quote_id}")
                        
                        if source_quote_id in self.comment_index:
                            quote_id = self.comment_index[source_quote_id]
                            logger.debug(f"评论 {comment['source_id']} 引用了 {source_quote_id} (内部ID: {quote_id})")
                    else:
                        logger.warning(f"quotes[0]不是字典类型，而是 {type(quotes[0])}")
                        # 如果是列表，尝试继续处理
                        if isinstance(quotes[0], list) and len(quotes[0]) > 0:
                            if isinstance(quotes[0][0], dict):
                                source_quote_id = quotes[0][0].get('quote_id')
                                logger.debug(f"从嵌套列表中获取引用ID: {source_quote_id}")
                                if source_quote_id in self.comment_index:
                                    quote_id = self.comment_index[source_quote_id]
                                    logger.debug(f"评论 {comment['source_id']} 引用了 {source_quote_id} (内部ID: {quote_id})")
                            else:
                                logger.warning(f"quotes[0][0]类型: {type(quotes[0][0]) if quotes[0] and len(quotes[0]) > 0 else 'N/A'}")
                        elif isinstance(quotes[0], str):
                            # 如果直接是字符串，可能是引用ID本身
                            source_quote_id = quotes[0]
                            logger.debug(f"quotes[0]是字符串类型: {source_quote_id}")
                            if source_quote_id in self.comment_index:
                                quote_id = self.comment_index[source_quote_id]
                                logger.debug(f"评论 {comment['source_id']} 引用了 {source_quote_id} (内部ID: {quote_id})")
                
                # 构建标准格式的帖子数据
                post_data = {
                    "post": {
                        "id": comment["id"],
                        "source_id": comment["source_id"],
                        "title": f"{comment['category']}热评",
                        "content": {
                            "text": comment["content"]["text"],
                            "format": "plaintext",
                            "media": comment["content"].get("media", [])
                        },
                        "created_at": comment["created_at"],
                        "updated_at": comment["updated_at"],
                        "category": {
                            "id": self.generate_id("jandan_category", comment['category']),
                            "name": comment['category']
                        },
                        "tags": [comment['category']],
                        "author": comment["author"],
                        "stats": {
                            "views": 0,
                            "likes": comment["stats"]["likes"],
                            "dislikes": comment["stats"]["dislikes"],
                            "replies": comment["stats"]["replies"],
                            "shares": 0
                        }
                    },
                    "source": {
                        "forum": "jandan",
                        "url": comment["url"],
                        "section": comment['category']
                    },
                    "replies": [],
                    "metadata": {
                        "crawled_at": datetime.now().isoformat(),
                        "language": "zh-CN",
                        "keywords": [comment['category'], "热评", "煎蛋"],
                        "is_nsfw": False
                    }
                }
                
                # 处理吐槽评论作为回复
                tucao_count = 0
                tucao_list = comment.get("tucao", [])
                logger.debug(f"评论 {comment['source_id']} 的tucao类型: {type(tucao_list)}, 长度: {len(tucao_list) if hasattr(tucao_list, '__len__') else '无法确定长度'}")
                
                for tucao_idx, tucao in enumerate(tucao_list):
                    try:
                        logger.debug(f"处理评论 {comment['source_id']} 的第 {tucao_idx+1} 条吐槽, 类型: {type(tucao)}")
                        
                        if isinstance(tucao, dict):
                            logger.debug(f"吐槽键: {list(tucao.keys())}")
                            tucao_id = str(tucao.get("comment_ID", ""))
                            tucao_author = tucao.get("comment_author", "匿名用户")
                            tucao_content = tucao.get("comment_content", "")
                            
                            logger.debug(f"处理评论 {comment['source_id']} 的吐槽 {tucao_id} 作者={tucao_author}")
                            
                            # 处理吐槽中的引用关系
                            tucao_plain_text, tucao_quotes = self.extract_quotes(tucao_content)
                            tucao_quote_id = ""
                            
                            # 如果吐槽中有引用，处理引用关系
                            if tucao_quotes:
                                logger.debug(f"吐槽 {tucao_id} 有 {len(tucao_quotes)} 个引用")
                                # 检查第一个引用是否为字典类型
                                if isinstance(tucao_quotes[0], dict):
                                    source_tucao_quote_id = tucao_quotes[0].get('quote_id')
                                    if source_tucao_quote_id in self.comment_index:
                                        tucao_quote_id = self.comment_index[source_tucao_quote_id]
                                        logger.debug(f"吐槽 {tucao_id} 引用了 {source_tucao_quote_id}")
                                else:
                                    logger.warning(f"tucao_quotes[0]不是字典类型，而是 {type(tucao_quotes[0])}")
                            
                            # 尝试从时间戳转换日期时间
                            tucao_created_at = datetime.now().isoformat()
                            try:
                                if tucao.get("comment_date_int"):
                                    tucao_created_at = datetime.fromtimestamp(tucao.get("comment_date_int")).isoformat()
                                    logger.debug(f"吐槽 {tucao_id} 从时间戳转换日期: {tucao_created_at}")
                                elif tucao.get("comment_date"):
                                    tucao_created_at = datetime.strptime(
                                        tucao.get("comment_date"), "%Y-%m-%d %H:%M:%S"
                                    ).isoformat()
                                    logger.debug(f"吐槽 {tucao_id} 从字符串转换日期: {tucao_created_at}")
                            except Exception as e:
                                logger.warning(f"转换吐槽时间失败: {str(e)}")
                            
                            # 生成吐槽评论的唯一ID
                            tucao_hash_id = self.generate_id("jandan_tucao", tucao_id)
                            
                            # 添加到评论索引
                            self.comment_index[tucao_id] = tucao_hash_id
                            
                            reply = {
                                "id": tucao_hash_id,
                                "source_id": tucao_id,
                                "content": {
                                    "text": tucao_plain_text,
                                    "format": "plaintext",
                                    "media": []
                                },
                                "created_at": tucao_created_at,
                                "updated_at": tucao_created_at,
                                "author": {
                                    "id": self.generate_id("jandan_user", tucao_author),
                                    "source_id": "",
                                    "username": tucao_author,
                                    "avatar": "",
                                    "role": "user"
                                },
                                "parent_id": comment["id"],
                                "quote_id": tucao_quote_id,
                                "stats": {
                                    "likes": tucao.get("vote_positive", 0),
                                    "dislikes": tucao.get("vote_negative", 0)
                                },
                                "quoted_users": [q["quoted_user"] for q in tucao_quotes if isinstance(q, dict) and "quoted_user" in q]
                            }
                            post_data["replies"].append(reply)
                            tucao_count += 1
                        else:
                            logger.error(f"吐槽项不是字典类型，而是 {type(tucao)}")
                            # 如果是字符串，可能是直接的评论内容
                            if isinstance(tucao, str):
                                logger.debug(f"吐槽是字符串类型: {tucao[:50]}...")
                            # 如果是列表，可能需要进一步处理
                            elif isinstance(tucao, list):
                                logger.debug(f"吐槽是列表类型，长度: {len(tucao)}")
                                if tucao and isinstance(tucao[0], dict):
                                    logger.debug(f"吐槽[0]是字典类型，键: {list(tucao[0].keys())}")
                        
                    except Exception as e:
                        logger.error(f"转换吐槽失败: {str(e)}", exc_info=True)
                        continue
                
                logger.info(f"评论 {comment['source_id']} 成功转换，包含 {tucao_count} 条吐槽回复")
                result.append(post_data)
                
            except Exception as e:
                logger.error(f"转换评论格式失败: {str(e)}", exc_info=True)
                continue
        
        logger.info(f"共转换 {len(result)} 条评论为统一格式")
        return result
    
    def scrape(self):
        """执行爬取操作"""
        logger.info("开始爬取煎蛋热评")
        
        # 获取热评页面
        response = self.http_client.get(self.top_comments_url)
        if not response['success']:
            logger.error(f"获取页面失败: {response.get('error')}")
            return None
        
        html_content = response['text']
        logger.info(f"成功获取HTML内容，长度: {len(html_content)}")
        
        # 手动检查一个评论的吐槽数据，用于调试
        debug_comment_id = '5877984'
        logger.info(f"调试: 手动获取评论 {debug_comment_id} 的吐槽数据")
        debug_tucao = self.fetch_tucao(debug_comment_id)
        if isinstance(debug_tucao, dict):
            hot_tucao = debug_tucao.get('hot_tucao', [])
            normal_tucao = debug_tucao.get('tucao', [])
            
            hot_count = len(hot_tucao) if isinstance(hot_tucao, list) else "无法确定长度"
            normal_count = len(normal_tucao) if isinstance(normal_tucao, list) else "无法确定长度"
            
            logger.info(f"调试: 评论 {debug_comment_id} 获取到 {hot_count} 条热门吐槽, {normal_count} 条普通吐槽")
            logger.debug(f"hot_tucao类型: {type(hot_tucao)}")
            logger.debug(f"tucao类型: {type(normal_tucao)}")
            
            # 检查返回的数据结构
            if hot_tucao and isinstance(hot_tucao, list) and len(hot_tucao) > 0:
                logger.debug(f"第一条hot_tucao类型: {type(hot_tucao[0])}")
                if isinstance(hot_tucao[0], dict):
                    logger.debug(f"hot_tucao[0]键: {list(hot_tucao[0].keys())}")
            
            if normal_tucao and isinstance(normal_tucao, list) and len(normal_tucao) > 0:
                logger.debug(f"第一条tucao类型: {type(normal_tucao[0])}")
                if isinstance(normal_tucao[0], dict):
                    logger.debug(f"tucao[0]键: {list(normal_tucao[0].keys())}")
        else:
            logger.error(f"调试: 获取到的吐槽数据不是字典类型，而是 {type(debug_tucao)}")
        
        # 解析评论
        logger.info("开始解析页面中的评论")
        comments = self.parse_comments(html_content)
        logger.info(f"解析完成，获取到 {len(comments)} 条评论")
        
        # 转换为统一格式
        logger.info("开始转换评论为统一格式")
        unified_data = self.transform_to_unified_format(comments)
        
        logger.info(f"爬取完成，共获取 {len(unified_data)} 条热评")
        return unified_data