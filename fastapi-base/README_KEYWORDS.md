# Keyword Management System

## Architecture

### Core Components

1. **Service Layer** (`app/services/statistics/`)
   - `statistics_service.py`: Core logic với `regenerate_keywords_with_gpt()`
   - `keyphrase_extractor_v2.py`: Entity-preserving n-gram extraction

2. **API Layer** (`app/api/statistics.py`)
   - `POST /api/stats/keywords/regenerate?limit=200` - Regenerate keywords
   - `GET /api/stats/keywords?limit=50` - Get current keywords
   - `GET /api/stats/overview?period_type=day` - Statistics overview

3. **Database** (`keyword_stats` table)
   - `keyword`: Cụm từ/từ khóa
   - `mention_count`: Số lần xuất hiện
   - `weight`: Trọng số (normalized)
   - `period_type`: 'all' | 'day' | 'week' | 'month'

## Features

### Entity Preservation
- Giữ nguyên địa danh: "hưng yên", "phố hiến", "hà nội" (không cắt thành "hưng" + "yên")
- GPT-4 intelligent filtering với prompt rõ ràng về entities

### Extraction Pipeline
1. Load articles from DB
2. Clean text (remove metadata, hashtags, URLs)
3. Extract n-grams (2-3 words) với CountVectorizer
4. Count mentions across documents
5. GPT-4 filtering (remove noise, keep meaningful phrases)
6. Save to `keyword_stats` table

## Usage

### API Call
```bash
curl -X POST http://localhost:7777/api/stats/keywords/regenerate?limit=200
```

### Python Code
```python
from app.services.statistics.statistics_service import StatisticsService
from app.core.database import SessionLocal

db = SessionLocal()
service = StatisticsService(db)
result = service.regenerate_keywords_with_gpt(limit=200)
# Returns: {"total": 27, "max_mentions": 100, "keywords": [...], "method": "gpt_cleaned"}
```

## Configuration

Environment variables:
- `OPENAI_API_KEY`: Required for GPT cleaning
- `POSTGRES_PORT`: Database port (default 5555)

## Results

Current keywords (top 10):
- hưng yên (100 mentions)
- phố hiến (10 mentions)
- giải phóng mặt bằng (9 mentions)
- hà nội (9 mentions)
- phát triển (5 mentions)
- dự án đầu tư (5 mentions)

## Integration Points

- **Superset Dashboard**: Queries `keyword_stats` for WordCloud visualization
- **Statistics Service**: Scheduled jobs can call `regenerate_keywords_with_gpt()`
- **Topic Service**: Can link keywords to topics for enriched analysis
