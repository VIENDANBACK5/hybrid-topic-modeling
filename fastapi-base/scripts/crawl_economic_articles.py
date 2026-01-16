#!/usr/bin/env python3
"""
Script crawl toàn bộ bài viết kinh tế từ thongkehungyen.nso.gov.vn
Lưu thành JSON vào thư mục data/crawled/

Usage:
    python scripts/crawl_economic_articles.py --max-pages 5
"""
import requests
import json
import re
import warnings
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import argparse
import time

warnings.filterwarnings('ignore')


class EconomicArticleCrawler:
    """Crawler cho website thống kê Hưng Yên"""
    
    BASE_URL = "https://thongkehungyen.nso.gov.vn"
    
    def __init__(self, output_dir: str = "data/crawled"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.session.verify = False
        
        # Add retry adapter
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.stats = {
            'total_listing_pages': 0,
            'total_articles_found': 0,
            'articles_crawled': 0,
            'articles_failed': 0,
            'start_time': None,
            'end_time': None
        }
    
    def crawl_article_list(self, max_pages: int = 5) -> List[Dict[str, str]]:
        """
        Crawl danh sách tất cả bài viết
        
        Returns:
            List of {title, url, date, summary}
        """
        print(f"\n{'='*80}")
        print(f"STEP 1: Crawling article list (max {max_pages} pages)...")
        print(f"{'='*80}\n")
        
        articles_dict = {}
        
        for page in range(1, max_pages + 1):
            url = f"{self.BASE_URL}/tinh-hinh-kinh-te-xa-hoi?page={page}"
            print(f"📄 Page {page}/{max_pages}: {url}")
            
            try:
                resp = self.session.get(url, timeout=90)  # Increased timeout
                resp.raise_for_status()
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                # Find all article links
                links = soup.find_all('a', href=True)
                article_links = [
                    l for l in links 
                    if '/tinh-hinh-kinh-te-xa-hoi/' in l.get('href', '') 
                    and l.get('href').split('/')[-1].isdigit()
                ]
                
                print(f"   Found {len(article_links)} potential items")
                
                for link in article_links:
                    href = link.get('href', '')
                    if not href.startswith('http'):
                        href = self.BASE_URL + href
                    
                    title = link.get_text(strip=True)
                    
                    # Skip pagination or invalid links
                    if title in ['<', '>', '<<', '>>', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
                        continue
                    
                    # Deduplicate: keep longest title for each URL
                    if href in articles_dict:
                        if len(title) > len(articles_dict[href]['title']):
                            articles_dict[href]['title'] = title
                    else:
                        # Try to find date
                        date_elem = None
                        parent = link.parent
                        for _ in range(3):  # Search up to 3 levels
                            if parent:
                                date_elem = parent.find(class_=re.compile(r'date|time'))
                                if date_elem:
                                    break
                                parent = parent.parent
                        
                        date_str = date_elem.get_text(strip=True) if date_elem else ""
                        
                        articles_dict[href] = {
                            'title': title,
                            'url': href,
                            'date': date_str,
                            'article_id': href.split('/')[-1]
                        }
                
                self.stats['total_listing_pages'] += 1
                time.sleep(1)  # Increased delay to be more polite
                
            except requests.exceptions.Timeout:
                print(f"   ⏱️  Timeout on page {page}, retrying...")
                try:
                    time.sleep(3)
                    resp = self.session.get(url, timeout=120)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    # Process the page...
                    links = soup.find_all('a', href=True)
                    article_links = [
                        l for l in links 
                        if '/tinh-hinh-kinh-te-xa-hoi/' in l.get('href', '') 
                        and l.get('href').split('/')[-1].isdigit()
                    ]
                    
                    for link in article_links:
                        href = link.get('href', '')
                        if not href.startswith('http'):
                            href = self.BASE_URL + href
                        
                        title = link.get_text(strip=True)
                        if title in ['<', '>', '<<', '>>', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
                            continue
                        
                        if href in articles_dict:
                            if len(title) > len(articles_dict[href]['title']):
                                articles_dict[href]['title'] = title
                        else:
                            date_elem = None
                            parent = link.parent
                            for _ in range(3):
                                if parent:
                                    date_elem = parent.find(class_=re.compile(r'date|time'))
                                    if date_elem:
                                        break
                                    parent = parent.parent
                            
                            date_str = date_elem.get_text(strip=True) if date_elem else ""
                            
                            articles_dict[href] = {
                                'title': title,
                                'url': href,
                                'date': date_str,
                                'article_id': href.split('/')[-1]
                            }
                    
                    self.stats['total_listing_pages'] += 1
                    print(f"   ✅ Retry succeeded, found {len(article_links)} items")
                except Exception as e2:
                    print(f"   ❌ Retry failed: {e2}")
                    continue
                
            except Exception as e:
                print(f"   ❌ Error crawling page {page}: {e}")
                continue
        
        # Filter out articles with too short titles
        articles = [
            art for art in articles_dict.values()
            if art['title'] and len(art['title']) >= 10
        ]
        
        self.stats['total_articles_found'] = len(articles)
        
        print(f"\n✅ Found {len(articles)} unique articles (after dedup and filter)")
        return articles
    
    def crawl_article_content(self, article: Dict[str, str]) -> Optional[Dict[str, str]]:
        """
        Crawl nội dung chi tiết của 1 bài viết
        
        Returns:
            Dict with full article data or None if failed
        """
        url = article['url']
        
        try:
            resp = self.session.get(url, timeout=90)  # Increased timeout
            resp.raise_for_status()
            
            # Use helper method to extract content
            return self._extract_article_from_response(resp, article)
            
        except requests.exceptions.Timeout:
            print(f"   ⏱️  Timeout, retrying...")
            try:
                time.sleep(3)
                resp = self.session.get(url, timeout=120)
                resp.raise_for_status()
                # Repeat extraction...
                return self._extract_article_from_response(resp, article)
            except Exception as e2:
                print(f"   ❌ Retry failed: {str(e2)[:50]}")
                self.stats['articles_failed'] += 1
                return None
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")
            self.stats['articles_failed'] += 1
            return None
    
    def _extract_article_from_response(self, resp, article):
        """Extract article content from response"""
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Xóa các thẻ không cần thiết
        for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
            tag.decompose()
        
        # Tìm thẻ chứa nội dung chính
        # Thử tìm các container phổ biến
        main_content = None
        for selector in [
            'article',
            'main',
            '.content',
            '.article-content',
            '.post-content',
            '#content',
            '.entry-content'
        ]:
            if selector.startswith('.'):
                main_content = soup.find(class_=selector[1:])
            elif selector.startswith('#'):
                main_content = soup.find(id=selector[1:])
            else:
                main_content = soup.find(selector)
            
            if main_content:
                break
        
        # Nếu không tìm thấy container, dùng toàn bộ body
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Lấy toàn bộ text từ container đã tìm được
        full_text = main_content.get_text(separator='\n', strip=True)
        
        # Làm sạch text: loại bỏ các dòng trống thừa và khoảng trắng
        content_text = re.sub(r'\n{3,}', '\n\n', full_text)
        content_text = re.sub(r' +', ' ', content_text)
        
        title_elem = soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else article['title']
        
        date_elem = soup.find('time') or soup.find(class_=re.compile(r'date|published'))
        date_str = date_elem.get_text(strip=True) if date_elem else article.get('date', '')
        
        summary = content_text[:500].strip()
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '_', slug)
        slug = slug[:100]
        
        result = {
            'article_id': article['article_id'],
            'url': article['url'],
            'title': title,
            'slug': slug,
            'date': date_str,
            'summary': summary,
            'content': content_text,
            'content_length': len(content_text),
            'crawled_at': datetime.now().isoformat()
        }
        
        self.stats['articles_crawled'] += 1
        return result
    
    def save_articles(self, articles: List[Dict[str, str]], output_file: str):
        """Lưu danh sách articles vào file JSON"""
        filepath = self.output_dir / output_file
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Saved to: {filepath}")
    
    def crawl_all(self, max_pages: int = 5, save_mode: str = 'single'):
        """
        Crawl toàn bộ articles và lưu vào JSON
        
        Args:
            max_pages: Số trang listing tối đa
            save_mode: 'single' (1 file duy nhất) hoặc 'individual' (mỗi article 1 file)
        """
        self.stats['start_time'] = datetime.now()
        timestamp = self.stats['start_time'].strftime('%Y%m%d_%H%M%S')
        
        # Step 1: Crawl article list
        articles = self.crawl_article_list(max_pages)
        
        if not articles:
            print("\n❌ No articles found!")
            return
        
        # Save article list
        list_file = f"article_list_{timestamp}.json"
        self.save_articles(articles, list_file)
        
        # Step 2: Crawl each article content
        print(f"\n{'='*80}")
        print(f"STEP 2: Crawling full content for {len(articles)} articles...")
        print(f"{'='*80}\n")
        
        full_articles = []
        
        for i, article in enumerate(articles, 1):
            print(f"[{i}/{len(articles)}] {article['article_id']}: {article['title'][:60]}...")
            
            full_article = self.crawl_article_content(article)
            
            if full_article:
                full_articles.append(full_article)
                print(f"   ✅ {full_article['content_length']:,} chars")
                
                # Save individual file with title-based filename
                if save_mode in ['individual', 'both']:
                    individual_file = f"{full_article['slug']}_{full_article['article_id']}.json"
                    self.save_articles([full_article], individual_file)
            
            # Be nice to the server
            time.sleep(1)  # Increased delay
        
        # Save all articles in one file
        if save_mode == 'single' or save_mode == 'both':
            all_file = f"all_articles_{timestamp}.json"
            self.save_articles(full_articles, all_file)
        
        # Step 3: Summary report
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        print(f"\n{'='*80}")
        print("CRAWL SUMMARY")
        print(f"{'='*80}")
        print(f"Listing pages crawled: {self.stats['total_listing_pages']}")
        print(f"Articles found:        {self.stats['total_articles_found']}")
        print(f"Articles crawled:      {self.stats['articles_crawled']} ✅")
        print(f"Articles failed:       {self.stats['articles_failed']} ❌")
        print(f"Duration:              {duration:.1f}s")
        print(f"Output directory:      {self.output_dir.absolute()}")
        print(f"{'='*80}\n")
        
        # Save summary report
        summary = {
            'crawl_date': timestamp,
            'statistics': self.stats,
            'output_files': {
                'article_list': list_file,
                'full_articles': all_file if save_mode in ['single', 'both'] else f"{len(full_articles)} individual files"
            }
        }
        
        summary_file = self.output_dir / f"crawl_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"📊 Summary saved to: {summary_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Crawl economic articles from thongkehungyen.nso.gov.vn'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=5,
        help='Maximum number of listing pages to crawl (default: 5)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/crawled',
        help='Output directory for JSON files (default: data/crawled)'
    )
    parser.add_argument(
        '--save-mode',
        type=str,
        choices=['single', 'individual', 'both'],
        default='single',
        help='Save mode: single file, individual files, or both (default: single)'
    )
    
    args = parser.parse_args()
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║         ECONOMIC ARTICLES CRAWLER - Hưng Yên Statistics          ║
╚═══════════════════════════════════════════════════════════════════╝

Configuration:
  - Max listing pages: {args.max_pages}
  - Output directory:  {args.output_dir}
  - Save mode:         {args.save_mode}

Starting crawl...
""")
    
    crawler = EconomicArticleCrawler(output_dir=args.output_dir)
    crawler.crawl_all(max_pages=args.max_pages, save_mode=args.save_mode)
    
    print("\n✨ Done!")


if __name__ == '__main__':
    main()
