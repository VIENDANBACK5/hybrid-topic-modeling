from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import json
from sqlalchemy.orm import Session
from app.services.crawler.pipeline import CrawlerPipeline
from app.services.crawler.smart_pipeline import get_smart_crawler_pipeline
from app.core.database import get_db
from app.models.model_article import Article
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

crawler_pipeline = CrawlerPipeline()
smart_crawler_pipeline = get_smart_crawler_pipeline()


class CrawlRequest(BaseModel):
    """
    CHỈ CẦN 2 THAM SỐ BẮT BUỘC:
    - url: Link cần crawl
    - mode: "preview" | "quick" | "max" | "full"
    """
    url: str  # Link web cần crawl
    mode: str = "max"  # "preview" (xem trước), "quick" (nhanh), "max" (mạnh nhất), "full" (chi tiết)
    
    # Advanced options (ẩn, không bắt buộc)
    custom_params: Optional[Dict] = None  # Chỉ dùng khi muốn custom


class CrawlResponse(BaseModel):
    status: str
    processed: int
    saved_to_db: int = 0
    db_duplicates: int = 0
    documents: List[Dict] = []
    
    # Optional - tùy mode
    preview: Optional[Dict] = None  # Nếu mode="preview"
    stats: Optional[Dict] = None  # Nếu mode="full"


@router.post("", response_model=CrawlResponse)
async def crawl(request: CrawlRequest, db: Session = Depends(get_db)):
    """
    🚀 CRAWL API - CỰC KỲ ĐƠN GIẢN
    
    Chỉ cần 2 tham số:
    - url: Link web cần crawl
    - mode: Chế độ crawl
    
    Modes:
    - "preview": Xem trước (title, description, số links) - KHÔNG crawl
    - "quick": Crawl nhanh (50 trang, depth=2) 
    - "max": Crawl mạnh nhất (5000 trang, depth=5) - MẶC ĐỊNH
    - "full": Crawl + trả về stats
    
    Examples:
        {"url": "https://baohungyen.vn", "mode": "max"}
        {"url": "https://vnexpress.net", "mode": "preview"}
        {"url": "https://example.com", "mode": "full"}
    """
    try:
        # MODE: PREVIEW - chỉ xem trước, không crawl
        if request.mode == "preview":
            from app.services.crawler.fetchers import WebFetcher
            fetcher = WebFetcher()
            try:
                page_info = await fetcher.fetch_single(request.url, extract_content=False)
                return {
                    "status": "preview_only",
                    "processed": 0,
                    "documents": [],
                    "preview": {
                        "url": page_info.get("url"),
                        "title": page_info.get("metadata", {}).get("title"),
                        "description": page_info.get("metadata", {}).get("description"),
                        "links_found": len(page_info.get("links", [])),
                        "metadata": page_info.get("metadata")
                    }
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Preview failed: {str(e)}")
        
        # Xác định crawl params theo mode
        crawl_params = dict(request.custom_params) if request.custom_params else {}
        
        if request.mode == "max":
            # Crawl mạnh nhất - toàn bộ site
            crawl_params.update({
                "follow_links": True,
                "max_depth": 5,
                "max_pages": 5000,
                "delay_ms": 50,
                "use_sitemap": True
            })
            logger.info(f"MAX mode for {request.url}")
        elif request.mode == "quick":
            # Crawl nhanh - lấy mẫu
            crawl_params.update({
                "follow_links": True,
                "max_depth": 2,
                "max_pages": 50,
                "delay_ms": 100
            })
            logger.info(f"QUICK mode for {request.url}")
        elif request.mode == "full":
            # Full mode - như max nhưng trả về stats
            crawl_params.update({
                "follow_links": True,
                "max_depth": 5,
                "max_pages": 5000,
                "delay_ms": 50,
                "use_sitemap": True
            })
            logger.info(f"FULL mode for {request.url}")
        
        # Chạy crawler
        result = await crawler_pipeline.run(
            source_type="web",  # Mặc định web
            source=request.url,
            clean=True,  # Luôn clean
            dedupe=True,  # Luôn dedupe
            **crawl_params
        )
        
        # Lưu vào database (MẶC ĐỊNH luôn lưu)
        saved_to_db = 0
        db_duplicates = 0
        
        try:
            from app.models.model_source import Source
            from datetime import datetime
            
            documents = result.get("documents", [])
            domain = urlparse(request.url).netloc if request.url else "unknown"
            
            # Tự động tạo/cập nhật source
            source_record = db.query(Source).filter(Source.url == request.url).first()
            if not source_record:
                # Auto detect type dựa vào URL
                source_type = "news"  # Default
                if "facebook.com" in request.url or "fb.com" in request.url:
                    source_type = "social"
                elif "twitter.com" in request.url or "instagram.com" in request.url:
                    source_type = "social"
                elif any(x in request.url for x in ["forum", "group", "fanpage"]):
                    source_type = "forum"
                
                source_record = Source(
                    name=domain,
                    url=request.url,
                    type=source_type,
                    domain=domain,
                    is_active=True
                )
                db.add(source_record)
                db.flush()  # Get ID
            
            # Update crawl stats
            source_record.last_crawled_at = datetime.utcnow()
            source_record.last_article_count = len(documents)
                
            for doc in documents:
                # Doc structure: {source, source_id, content, raw_content, cleaned_content, metadata}
                url = doc.get("source_id") or doc.get("url") or doc.get("source")
                if not url or url in ["web", "rss", "file", "api"]:
                    continue
                
                # Check duplicate URL
                existing = db.query(Article).filter(Article.url == url).first()
                if existing:
                    db_duplicates += 1
                    continue
                
                # Get metadata
                meta = doc.get("metadata", {})
                
                # Create article record
                article = Article(
                    url=url,
                    source_type="web",
                    source=request.url,
                    domain=domain,
                    title=meta.get("title"),
                    content=doc.get("cleaned_content") or doc.get("content"),
                    summary=meta.get("description") or meta.get("summary"),
                    author=meta.get("author"),
                    published_date=meta.get("published_time"),
                    category=meta.get("category") or meta.get("section"),
                    tags=meta.get("tags"),
                    images=meta.get("images"),
                    videos=meta.get("videos"),
                    is_cleaned=True,
                    is_deduped=True,
                    word_count=len(doc.get("content", "").split()) if doc.get("content") else 0,
                    crawl_params=crawl_params,
                    raw_metadata=meta
                )
                db.add(article)
                saved_to_db += 1
            
            # Update source total articles
            if source_record:
                source_record.total_articles = db.query(Article).filter(Article.source == request.url).count()
            
            db.commit()
            logger.info(f"Saved {saved_to_db} articles, {db_duplicates} duplicates. Source updated.")
        except Exception as e:
            db.rollback()
            logger.error(f"DB error: {e}")

        # Lấy stats nếu mode="full"
        domain_stats = None
        if request.mode == "full":
            try:
                if domain:
                    from app.services.srv_crawl_history import CrawlHistoryService
                    crawl_service = CrawlHistoryService()
                    domain_stats = crawl_service.get_stats(db, domain)
            except Exception as e:
                logger.warning(f"Could not get stats: {e}")

        return {
            **result,
            "saved_to_db": saved_to_db,
            "db_duplicates": db_duplicates,
            "stats": domain_stats
        }
    except Exception as e:
        logger.error(f"Crawl error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """Get crawler status including LLM capabilities"""
    status = {
        "status": "ready",
        "available_sources": ["web", "rss", "file", "api"],
        "traditional_pipeline": "available",
        "smart_pipeline": "available"
    }
    
    # Add LLM capabilities info
    try:
        pipeline_stats = smart_crawler_pipeline.get_pipeline_stats()
        status["llm_enabled"] = pipeline_stats.get("llm_enabled", False)
        status["llm_features"] = pipeline_stats.get("llm_features", [])
        status["cost_tracking"] = pipeline_stats.get("cost_aware", False)
    except Exception as e:
        logger.warning(f"Could not get smart pipeline stats: {e}")
    
    return status


class PreviewRequest(BaseModel):
    url: str
    max_depth: int = 1  # Chỉ crawl 1 trang để preview


class PreviewResponse(BaseModel):
    url: str
    page_type: str
    title: str
    total_internal_links: int  # Tổng số links thực tế (không bị limit)
    internal_links_sample: List[str]  # Sample 20 links đầu
    estimated_pages: int
    metadata_summary: Dict
    warning: Optional[str] = None


@router.post("/preview", response_model=PreviewResponse)
async def preview_crawl(request: PreviewRequest):
    """
    Preview metadata của 1 trang (homepage) trước khi crawl thật.
    Chỉ đếm links ở trang đầu tiên.
    
    Để đếm TẤT CẢ links trong toàn bộ domain, dùng /preview-full
    """
    try:
        # Fetch HTML trực tiếp để đếm links
        import httpx
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse
        
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            response = await client.get(request.url, follow_redirects=True)
            html = response.text
        
        soup = BeautifulSoup(html, 'html.parser')
        base_domain = urlparse(request.url).netloc
        
        # Đếm TẤT CẢ internal links
        all_internal_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('#') or href.startswith('javascript:'):
                continue
            
            absolute_url = urljoin(request.url, href)
            link_domain = urlparse(absolute_url).netloc
            
            if link_domain == base_domain:
                all_internal_links.append(absolute_url)
        
        # Deduplicate
        all_internal_links = list(dict.fromkeys(all_internal_links))
        total_links = len(all_internal_links)
        
        # Crawl để lấy metadata chi tiết
        result = await crawler_pipeline.run(
            source_type="web",
            source=request.url,
            clean=False,
            dedupe=False,
            follow_links=False,
            max_pages=1
        )
        
        metadata = {}
        if result.get("documents"):
            doc = result["documents"][0]
            metadata = doc.get("metadata", {})
        
        
        # Ước tính số trang nếu crawl với follow_links
        estimated_pages = min(total_links, 100)  # Cap tối đa 100
        
        # Tổng hợp metadata
        summary = {
            "h1_count": len(metadata.get("h1", [])),
            "h2_count": len(metadata.get("h2", [])),
            "h3_count": len(metadata.get("h3", [])),
            "paragraphs_count": len(metadata.get("paragraphs", [])),
            "images_count": len(metadata.get("images", [])),
            "videos_count": len(metadata.get("videos", [])),
            "content_length": len(result.get("documents", [{}])[0].get("content", "") if result.get("documents") else ""),
        }
        
        # Cảnh báo nếu quá nhiều links
        warning = None
        if total_links > 500:
            warning = f"⚠️⚠️ CỰC NHIỀU! Có {total_links} internal links! Khuyến nghị: follow_links=false hoặc max_pages <= 3"
        elif total_links > 200:
            warning = f"⚠️ RẤT NHIỀU! Có {total_links} internal links! Nên giảm max_pages <= 5"
        elif total_links > 100:
            warning = f"⚠️ Có {total_links} internal links. Khuyến nghị max_pages <= 10"
        elif total_links > 50:
            warning = f"ℹ️ Có {total_links} internal links. Có thể crawl max_pages <= 20"
        
        return {
            "url": request.url,
            "page_type": metadata.get("page_type", "unknown"),
            "title": metadata.get("title", ""),
            "total_internal_links": total_links,
            "internal_links_sample": all_internal_links[:20],  # Chỉ show 20 links đầu
            "estimated_pages": estimated_pages,
            "metadata_summary": summary,
            "warning": warning
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PreviewFullRequest(BaseModel):
    url: str
    max_depth: int = 3  # Số tầng sâu để crawl recursive
    max_pages: int = 100  # Giới hạn tối đa số trang để tránh crawl vô hạn


class CategoryInfo(BaseModel):
    name: str
    total_links: int
    subcategories: Optional[Dict[str, int]] = {}  # {subcategory: số links}
    

class PreviewFullResponse(BaseModel):
    url: str
    total_pages_found: int
    total_unique_links: int
    total_categories: int
    standalone_links: int  # Links lẻ không thuộc danh mục nào
    categories_detail: Dict[str, Dict]  # {category: {total_links, subcategories}}
    depth_breakdown: Dict[int, int]
    warning: Optional[str] = None
    recommendation: str


@router.post("/preview-full", response_model=PreviewFullResponse)
async def preview_full_domain(request: PreviewFullRequest):
    """
    Preview thông minh: Phát hiện cấu trúc danh mục của website
    - Tự động phát hiện categories và subcategories
    - Đếm số links trong mỗi danh mục/danh mục con
    - Phân biệt links lẻ vs links trong danh mục
    - Không hiển thị chi tiết URLs (chỉ số lượng)
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse
        from collections import deque, defaultdict
        
        base_domain = urlparse(request.url).netloc
        visited = set()
        all_links_seen = set()
        to_visit = deque([(request.url, 0)])
        depth_count = {}
        
        # Structure: {category: {subcategory: count}}
        category_structure = defaultdict(lambda: defaultdict(int))
        standalone_links = []
        
        def parse_url_structure(url: str) -> tuple:
            """
            Parse URL thành (category, subcategory, is_standalone)
            Examples:
            - /dich-vu/spa-cham-soc-da → ('dich-vu', 'spa-cham-soc-da', False)
            - /tin-tuc → ('tin-tuc', None, False)
            - /page-123 → (None, None, True) # standalone
            """
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            
            if not path:
                return ('homepage', None, False)
            
            parts = [p for p in path.split('/') if p]
            
            if len(parts) == 0:
                return ('homepage', None, False)
            elif len(parts) == 1:
                # Single level: có thể là category hoặc standalone
                # Heuristic: nếu có dấu '-' nhiều thì là category, ngược lại là standalone
                if '-' in parts[0] or len(parts[0]) > 3:
                    return (parts[0], None, False)
                else:
                    return (None, None, True)
            elif len(parts) >= 2:
                # Multi-level: category/subcategory hoặc category/subcategory/item
                return (parts[0], parts[1] if len(parts) == 2 else f"{parts[1]}/...", False)
            
            return (None, None, True)
        
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            while to_visit and len(visited) < request.max_pages:
                current_url, depth = to_visit.popleft()
                
                if depth > request.max_depth or current_url in visited:
                    continue
                
                try:
                    response = await client.get(current_url, follow_redirects=True)
                    if response.status_code != 200:
                        continue
                    
                    visited.add(current_url)
                    depth_count[depth] = depth_count.get(depth, 0) + 1
                    
                    # Parse HTML và thu thập links
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if href.startswith('#') or href.startswith('javascript:'):
                            continue
                        
                        absolute_url = urljoin(current_url, href)
                        link_domain = urlparse(absolute_url).netloc
                        
                        if link_domain == base_domain:
                            all_links_seen.add(absolute_url)
                            
                            # Phân tích cấu trúc
                            category, subcategory, is_standalone = parse_url_structure(absolute_url)
                            
                            if is_standalone:
                                if absolute_url not in standalone_links:
                                    standalone_links.append(absolute_url)
                            elif category:
                                if subcategory:
                                    category_structure[category][subcategory] += 1
                                else:
                                    category_structure[category]['_root'] += 1
                            
                            if absolute_url not in visited:
                                to_visit.append((absolute_url, depth + 1))
                
                except Exception as e:
                    logger.debug(f"Error crawling {current_url}: {e}")
                    continue
        
        # Build categories detail
        categories_detail = {}
        for cat, subcats in category_structure.items():
            total = sum(subcats.values())
            subcategories = {k: v for k, v in subcats.items() if k != '_root'}
            
            categories_detail[cat] = {
                'total_links': total,
                'subcategories': subcategories if subcategories else {}
            }
        
        # Sort by total_links
        categories_detail = dict(sorted(
            categories_detail.items(), 
            key=lambda x: x[1]['total_links'], 
            reverse=True
        ))
        
        total_found = len(visited)
        total_unique_links = len(all_links_seen)
        total_categories = len(categories_detail)
        standalone_count = len(standalone_links)
        
        # Cảnh báo
        warning = None
        recommendation = ""
        
        if total_found >= request.max_pages:
            warning = f"⚠️ ĐÃ ĐẠT GIỚI HẠN! Crawl {total_found} trang, tìm {total_unique_links} links unique. Có thể còn nhiều hơn!"
            recommendation = f"🔴 Domain lớn! Có {total_categories} danh mục. Khuyến nghị:\n- Crawl từng danh mục cụ thể\n- max_pages <= 20 cho mỗi danh mục"
        elif total_unique_links > 1000:
            warning = f"⚠️ RẤT NHIỀU! {total_unique_links} links, {total_categories} danh mục"
            recommendation = f"� Khuyến nghị: Crawl theo từng danh mục, max_pages <= 30"
        elif total_unique_links > 500:
            warning = f"ℹ️ NHIỀU! {total_unique_links} links, {total_categories} danh mục"
            recommendation = f"� Có thể crawl toàn bộ với max_pages <= 50"
        else:
            recommendation = f"🟢 Domain nhỏ/vừa ({total_unique_links} links, {total_categories} danh mục). Crawl toàn bộ OK!"
        
        return {
            "url": request.url,
            "total_pages_found": total_found,
            "total_unique_links": total_unique_links,
            "total_categories": total_categories,
            "standalone_links": standalone_count,
            "categories_detail": categories_detail,
            "depth_breakdown": depth_count,
            "warning": warning,
            "recommendation": recommendation
        }
        
    except Exception as e:
        logger.error(f"Preview full error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== CRAWL BY CATEGORY =====================
class CrawlByCategoryRequest(BaseModel):
    url: str  # Base URL của domain
    category: str  # Tên category muốn crawl (ví dụ: "dich-vu", "tin-tuc")
    subcategory: Optional[str] = None  # Subcategory cụ thể (ví dụ: "spa-cham-soc-da")
    max_pages: int = 50  # Giới hạn số trang crawl trong category này
    max_depth: int = 2  # Độ sâu crawl trong category
    clean: bool = True
    dedupe: bool = True
    save: bool = True
    save_dir: Optional[str] = "data/processed"
    filename: Optional[str] = None


class CrawlByCategoryResponse(BaseModel):
    status: str
    category: str
    subcategory: Optional[str]
    total_crawled: int
    documents: List[Dict] = []
    saved_file: Optional[str] = None
    stats: Dict


@router.post("/by-category", response_model=CrawlByCategoryResponse)
async def crawl_by_category(request: CrawlByCategoryRequest):
    """
    Crawl chỉ các trang thuộc category/subcategory cụ thể.
    
    Ví dụ:
    - category="dich-vu", subcategory="spa-cham-soc-da"
      → Chỉ crawl các link có path: /dich-vu/spa-cham-soc-da/*
    
    - category="tin-tuc", subcategory=None
      → Crawl tất cả link có path: /tin-tuc/*
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
        from collections import deque
        
        # Parse domain
        parsed = urlparse(request.url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Xây dựng category path pattern
        if request.subcategory:
            category_pattern = f"/{request.category}/{request.subcategory}"
        else:
            category_pattern = f"/{request.category}"
        
        logger.info(f"Crawl by category: {category_pattern} from {base_domain}")
        
        # BFS crawl với filter theo category
        visited = set()
        to_visit = deque()
        category_links = []
        
        # Thêm URL gốc của category vào queue
        start_url = f"{base_domain}{category_pattern}"
        to_visit.append((start_url, 0))
        visited.add(start_url)
        
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            while to_visit and len(category_links) < request.max_pages:
                current_url, depth = to_visit.popleft()
                
                if depth > request.max_depth:
                    continue
                
                try:
                    response = await client.get(current_url)
                    if response.status_code != 200:
                        continue
                    
                    # Parse HTML và tìm links
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Lưu URL hiện tại vào danh sách cần crawl
                    category_links.append(current_url)
                    
                    # Tìm tất cả internal links thuộc category
                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag['href']
                        
                        # Chuẩn hóa URL
                        if href.startswith('/'):
                            link = base_domain + href
                        elif href.startswith('http'):
                            link_parsed = urlparse(href)
                            if link_parsed.netloc != parsed.netloc:
                                continue  # Skip external links
                            link = href
                        else:
                            continue
                        
                        # Lọc chỉ lấy links thuộc category pattern
                        link_path = urlparse(link).path
                        if not link_path.startswith(category_pattern):
                            continue
                        
                        # Thêm vào queue nếu chưa visit
                        if link not in visited and len(category_links) < request.max_pages:
                            visited.add(link)
                            to_visit.append((link, depth + 1))
                
                except Exception as e:
                    logger.warning(f"Error crawling {current_url}: {e}")
                    continue
        
        logger.info(f"Found {len(category_links)} links in category {category_pattern}")
        
        # Giờ crawl thực sự các links đã filter
        # Crawl từng URL một vì pipeline không hỗ trợ batch URLs
        all_documents = []
        for url in category_links:
            try:
                result = await crawler_pipeline.run(
                    source_type="web",
                    source=url,
                    clean=request.clean,
                    dedupe=False,  # Sẽ dedupe tổng thể sau
                    follow_links=False  # Không follow thêm links
                )
                if result.get('documents'):
                    all_documents.extend(result['documents'])
            except Exception as e:
                logger.warning(f"Error crawling {url}: {e}")
                continue
        
        # Dedupe nếu cần
        if request.dedupe:
            from app.services.etl.dedupe import Deduplicator
            deduper = Deduplicator()
            all_documents = deduper.deduplicate(all_documents)
        
        # Lưu file nếu cần
        saved_path = None
        if request.save:
            try:
                base_dir = Path(request.save_dir or "data/processed")
                base_dir.mkdir(parents=True, exist_ok=True)
                
                if request.filename:
                    filename = request.filename
                else:
                    category_name = f"{request.category}"
                    if request.subcategory:
                        category_name += f"_{request.subcategory}"
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{parsed.netloc}_{category_name}_{timestamp}.json"
                
                file_path = base_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(all_documents, f, ensure_ascii=False, indent=2)
                saved_path = str(file_path)
                logger.info(f"Saved to {saved_path}")
            except Exception as e:
                logger.error(f"Error saving file: {e}")
        
        # Tính stats
        stats = {
            "total_links_found": len(category_links),
            "total_crawled": len(all_documents),
            "category_pattern": category_pattern,
            "max_depth_used": request.max_depth,
            "max_pages_limit": request.max_pages
        }
        
        return {
            "status": "success",
            "category": request.category,
            "subcategory": request.subcategory,
            "total_crawled": len(all_documents),
            "documents": all_documents,
            "saved_file": saved_path,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Crawl by category error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= INCREMENTAL CRAWLING ENDPOINTS =============

class IncrementalCrawlRequest(BaseModel):
    """Request for incremental crawling - only new URLs"""
    domain: str  # e.g., "baohungyen.vn"
    category: Optional[str] = None  # e.g., "chinh-tri"
    limit: int = 100  # max URLs to crawl
    article_only: bool = True  # only crawl article pages (skip listing pages)
    force_recrawl_days: Optional[int] = None  # re-crawl articles older than X days


class CrawlStatsResponse(BaseModel):
    """Crawl history statistics"""
    domain: str
    total_urls: int
    pending: int
    success: int
    failed: int
    articles: int
    categories: Dict[str, int]


@router.get("/stats/{domain}", response_model=CrawlStatsResponse)
async def get_crawl_stats(domain: str, db: Session = Depends(get_db)):
    """Get crawl statistics for a domain"""
    try:
        from app.services.srv_crawl_history import CrawlHistoryService
        
        stats = CrawlHistoryService.get_stats(db, domain)
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/incremental", response_model=CrawlResponse)
async def incremental_crawl(request: IncrementalCrawlRequest, db: Session = Depends(get_db)):
    """
    Incremental crawling - only crawl new/pending URLs
    Use this for daily updates instead of full site crawl
    """
    try:
        from app.services.srv_crawl_history import CrawlHistoryService
        
        # Get URLs that need crawling
        pending_urls = CrawlHistoryService.get_pending_urls(
            db=db,
            domain=request.domain,
            limit=request.limit,
            category=request.category,
            article_only=request.article_only
        )
        
        # If force_recrawl_days specified, also get old URLs
        if request.force_recrawl_days:
            old_urls = CrawlHistoryService.get_urls_needing_recrawl(
                db=db,
                domain=request.domain,
                days_old=request.force_recrawl_days,
                limit=max(10, request.limit // 10)  # 10% of limit
            )
            pending_urls.extend(old_urls)
        
        if not pending_urls:
            return {
                "status": "success",
                "processed": 0,
                "documents": [],
                "saved_to_db": 0,
                "db_duplicates": 0,
                "saved_file": None
            }
        
        logger.info(f"Incremental crawl: {len(pending_urls)} URLs to crawl from {request.domain}")
        
        # Crawl each URL individually (no follow_links)
        all_docs = []
        saved_to_db = 0
        db_duplicates = 0
        
        for url in pending_urls:
            try:
                # Crawl single URL
                result = await crawler_pipeline.run(
                    source_type="web",
                    source=url,
                    clean=True,
                    dedupe=False,  # already deduped by history
                    params={
                        "follow_links": False,  # don't follow, just this URL
                        "max_pages": 1
                    }
                )
                
                if result['documents']:
                    doc = result['documents'][0]
                    all_docs.append(doc)
                    
                    # Save to DB
                    url_to_save = doc.get("source_id") or doc.get("url") or doc.get("source")
                    
                    # Check duplicate
                    existing = db.query(Article).filter(Article.url == url_to_save).first()
                    if existing:
                        db_duplicates += 1
                        CrawlHistoryService.mark_crawled(
                            db=db,
                            url=url_to_save,
                            success=True,
                            article_id=existing.id
                        )
                        continue
                    
                    # Create new article
                    meta = doc.get("metadata", {})
                    article = Article(
                        url=url_to_save,
                        source_type="web",
                        source=request.domain,
                        domain=request.domain,
                        content=doc.get("cleaned_content") if doc.get("cleaned_content") else doc.get("content"),
                        raw_content=doc.get("raw_content"),
                        title=meta.get("title"),
                        summary=doc.get("summary"),
                        author=meta.get("author"),
                        published_date=meta.get("published"),
                        category=meta.get("category") or request.category,
                        tags=meta.get("tags"),
                        images=doc.get("images"),
                        videos=doc.get("videos"),
                        internal_links=doc.get("internal_links"),
                        word_count=len(doc.get("content", "").split()) if doc.get("content") else 0,
                        is_cleaned=bool(doc.get("cleaned_content")),
                        crawl_params={"incremental": True, "category": request.category},
                        raw_metadata=meta
                    )
                    db.add(article)
                    db.flush()  # Get article ID
                    
                    # Mark as crawled in history
                    CrawlHistoryService.mark_crawled(
                        db=db,
                        url=url_to_save,
                        success=True,
                        article_id=article.id,
                        page_metadata=meta,
                        child_links_count=len(doc.get("internal_links", []))
                    )
                    
                    saved_to_db += 1
                    
                else:
                    # No content found
                    CrawlHistoryService.mark_crawled(
                        db=db,
                        url=url,
                        success=False,
                        error_message="No content extracted"
                    )
                    
            except Exception as e:
                logger.error(f"Error crawling {url}: {e}")
                CrawlHistoryService.mark_crawled(
                    db=db,
                    url=url,
                    success=False,
                    error_message=str(e)
                )
        
        db.commit()
        logger.info(f"Incremental crawl complete: {saved_to_db} new articles, {db_duplicates} duplicates")
        
        return {
            "status": "success",
            "processed": len(all_docs),
            "documents": all_docs,
            "saved_to_db": saved_to_db,
            "db_duplicates": db_duplicates,
            "saved_file": None
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Incremental crawl error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover")
async def discover_urls(
    domain: str,
    start_url: Optional[str] = None,
    max_pages: int = 50,
    db: Session = Depends(get_db)
):
    """
    Discovery phase: crawl to find URLs without extracting content
    Builds the crawl_history table for later incremental crawling
    """
    try:
        from app.services.srv_crawl_history import CrawlHistoryService
        from app.services.crawler.fetchers import WebFetcher
        
        if not start_url:
            start_url = f"https://{domain}/"
        
        logger.info(f"Discovering URLs from {start_url}")
        
        # Use fetcher directly to get URLs only
        fetcher = WebFetcher()
        discovered_urls = set()
        
        # Crawl with follow_links to discover all URLs
        docs = fetcher.fetch(
            url=start_url,
            follow_links=True,
            max_pages=max_pages,
            max_depth=3,
            extract_content=False  # Don't extract content, just get URLs
        )
        
        # Collect all URLs
        for doc in docs:
            url = doc.get("source_id") or doc.get("url")
            if url:
                discovered_urls.add(url)
            # Also add internal links
            for link in doc.get("internal_links", []):
                discovered_urls.add(link)
        
        # Register URLs in history
        url_stats = CrawlHistoryService.discover_urls(
            db=db,
            urls=list(discovered_urls),
            source_domain=domain,
            source_category=None
        )
        
        stats = CrawlHistoryService.get_stats(db, domain)
        
        return {
            "status": "success",
            "discovered": len(discovered_urls),
            "new_urls": sum(1 for v in url_stats.values() if v == 'new'),
            "existing_urls": sum(1 for v in url_stats.values() if v == 'existing'),
            "article_exists": sum(1 for v in url_stats.values() if v == 'article_exists'),
            "domain_stats": stats
        }
        
    except Exception as e:
        logger.error(f"URL discovery error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= SMART CRAWL ENDPOINTS WITH LLM INTEGRATION =============

class SmartCrawlRequest(BaseModel):
    """Request for smart crawl with LLM features"""
    url: str
    mode: str = "max"
    
    # LLM Feature Flags
    enable_llm_enrichment: bool = True
    enable_semantic_dedupe: bool = True
    enable_auto_categorization: bool = True
    enable_summarization: bool = False
    
    # Cost Management
    max_cost: Optional[float] = None  # Max cost for this crawl
    priority: str = "balanced"  # low, balanced, high
    
    # Advanced Options
    force_enrich_all: bool = False  # Force enrich all docs (ignore smart selection)
    similarity_threshold: float = 0.85


class SmartCrawlResponse(BaseModel):
    """Response from smart crawl"""
    success: bool
    articles: List[Dict]
    
    # LLM Enhancement Info
    llm_enriched_count: int = 0
    duplicates_found: int = 0
    categories_assigned: int = 0
    
    # Cost Tracking
    estimated_cost: float
    actual_cost: float
    operations_performed: Dict[str, int]
    
    # Processing Stats
    processing_time: float
    high_value_docs: int
    low_value_docs: int


@router.post("/smart", response_model=SmartCrawlResponse)
async def crawl_with_smart_features(request: SmartCrawlRequest):
    """
    🚀 Smart Crawl với LLM Features
    
    Crawl và tự động enhance content bằng LLM:
    - Content enrichment (keywords, entities, summary)
    - Semantic deduplication
    - Auto categorization
    - Smart cost optimization
    
    Examples:
        # Balanced mode (default)
        POST /api/crawl/smart
        {
            "url": "https://vnexpress.net/category/news",
            "mode": "max",
            "enable_llm_enrichment": true,
            "priority": "balanced"
        }
        
        # High quality mode (enrich all)
        {
            "url": "https://important-source.com",
            "force_enrich_all": true,
            "priority": "high",
            "max_cost": 5.0
        }
        
        # Cost-saving mode (only dedupe)
        {
            "url": "https://many-articles.com",
            "enable_llm_enrichment": false,
            "enable_semantic_dedupe": true,
            "priority": "low"
        }
    """
    try:
        import time
        start_time = time.time()
        
        # Configure pipeline
        smart_crawler_pipeline.configure(
            enable_llm_enrichment=request.enable_llm_enrichment,
            enable_semantic_dedupe=request.enable_semantic_dedupe,
            enable_auto_categorization=request.enable_auto_categorization,
            enable_summarization=request.enable_summarization,
            force_enrich_all=request.force_enrich_all,
            similarity_threshold=request.similarity_threshold,
            max_cost=request.max_cost,
            priority=request.priority
        )
        
        # Run smart pipeline
        results = await smart_crawler_pipeline.run(request.url, mode=request.mode)
        
        processing_time = time.time() - start_time
        
        return SmartCrawlResponse(
            success=results["success"],
            articles=results["articles"],
            llm_enriched_count=results.get("llm_enriched_count", 0),
            duplicates_found=results.get("duplicates_found", 0),
            categories_assigned=results.get("categories_assigned", 0),
            estimated_cost=results.get("estimated_cost", 0.0),
            actual_cost=results.get("actual_cost", 0.0),
            operations_performed=results.get("operations_performed", {}),
            processing_time=processing_time,
            high_value_docs=results.get("high_value_docs", 0),
            low_value_docs=results.get("low_value_docs", 0)
        )
        
    except Exception as e:
        logger.error(f"Smart crawl error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost/report")
async def get_cost_report():
    """
    📊 Báo cáo chi phí LLM
    
    Returns:
        - Daily/monthly usage
        - Cost breakdown by operation
        - Budget status
        - Usage trends
    """
    try:
        cost_optimizer = smart_crawler_pipeline.cost_optimizer
        
        report = {
            "daily_usage": cost_optimizer.get_daily_usage(),
            "monthly_usage": cost_optimizer.get_monthly_usage(),
            "daily_budget": cost_optimizer.daily_budget,
            "budget_remaining": cost_optimizer.get_remaining_budget(),
            "operations_count": cost_optimizer.get_operations_count(),
            "cost_by_operation": cost_optimizer.get_cost_breakdown(),
            "avg_cost_per_doc": cost_optimizer.get_avg_cost_per_doc(),
            "recommendations": cost_optimizer.get_cost_recommendations()
        }
        
        return report
        
    except Exception as e:
        logger.error(f"Cost report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cost/set-budget")
async def set_daily_budget(daily_budget: float):
    """
    💰 Set ngân sách hàng ngày cho LLM operations
    
    Args:
        daily_budget: Budget in USD (e.g., 10.0 = $10/day)
    """
    try:
        if daily_budget < 0:
            raise HTTPException(status_code=400, detail="Budget must be positive")
            
        cost_optimizer = smart_crawler_pipeline.cost_optimizer
        cost_optimizer.set_daily_budget(daily_budget)
        
        return {
            "success": True,
            "daily_budget": daily_budget,
            "message": f"Daily budget set to ${daily_budget}"
        }
        
    except Exception as e:
        logger.error(f"Set budget error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cost/estimate")
async def estimate_crawl_cost(request: SmartCrawlRequest):
    """
    🧮 Ước tính chi phí trước khi crawl
    
    Returns cost estimate based on:
    - Expected number of documents
    - Enabled features
    - Document characteristics
    """
    try:
        cost_optimizer = smart_crawler_pipeline.cost_optimizer
        
        # Estimate based on similar past crawls
        estimate = cost_optimizer.estimate_crawl_cost(
            url=request.url,
            enable_enrichment=request.enable_llm_enrichment,
            enable_dedupe=request.enable_semantic_dedupe,
            enable_categorization=request.enable_auto_categorization,
            enable_summarization=request.enable_summarization,
            force_enrich_all=request.force_enrich_all
        )
        
        return {
            "estimated_cost": estimate["total_cost"],
            "estimated_documents": estimate["doc_count"],
            "cost_breakdown": estimate["breakdown"],
            "can_afford": estimate["can_afford"],
            "budget_remaining": estimate["budget_remaining"],
            "recommendation": estimate["recommendation"]
        }
        
    except Exception as e:
        logger.error(f"Cost estimation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline/stats")
async def get_pipeline_stats():
    """
    📈 Thống kê pipeline performance
    
    Returns:
        - Success rate
        - Average processing time
        - LLM usage stats
        - Quality metrics
    """
    try:
        stats = smart_crawler_pipeline.get_pipeline_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Pipeline stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PipelineConfig(BaseModel):
    """Pipeline configuration"""
    enable_llm_enrichment: bool = True
    enable_semantic_dedupe: bool = True
    enable_auto_categorization: bool = True
    enable_summarization: bool = False
    force_enrich_all: bool = False
    similarity_threshold: float = 0.85
    max_cost: Optional[float] = None
    priority: str = "balanced"


@router.post("/pipeline/configure")
async def configure_pipeline(config: PipelineConfig):
    """
    ⚙️ Configure pipeline settings
    
    Update pipeline configuration for all future crawls
    """
    try:
        smart_crawler_pipeline.configure(
            enable_llm_enrichment=config.enable_llm_enrichment,
            enable_semantic_dedupe=config.enable_semantic_dedupe,
            enable_auto_categorization=config.enable_auto_categorization,
            enable_summarization=config.enable_summarization,
            force_enrich_all=config.force_enrich_all,
            similarity_threshold=config.similarity_threshold,
            max_cost=config.max_cost,
            priority=config.priority
        )
        
        return {
            "success": True,
            "config": config.dict(),
            "message": "Pipeline configured successfully"
        }
        
    except Exception as e:
        logger.error(f"Configure pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class DedupeRequest(BaseModel):
    """Request for semantic deduplication"""
    articles: List[Dict]
    similarity_threshold: float = 0.85
    use_llm: bool = True


@router.post("/dedupe/find")
async def find_duplicates(request: DedupeRequest):
    """
    🔍 Tìm duplicates với semantic similarity
    
    Uses hybrid approach:
    1. Fast hash-based dedupe
    2. LLM semantic similarity for remaining candidates
    
    Returns list of duplicate groups
    """
    try:
        from app.services.etl.hybrid_dedupe import HybridDeduplicator
        
        deduplicator = HybridDeduplicator()
        
        duplicates = deduplicator.find_duplicates(
            articles=request.articles,
            similarity_threshold=request.similarity_threshold,
            use_llm=request.use_llm
        )
        
        return {
            "success": True,
            "duplicate_groups": duplicates["groups"],
            "total_duplicates": duplicates["total_duplicates"],
            "unique_articles": duplicates["unique_count"],
            "processing_time": duplicates["processing_time"],
            "cost": duplicates.get("cost", 0.0)
        }
        
    except Exception as e:
        logger.error(f"Deduplication error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
