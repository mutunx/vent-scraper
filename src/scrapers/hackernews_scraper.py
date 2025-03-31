import hashlib
from datetime import datetime, timedelta
import logging
import json
import re
import time
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from utils.http_utils import HttpUtils

# 配置日志
logger = logging.getLogger(__name__)

class HackerNewsScraper(BaseScraper):
    """Hacker News Ask HN 帖子爬虫"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://news.ycombinator.com"
        self.api_base_url = "https://hacker-news.firebaseio.com/v0"
        self.ask_hn_stories = []
        logger.info("HackerNewsScraper初始化完成")
        
        # 创建HTTP客户端，带缓存功能
        self.http_client = HttpUtils.create_client(
            use_cache=True,
            cache_dir='.hackernews_cache',
            cache_ttl=3600 * 2,  # 缓存2小时
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
            }
        )
        
    def get_source_id(self):
        return "hackernews"
    
    def get_source_name(self):
        return "Hacker News"
    
    def fetch_story_details(self, story_id):
        """获取单个故事的详细信息"""
        url = f"{self.base_url}/item?id={story_id}"
        logger.debug(f"获取故事详情: {url}")
        
        response = self.http_client.get(url)
        if not response['success']:
            logger.error(f"获取故事详情失败: {story_id}")
            return None
        
        return response['text']

    def fetch_ask_hn_page(self):
        """获取Ask HN页面HTML内容"""
        url = f"{self.base_url}/ask"
        logger.info(f"获取Ask HN页面: {url}")
        
        response = self.http_client.get(url)
        if not response['success']:
            logger.error("获取Ask HN页面失败")
            return None
        
        return response['text']
    
    def parse_ask_hn_stories_from_html(self, html_content, limit=15):
        """从HTML内容解析Ask HN故事列表"""
        if not html_content:
            logger.error("HTML内容为空")
            return []
        
        stories = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        story_rows = soup.select('tr.athing.submission')
        logger.info(f"找到 {len(story_rows)} 个帖子行")
        
        count = 0
        for story_row in story_rows:
            if count >= limit:
                break
                
            try:
                # 获取帖子ID
                story_id = story_row.get('id')
                if not story_id:
                    continue
                
                # 获取标题链接
                title_elem = story_row.select_one('td.title span.titleline a')
                if not title_elem:
                    continue
                    
                title = title_elem.text.strip()
                
                # 只处理Ask HN帖子
                if not title.startswith("Ask HN:"):
                    continue
                
                # 获取链接URL
                item_url = title_elem.get('href')
                if item_url.startswith('item?id='):
                    item_url = f"{self.base_url}/{item_url}"
                    
                # 获取子文本行（包含作者、点赞数等信息）
                subtext_row = story_row.find_next_sibling('tr')
                if not subtext_row:
                    continue
                    
                subtext = subtext_row.select_one('td.subtext span.subline')
                if not subtext:
                    continue
                
                # 获取点赞数
                score_elem = subtext.select_one('span.score')
                score = 0
                if score_elem:
                    score_text = score_elem.text.strip()
                    score_match = re.search(r'(\d+)', score_text)
                    if score_match:
                        score = int(score_match.group(1))
                
                # 获取作者
                author_elem = subtext.select_one('a.hnuser')
                author = '匿名用户'
                if author_elem:
                    author = author_elem.text.strip()
                
                # 获取时间
                age_elem = subtext.select_one('span.age')
                created_at = datetime.now().isoformat()
                if age_elem:
                    time_attr = age_elem.get('title')
                    if time_attr:
                        try:
                            created_at = datetime.fromtimestamp(int(time_attr)).isoformat()
                        except:
                            pass
                
                # 获取评论数
                comments_elem = subtext.select_one('a:last-child')
                comments_count = 0
                if comments_elem and 'comments' in comments_elem.text:
                    comments_text = comments_elem.text.strip()
                    comments_match = re.search(r'(\d+)', comments_text)
                    if comments_match:
                        comments_count = int(comments_match.group(1))
                
                # 生成故事数据
                story_hash_id = self.generate_id("hackernews_story", story_id)
                
                story_data = {
                    "id": story_hash_id,
                    "source_id": story_id,
                    "title": title,
                    "content": {
                        "text": "",  # 内容需要访问详情页获取
                        "format": "html",
                        "media": []
                    },
                    "created_at": created_at,
                    "updated_at": created_at,
                    "category": {
                        "id": self.generate_id("hackernews_category", "ask"),
                        "name": "Ask HN"
                    },
                    "url": item_url,
                    "author": {
                        "id": self.generate_id("hackernews_user", author),
                        "source_id": author,
                        "username": author,
                        "avatar": "",
                        "role": "user",
                        "signature": ""
                    },
                    "stats": {
                        "views": 0,
                        "likes": score,
                        "dislikes": 0,
                        "replies": comments_count,
                        "shares": 0
                    }
                }
                
                stories.append(story_data)
                count += 1
                logger.info(f"成功解析故事: {title[:30]}..., 作者={author}, 点赞={score}, 评论={comments_count}")
                
            except Exception as e:
                logger.error(f"解析故事行失败: {str(e)}", exc_info=True)
                continue
        
        logger.info(f"成功解析 {len(stories)} 个Ask HN故事")
        return stories
    
    def fetch_story_content(self, story):
        """获取故事详情内容"""
        story_id = story['source_id']
        html_content = self.fetch_story_details(story_id)
        
        if not html_content:
            return story
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 在详情页面查找帖子内容
            # HN帖子内容通常在一个特定格式的div中
            # 先查找帖子标题行
            title_row = soup.select_one(f'tr.athing[id="{story_id}"]')
            if title_row:
                # 获取下一行的内容（可能包含帖子文本）
                next_row = title_row.find_next_sibling('tr')
                if next_row:
                    # 寻找帖子内容
                    content_div = next_row.find_next_sibling('tr').select_one('div.toptext') or next_row.find_next_sibling('tr').select_one('td.default')
                    if content_div:
                        story['content']['text'] = str(content_div)
        except Exception as e:
            logger.error(f"获取故事内容失败: {story_id}, {str(e)}", exc_info=True)
        
        return story
    
    def parse_comments(self, story_id):
        """解析故事的评论"""
        html_content = self.fetch_story_details(story_id)
        if not html_content:
            return []
        
        comments = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找所有评论区域
            comment_rows = soup.select('tr.athing.comtr')
            logger.info(f"找到 {len(comment_rows)} 条评论")
            
            for comment_row in comment_rows:
                try:
                    # 获取评论ID
                    comment_id = comment_row.get('id')
                    if not comment_id:
                        continue
                    
                    # 获取评论内容
                    comment_div = comment_row.select_one('div.comment')
                    if not comment_div:
                        continue
                        
                    comment_text = comment_div.decode_contents().strip()
                    
                    # 获取评论作者
                    author_elem = comment_row.select_one('a.hnuser')
                    author = '匿名用户'
                    if author_elem:
                        author = author_elem.text.strip()
                    
                    # 获取回复时间
                    age_elem = comment_row.select_one('span.age')
                    created_at = datetime.now().isoformat()
                    if age_elem:
                        time_attr = age_elem.get('title')
                        if time_attr:
                            try:
                                created_at = datetime.fromtimestamp(int(time_attr)).isoformat()
                            except:
                                pass
                    
                    # 获取点赞数（HN评论没有明确显示点赞数）
                    
                    # 生成评论数据
                    comment_hash_id = self.generate_id("hackernews_comment", comment_id)
                    
                    # 获取父评论ID
                    parent_comment = comment_row.find_previous('tr.comtr')
                    parent_id = ""
                    if parent_comment:
                        parent_comment_id = parent_comment.get('id')
                        if parent_comment_id:
                            parent_id = self.generate_id("hackernews_comment", parent_comment_id)
                    
                    comment_data = {
                        "id": comment_hash_id,
                        "source_id": comment_id,
                        "content": {
                            "text": comment_text,
                            "format": "html",
                            "media": []
                        },
                        "created_at": created_at,
                        "updated_at": created_at,
                        "author": {
                            "id": self.generate_id("hackernews_user", author),
                            "source_id": author,
                            "username": author,
                            "avatar": "",
                            "role": "user"
                        },
                        "parent_id": parent_id,
                        "quote_id": "",
                        "stats": {
                            "likes": 0,
                            "dislikes": 0
                        },
                        "quoted_users": []
                    }
                    
                    comments.append(comment_data)
                    
                except Exception as e:
                    logger.error(f"解析评论失败: {str(e)}", exc_info=True)
                    continue
            
        except Exception as e:
            logger.error(f"解析评论列表失败: {str(e)}", exc_info=True)
        
        return comments[:100]  # 限制返回100条评论
    
    def transform_to_unified_format(self, stories_data):
        """将爬取的数据转换为统一格式"""
        logger.info(f"开始转换 {len(stories_data)} 个故事到统一格式")
        result = []
        
        for idx, story in enumerate(stories_data):
            try:
                logger.info(f"转换第 {idx+1}/{len(stories_data)} 个故事: {story['title'][:30]}...")
                
                # 先获取故事详情内容
                story = self.fetch_story_content(story)
                
                # 获取故事的评论
                comments = self.parse_comments(story['source_id'])
                
                # 构建标准格式的帖子数据
                post_data = {
                    "post": {
                        "id": story["id"],
                        "source_id": story["source_id"],
                        "title": story["title"],
                        "content": story["content"],
                        "created_at": story["created_at"],
                        "updated_at": story["updated_at"],
                        "category": story["category"],
                        "tags": ["Ask HN", "hacker news", "tech"],
                        "author": story["author"],
                        "stats": story["stats"]
                    },
                    "source": {
                        "forum": "hackernews",
                        "url": story["url"],
                        "section": "Ask HN"
                    },
                    "replies": comments,
                    "metadata": {
                        "crawled_at": datetime.now().isoformat(),
                        "language": "en-US",
                        "keywords": ["tech", "startup", "programming", "ask", "question"],
                        "is_nsfw": False
                    }
                }
                
                result.append(post_data)
                logger.info(f"故事 {story['title'][:30]}... 转换完成，包含 {len(comments)} 条评论")
                
            except Exception as e:
                logger.error(f"转换故事格式失败: {str(e)}", exc_info=True)
                continue
        
        logger.info(f"共转换 {len(result)} 个故事为统一格式")
        return result
    
    def scrape(self):
        """执行爬取操作"""
        logger.info("开始爬取Hacker News Ask HN帖子")
        
        # 获取Ask HN页面HTML内容
        html_content = self.fetch_ask_hn_page()
        if not html_content:
            logger.error("未能获取Ask HN页面内容")
            return None
        
        # 从HTML解析Ask HN故事列表
        stories = self.parse_ask_hn_stories_from_html(html_content, 15)  # 限制为前15个故事
        if not stories:
            logger.error("未解析到任何Ask HN故事")
            return None
        
        # 转换为统一格式
        unified_data = self.transform_to_unified_format(stories)
        
        logger.info(f"爬取完成，共获取 {len(unified_data)} 个Ask HN故事")
        return unified_data
