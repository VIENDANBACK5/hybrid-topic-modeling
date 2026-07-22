#!/usr/bin/env python3
"""Fill all statistics tables with current data"""

from app.core.database import SessionLocal
from app.models import Article, SentimentAnalysis
from app.models.model_statistics import (
    DailySnapshot, HotTopic, TopicMentionStats, WebsiteActivityStats
)
from app.models.model_trends import (
    CategoryTrendStats, HashtagStats, TrendAlert, ViralContent
)
from datetime import datetime
from collections import Counter
import json

db = SessionLocal()
print("\nPopulating all statistics tables...")

try:
    articles = db.query(Article).all()
    sentiments = db.query(SentimentAnalysis).all()
    
    print(f"Data: {len(articles)} articles, {len(sentiments)} sentiments\n")
    
    # Aggregations
    categories = Counter([s.category for s in sentiments if s.category])
    emotions = Counter([s.emotion_vi for s in sentiments if s.emotion_vi])
    domains = Counter([a.domain for a in articles if a.domain])
    
    # 1. Daily Snapshot
    snapshot = DailySnapshot(
        snapshot_date=datetime.now().date(),
        total_articles=len(articles),
        total_sources=len(domains),
        positive_count=sum(1 for s in sentiments if s.sentiment_group == 'positive'),
        negative_count=sum(1 for s in sentiments if s.sentiment_group == 'negative'),
        neutral_count=sum(1 for s in sentiments if s.sentiment_group == 'neutral'),
        emotion_counts=json.dumps(dict(emotions.most_common())),
        top_topics=json.dumps([{"topic": c, "count": n} for c, n in categories.most_common(5)]),
        top_keywords=json.dumps([]),
        top_sources=json.dumps([{"domain": d, "count": n} for d, n in domains.most_common(5)]),
        crisis_topics=json.dumps([]),
        trending_up=json.dumps([]),
        trending_down=json.dumps([])
    )
    db.add(snapshot)
    print("1. daily_snapshots")
    
    # 2. Hot Topics
    today = datetime.now().date()
    for i, (cat, count) in enumerate(categories.most_common(10), 1):
        cat_sents = [s for s in sentiments if s.category == cat]
        pos = sum(1 for s in cat_sents if s.sentiment_group == 'positive')
        neg = sum(1 for s in cat_sents if s.sentiment_group == 'negative')
        
        db.add(HotTopic(
            topic_id=i,
            topic_name=cat,
            period_type='weekly',
            period_start=today,
            period_end=today,
            mention_count=count,
            positive_count=pos,
            negative_count=neg,
            neutral_count=len(cat_sents) - pos - neg,
            hot_score=float(count),
            rank=i,
            is_hot=i <= 3
        ))
    print(f"2. hot_topics ({len(categories)} topics)")
    
    # 3. Topic Mentions
    for i, (cat, count) in enumerate(categories.items(), 1):
        cat_sents = [s for s in sentiments if s.category == cat]
        pos = sum(1 for s in cat_sents if s.sentiment_group == 'positive')
        neg = sum(1 for s in cat_sents if s.sentiment_group == 'negative')
        
        db.add(TopicMentionStats(
            topic_name=cat,
            category=cat,
            period_type='weekly',
            period_start=today,
            period_end=today,
            total_mentions=count,
            positive_mentions=pos,
            negative_mentions=neg,
            neutral_mentions=len(cat_sents) - pos - neg,
            rank_by_mention=i
        ))
    print(f"3. topic_mentions ({len(categories)} topics)")
    
    # 4. Website Stats
    for domain, count in domains.items():
        domain_art_ids = [a.id for a in articles if a.domain == domain]
        domain_sents = [s for s in sentiments if s.article_id in domain_art_ids]
        pos = sum(1 for s in domain_sents if s.sentiment_group == 'positive')
        neg = sum(1 for s in domain_sents if s.sentiment_group == 'negative')
        
        db.add(WebsiteActivityStats(
            domain=domain,
            period_type='weekly',
            period_start=today,
            period_end=today,
            article_count=count,
            positive_count=pos,
            negative_count=neg,
            neutral_count=len(domain_sents) - pos - neg
        ))
    print(f"4. website_stats ({len(domains)} domains)")
    
    # 5. Category Trends
    for i, (cat, count) in enumerate(categories.items(), 1):
        cat_sents = [s for s in sentiments if s.category == cat]
        pos = sum(1 for s in cat_sents if s.sentiment_group == 'positive')
        neg = sum(1 for s in cat_sents if s.sentiment_group == 'negative')
        
        db.add(CategoryTrendStats(
            category=cat,
            period_type='daily',
            period_start=today,
            period_end=today,
            total_mentions=count,
            unique_articles=count,
            positive_count=pos,
            negative_count=neg,
            neutral_count=len(cat_sents) - pos - neg,
            rank_by_mention=i
        ))
    print(f"5. category_trends ({len(categories)} categories)")
    
    # 6. Hashtag Stats
    hashtags = Counter()
    for art in articles:
        if art.content:
            words = art.content.split()
            tags = [w.lower() for w in words if w.startswith('#')]
            hashtags.update(tags)
    
    if hashtags:
        for i, (tag, count) in enumerate(hashtags.most_common(50), 1):
            db.add(HashtagStats(
                hashtag=tag,
                hashtag_normalized=tag.lower().lstrip('#'),
                period_type='daily',
                period_start=today,
                period_end=today,
                mention_count=count,
                rank=i
            ))
        print(f"6. hashtag_stats ({len(hashtags)} hashtags)")
    else:
        print("6. hashtag_stats (0 hashtags - no # in content)")
    
    # 7. Trend Alerts
    alert_count = 0
    for cat in categories.most_common(5):
        cat_name, cat_count = cat
        cat_sents = [s for s in sentiments if s.category == cat_name]
        neg = sum(1 for s in cat_sents if s.sentiment_group == 'negative')
        
        if neg > len(cat_sents) * 0.1:
            db.add(TrendAlert(
                alert_type='crisis',
                alert_level='medium',
                category=cat_name,
                current_count=neg,
                negative_ratio=neg / len(cat_sents),
                title=f'Cảm xúc tiêu cực cao trong {cat_name}',
                description=f'Đã phát hiện {neg} bài viết có cảm xúc tiêu cực trong danh mục {cat_name}'
            ))
            alert_count += 1
    print(f"7. trend_alerts ({alert_count} alerts)")
    
    # 8. Viral Content
    viral_arts = sorted(
        [a for a in articles if (a.likes_count or 0) + (a.shares_count or 0) > 0],
        key=lambda a: (a.likes_count or 0) + (a.shares_count or 0),
        reverse=True
    )[:20]
    
    if viral_arts:
        for art in viral_arts:
            art_sent = next((s for s in sentiments if s.article_id == art.id), None)
            db.add(ViralContent(
                article_id=art.id,
                title=art.title or '',
                url=art.url or '',
                source_domain=art.domain or '',
                period_type='daily',
                period_start=today,
                viral_score=float((art.likes_count or 0) + (art.shares_count or 0) * 2),
                share_count=art.shares_count or 0,
                engagement_score=float(art.engagement_rate or 0),
                sentiment_group=art_sent.sentiment_group if art_sent else 'neutral',
                emotion=art_sent.emotion if art_sent else None,
                emotion_vi=art_sent.emotion_vi if art_sent else None,
                category=art_sent.category if art_sent else None
            ))
        print(f"8. viral_content ({len(viral_arts)} posts)")
    else:
        print("8. viral_content (0 posts - no engagement data)")
    
    db.commit()
    print("\n🎉 ALL TABLES POPULATED!\n")
    
except Exception as e:
    db.rollback()
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
