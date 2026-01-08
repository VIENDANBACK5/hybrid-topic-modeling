Các bảng CÓ THỂ update mà KHÔNG cần train topic:
✅ 1. Articles (bảng chính - 36M records)
API: POST /topic-service/ingest
Thêm bài viết mới vào hệ thống
Tự động phân tích sentiment nếu enable
✅ 2. sentiment_analysis (11M records)
API: POST /topic-service/ingest (với analyze_sentiment: true)
Phân tích cảm xúc của bài viết
Không phụ thuộc vào topic training
✅ 3. article_field_classifications (1.9M records)
API: POST /api/v1/fields/classify
Phân loại bài viết vào 10 lĩnh vực (Chính trị, Kinh tế, v.v.)
Dùng keyword matching + LLM
✅ 4. field_statistics (80K records)
API: POST /api/v1/fields/statistics/update
Thống kê số lượng bài viết, engagement theo lĩnh vực
✅ 5. field_summaries (128K records)
API: POST /api/v1/fields/summaries/generate
Tóm tắt xu hướng theo lĩnh vực bằng LLM
✅ 6. daily_snapshots (64K records)
API: Tự động update qua POST /topic-service/ingest
Hoặc qua statistics service: stats_service.create_daily_snapshot()
✅ 7. trend_reports (80K records)
API: Tự động update khi ingest (nếu có đủ data)
stats_service.calculate_trend_report("weekly")
✅ 8. hot_topics (176K records)
API: Tự động update khi ingest
stats_service.calculate_hot_topics("weekly")
✅ 9. keyword_stats (272K records)
API: Tự động update khi ingest
stats_service.calculate_keyword_stats("weekly")
✅ 10. hashtag_stats (144K records)
API: trend_service.calculate_hashtag_stats("daily")
✅ 11. viral_contents (104K records)
API: trend_service.detect_viral_content("daily")
✅ 12. category_trend_stats (112K records)
API: trend_service.calculate_category_trends("daily")
🚫 Các bảng KHÔNG NÊN update (cần train topic):
article_bertopic_topics (1.6M) - Cần train BERTopic
article_custom_topics (48K) - Cần classify với custom topics
bertopic_discovered_topics (1.1M) - Tự động khi train
custom_topics (112K) - Quản lý thủ công
🎯 WORKFLOW KHI THÊM DATA MỚI (KHÔNG TRAIN TOPIC):
# 1. Ingest data mới (tự động analyze sentiment + update statistics)
curl -X POST "http://localhost:7777/topic-service/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "source": "web",
        "source_id": "https://example.com/article1",
        "content": "Nội dung bài viết...",
        "metadata": {
          "title": "Tiêu đề",
          "published": "2026-01-08T10:00:00Z",
          "category": "Chính trị"
        }
      }
    ],
    "skip_duplicates": true,
    "analyze_sentiment": true
  }'

# 2. Phân loại lĩnh vực
curl -X POST "http://localhost:7777/api/v1/fields/classify" \
  -H "Content-Type: application/json" \
  -d '{"method": "auto", "force_reclassify": false}'

# 3. Update thống kê lĩnh vực
curl -X POST "http://localhost:7777/api/v1/fields/statistics/update"

# 4. Tạo summary (tùy chọn)
curl -X POST "http://localhost:7777/api/v1/fields/summaries/generate" \
  -H "Content-Type: application/json" \
  -d '{"period": "daily"}'
Các bảng sẽ tự động update:

articles
sentiment_analysis
daily_snapshots
trend_reports
hot_topics
keyword_stats
hashtag_stats
viral_contents
category_trend_stats
article_field_classifications
field_statistics



topic over time 
các bảng liêm quan topci pic 


topic hot 