import re
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from .base_scraper import BaseScraper
from utils.http_utils import HttpUtils

logger = logging.getLogger(__name__)

class JandanScraper(BaseScraper):
    """煎蛋网评论热榜爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://jandan.net"
        self.top_comments_url = f"{self.base_url}/top-comments"
        self.api_tucao_url = f"{self.base_url}/api/tucao/list/"
        self.comment_index = {}  # 存储评论ID映射
        
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
            
            if not response['success']:
                logger.error(f"获取吐槽失败: {comment_id}, 错误: {response.get('error')}")
                return {"tucao": [], "hot_tucao": []}
            
            # 确保响应包含json数据
            if 'json' in response:
                result = response['json']
                
                # 记录获取到的吐槽数量
                hot_count = len(result.get('hot_tucao', []))
                normal_count = len(result.get('tucao', []))
                logger.info(f"评论 {comment_id} 获取到 {hot_count} 条热门吐槽, {normal_count} 条普通吐槽")
                
                return result
            else:
                # 尝试手动解析JSON
                import json
                try:
                    result = json.loads(response.get('text', '{}'))
                    logger.info(f"手动解析JSON成功: {comment_id}")
                    return result
                except json.JSONDecodeError:
                    logger.warning(f"吐槽响应不是有效的JSON格式: {comment_id}")
                    return {"tucao": [], "hot_tucao": []}
        except Exception as e:
            logger.error(f"获取吐槽过程中出错: {str(e)}", exc_info=True)
            return {"tucao": [], "hot_tucao": []}
    
    def extract_quotes(self, content_html):
        """从HTML内容中提取引用信息"""
        quotes = []
        soup = BeautifulSoup(content_html, 'html.parser')
        
        # 查找所有引用链接
        for quote_link in soup.select('a.tucao-link'):
            try:
                quote_id = quote_link.get('data-id')
                quoted_user = quote_link.text.strip().replace('@', '')
                quotes.append({
                    'quote_id': quote_id,
                    'quoted_user': quoted_user
                })
                logger.debug(f"提取到引用: 用户={quoted_user}, ID={quote_id}")
            except Exception as e:
                logger.warning(f"提取引用信息失败: {str(e)}")
        
        # 获取去除HTML标签后的纯文本
        for a_tag in soup.find_all('a'):
            a_tag.replace_with(a_tag.text)
        plain_text = soup.get_text(strip=True)
        
        return plain_text, quotes
    
    def parse_comments(self, html_content):
        """解析页面中的评论内容"""
        if not html_content:
            logger.error("解析评论失败: HTML内容为空")
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        comments_list = soup.select('ol.commentlist > li')
        
        logger.info(f"找到 {len(comments_list)} 条热门评论")
        
        comments = []
        for idx, comment in enumerate(comments_list):
            try:
                # 提取评论ID
                comment_id = comment.get('id', '').replace('comment-', '')
                logger.debug(f"开始处理第 {idx+1}/{len(comments_list)} 条评论, ID={comment_id}")
                
                # 提取作者信息
                author_elem = comment.select_one('.author strong')
                author = author_elem.text.strip() if author_elem else "匿名用户"
                
                # 提取时间
                time_elem = comment.select_one('.author small')
                time_text = time_elem.text.strip() if time_elem else ""
                
                # 提取评论内容 - 保留原始HTML以便后续分析引用关系
                text_elem = comment.select_one('.text p')
                text_html = str(text_elem) if text_elem else ""
                
                # 提取评论类型(树洞/随手拍等)
                category_elem = comment.select_one('.text small b')
                category = category_elem.text.strip() if category_elem else ""
                
                # 提取点赞/踩数
                oo_elem = comment.select_one('.jandan-vote .comment-like + span')
                oo_count = int(oo_elem.text.strip('[]')) if oo_elem else 0
                
                xx_elem = comment.select_one('.jandan-vote .comment-unlike + span')
                xx_count = int(xx_elem.text.strip('[]')) if xx_elem else 0
                
                # 提取吐槽数 - 修复吐槽数量识别
                tucao_btn = comment.select_one('.tucao-btn')
                tucao_count = 0
                
                if tucao_btn:
                    tucao_text = tucao_btn.text.strip()
                    tucao_match = re.search(r'$$(\d+)$$', tucao_text)
                    if tucao_match:
                        tucao_count = int(tucao_match.group(1))
                        logger.debug(f"评论 {comment_id} 的吐槽按钮文本: '{tucao_text}', 解析得到吐槽数: {tucao_count}")
                    else:
                        # 尝试更宽松的匹配
                        tucao_match = re.search(r'(\d+)', tucao_text)
                        if tucao_match:
                            tucao_count = int(tucao_match.group(1))
                            logger.debug(f"评论 {comment_id} 使用宽松匹配得到吐槽数: {tucao_count}")
                        else:
                            logger.warning(f"无法从文本 '{tucao_text}' 中提取吐槽数量")
                
                # 处理文本内容，提取引用关系
                plain_text, quotes = self.extract_quotes(text_html)
                
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
                except Exception as e:
                    logger.warning(f"处理时间失败: {time_text}, 错误: {str(e)}")
                
                # 获取吐槽内容 
                tucao_data = []
                if tucao_count > 0:
                    logger.info(f"评论 {comment_id} 有 {tucao_count} 条吐槽，开始获取")
                    tucao_response = self.fetch_tucao(comment_id)
                    hot_tucao = tucao_response.get('hot_tucao', [])
                    normal_tucao = tucao_response.get('tucao', [])
                    
                    if not hot_tucao and not normal_tucao:
                        logger.warning(f"评论 {comment_id} 的吐槽API返回为空")
                    
                    # 合并热门吐槽和普通吐槽，去重
                    seen_ids = set()
                    for tucao in hot_tucao + normal_tucao:
                        tucao_id = tucao.get('comment_ID')
                        if tucao_id and tucao_id not in seen_ids:
                            seen_ids.add(tucao_id)
                            tucao_data.append(tucao)
                            
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
                logger.debug(f"转换第 {idx+1}/{len(comments)} 条评论: ID={comment['source_id']}")
                
                # 处理引用关系
                quotes = comment.get('quotes', [])
                quote_id = ""
                
                # 如果有引用，使用第一个引用的ID
                if quotes:
                    source_quote_id = quotes[0].get('quote_id')
                    if source_quote_id in self.comment_index:
                        quote_id = self.comment_index[source_quote_id]
                        logger.debug(f"评论 {comment['source_id']} 引用了 {source_quote_id}")
                
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
                for tucao in comment.get("tucao", []):
                    try:
                        tucao_id = str(tucao.get("comment_ID", ""))
                        tucao_author = tucao.get("comment_author", "匿名用户")
                        tucao_content = tucao.get("comment_content", "")
                        
                        logger.debug(f"处理评论 {comment['source_id']} 的吐槽 {tucao_id} 作者={tucao_author}")
                        
                        # 处理吐槽中的引用关系
                        tucao_plain_text, tucao_quotes = self.extract_quotes(tucao_content)
                        tucao_quote_id = ""
                        
                        # 如果吐槽中有引用，处理引用关系
                        if tucao_quotes:
                            source_tucao_quote_id = tucao_quotes[0].get('quote_id')
                            if source_tucao_quote_id in self.comment_index:
                                tucao_quote_id = self.comment_index[source_tucao_quote_id]
                                logger.debug(f"吐槽 {tucao_id} 引用了 {source_tucao_quote_id}")
                        
                        # 尝试从时间戳转换日期时间
                        tucao_created_at = datetime.now().isoformat()
                        try:
                            if tucao.get("comment_date_int"):
                                tucao_created_at = datetime.fromtimestamp(tucao.get("comment_date_int")).isoformat()
                            elif tucao.get("comment_date"):
                                tucao_created_at = datetime.strptime(
                                    tucao.get("comment_date"), "%Y-%m-%d %H:%M:%S"
                                ).isoformat()
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
                            "quoted_users": [q["quoted_user"] for q in tucao_quotes if "quoted_user" in q]
                        }
                        post_data["replies"].append(reply)
                        tucao_count += 1
                        
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
        
        # 手动检查一个评论的吐槽数据，用于调试
        debug_comment_id = '5877984'
        logger.info(f"调试: 手动获取评论 {debug_comment_id} 的吐槽数据")
        debug_tucao = self.fetch_tucao(debug_comment_id)
        hot_count = len(debug_tucao.get('hot_tucao', []))
        normal_count = len(debug_tucao.get('tucao', []))
        logger.info(f"调试: 评论 {debug_comment_id} 获取到 {hot_count} 条热门吐槽, {normal_count} 条普通吐槽")
        
        # 解析评论
        logger.info("开始解析页面中的评论")
        comments = self.parse_comments(html_content)
        
        # 转换为统一格式
        logger.info("开始转换评论为统一格式")
        unified_data = self.transform_to_unified_format(comments)
        
        logger.info(f"爬取完成，共获取 {len(unified_data)} 条热评")
        return unified_data