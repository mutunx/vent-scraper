import hashlib
from datetime import datetime, timedelta
import logging
import json
import re
import time
from .base_scraper import BaseScraper
from utils.http_utils import HttpUtils

# 配置日志
logger = logging.getLogger(__name__)

class RedditScraper(BaseScraper):
    """Reddit r/confessions 每周热门帖子爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.reddit.com"
        self.api_url = f"{self.base_url}/r/confessions/top/.json?t=week&limit=10"
        logger.info("RedditScraper初始化完成")
        
        # 创建HTTP客户端，使用更严格的请求头
        self.http_client = self.get_reddit_http_client()
        
    def get_source_id(self):
        return "reddit"
    
    def get_source_name(self):
        return "Reddit"
    
    def get_reddit_http_client(self):
        """获取配置了特殊请求头的Reddit HTTP客户端"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.reddit.com/r/confessions/top/?t=week',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        
        return HttpUtils.create_client(
            use_cache=True,
            cache_dir='.reddit_cache',
            cache_ttl=3600 * 4,  # 缓存4小时
            headers=headers
        )
    
    def parse_post(self, post_data):
        """解析单个帖子的JSON数据"""
        try:
            post = post_data['data']
            
            # 提取帖子ID
            post_id = post.get('id', '')
            logger.debug(f"正在解析帖子ID: {post_id}")
            
            # 提取标题和内容
            title = post.get('title', 'No Title')
            content_text = post.get('selftext', '')
            
            # 提取帖子URL
            post_url = f"{self.base_url}{post.get('permalink', '')}"
            
            # 处理创建时间（Reddit API返回的是UTC时间戳）
            created_utc = post.get('created_utc', 0)
            created_at = datetime.fromtimestamp(created_utc).isoformat()
            
            # 提取作者信息
            author = post.get('author', '匿名用户')
            
            # 提取统计信息
            score = post.get('score', 0)
            comments_count = post.get('num_comments', 0)
            
            # 提取帖子中的媒体内容
            media = []
            if 'preview' in post and 'images' in post['preview']:
                for image in post['preview']['images']:
                    if 'source' in image and 'url' in image['source']:
                        img_url = image['source']['url'].replace('&amp;', '&')
                        media.append({
                            "type": "image",
                            "url": img_url,
                            "description": title,
                            "thumbnail": img_url
                        })
            
            # 生成帖子数据
            post_hash_id = self.generate_id("reddit_post", post_id)
            
            post_data = {
                "id": post_hash_id,
                "source_id": post_id,
                "title": title,
                "content": {
                    "text": content_text,
                    "format": "plaintext",
                    "media": media
                },
                "created_at": created_at,
                "updated_at": created_at,
                "category": {
                    "id": self.generate_id("reddit_category", "confessions"),
                    "name": "confessions"
                },
                "url": post_url,
                "author": {
                    "id": self.generate_id("reddit_user", author),
                    "source_id": author,
                    "username": author,
                    "avatar": "",
                    "role": "user",
                    "signature": ""
                },
                "stats": {
                    "views": 0,  # Reddit不显示浏览量
                    "likes": score,
                    "dislikes": 0,  # Reddit不再显示踩数
                    "replies": comments_count,
                    "shares": 0
                }
            }
            
            logger.info(f"成功解析帖子: {title[:30]}..., 作者={author}, 点赞={score}, 评论={comments_count}")
            return post_data
            
        except Exception as e:
            logger.error(f"解析帖子时出错: {str(e)}", exc_info=True)
            return None
    
    def parse_comments(self, post_url, post_id):
        """获取帖子的评论"""
        logger.info(f"获取帖子评论: {post_url}")
        
        try:
            # 使用JSON格式获取评论
            comments_url = f"{post_url}.json"
            response = self.http_client.get(comments_url)
            
            if not response['success']:
                logger.error(f"获取评论数据失败: {response.get('error')}")
                return []
            
            if 'json' not in response:
                logger.error("评论响应中没有JSON数据")
                return []
            
            comments_data = response['json']
            
            # Reddit API返回的评论在第二个数组元素中
            if not isinstance(comments_data, list) or len(comments_data) < 2:
                logger.warning("评论数据格式不符合预期")
                return []
            
            comments_list = comments_data[1]['data']['children']
            
            logger.info(f"找到 {len(comments_list)} 条评论")
            
            comments = []
            for comment_data in comments_list:
                try:
                    if comment_data['kind'] != 't1':  # t1表示评论类型
                        continue
                    
                    comment = comment_data['data']
                    
                    # 提取评论ID
                    comment_id = comment.get('id', '')
                    
                    # 提取评论内容
                    content_text = comment.get('body', '')
                    
                    # 处理创建时间
                    created_utc = comment.get('created_utc', 0)
                    created_at = datetime.fromtimestamp(created_utc).isoformat()
                    
                    # 提取评论者信息
                    author = comment.get('author', '匿名用户')
                    
                    # 提取点赞数
                    score = comment.get('score', 0)
                    
                    # 生成评论数据
                    comment_hash_id = self.generate_id("reddit_comment", comment_id)
                    
                    comment_data = {
                        "id": comment_hash_id,
                        "source_id": comment_id,
                        "content": {
                            "text": content_text,
                            "format": "plaintext",
                            "media": []
                        },
                        "created_at": created_at,
                        "updated_at": created_at,
                        "author": {
                            "id": self.generate_id("reddit_user", author),
                            "source_id": author,
                            "username": author,
                            "avatar": "",
                            "role": "user"
                        },
                        "parent_id": post_id,
                        "quote_id": "",
                        "stats": {
                            "likes": score,
                            "dislikes": 0
                        },
                        "quoted_users": []
                    }
                    
                    comments.append(comment_data)
                    
                except Exception as e:
                    logger.error(f"解析评论失败: {str(e)}", exc_info=True)
                    continue
            
            return comments
        
        except Exception as e:
            logger.error(f"获取评论过程中出错: {str(e)}", exc_info=True)
            return []
    
    def transform_to_unified_format(self, posts_data):
        """将帖子转换为统一的JSON格式"""
        logger.info(f"开始转换 {len(posts_data)} 个帖子到统一格式")
        result = []
        
        for idx, post in enumerate(posts_data):
            try:
                logger.info(f"转换第 {idx+1}/{len(posts_data)} 个帖子: {post['title'][:30]}...")
                
                # 获取帖子的评论
                comments = self.parse_comments(post['url'], post['id'])
                
                # 构建标准格式的帖子数据
                post_data = {
                    "post": {
                        "id": post["id"],
                        "source_id": post["source_id"],
                        "title": post["title"],
                        "content": post["content"],
                        "created_at": post["created_at"],
                        "updated_at": post["updated_at"],
                        "category": post["category"],
                        "tags": ["confession", "reddit"],
                        "author": post["author"],
                        "stats": post["stats"]
                    },
                    "source": {
                        "forum": "reddit",
                        "url": post["url"],
                        "section": "r/confessions"
                    },
                    "replies": comments,
                    "metadata": {
                        "crawled_at": datetime.now().isoformat(),
                        "language": "en-US",
                        "keywords": ["confession", "reddit", "personal"],
                        "is_nsfw": False  # 可以基于内容进行更精确的判断
                    }
                }
                
                result.append(post_data)
                logger.info(f"帖子 {post['title'][:30]}... 转换完成，包含 {len(comments)} 条评论")
                
            except Exception as e:
                logger.error(f"转换帖子格式失败: {str(e)}", exc_info=True)
                continue
        
        logger.info(f"共转换 {len(result)} 个帖子为统一格式")
        return result
    
    def scrape(self):
        """执行爬取操作"""
        logger.info("开始爬取Reddit r/confessions每周热门帖子")
        
        # 获取API响应
        response = self.http_client.get(self.api_url)
        if not response['success']:
            logger.error(f"获取API数据失败: {response.get('error')}")
            return None
        
        # 解析JSON响应
        if 'json' not in response:
            logger.error("API响应中没有JSON数据")
            return None
        
        data = response['json']
        
        # 解析帖子列表
        if 'data' not in data or 'children' not in data['data']:
            logger.error("API响应格式不符合预期")
            return None
        
        posts_list = data['data']['children']
        logger.info(f"找到 {len(posts_list)} 个帖子")
        
        posts = []
        for post_data in posts_list:
            if post_data['kind'] == 't3':  # t3表示帖子类型
                post = self.parse_post(post_data)
                if post:
                    posts.append(post)
        
        logger.info(f"成功解析 {len(posts)} 个帖子")
        
        # 转换为统一格式
        unified_data = self.transform_to_unified_format(posts)
        
        logger.info(f"爬取完成，共获取 {len(unified_data)} 个帖子")
        return unified_data
