# Data Timestamp & Datetime Handling

## 📅 Tổng Quan

Hệ thống xử lý nhiều định dạng timestamp/datetime từ các nguồn khác nhau (Facebook, web scraping, API, etc.) và chuẩn hóa về Python `datetime` objects.

## 🔧 Các Định Dạng Được Hỗ Trợ

### 1. Unix Timestamp
```json
{
  "timestamp": 1767246269,           // int
  "created_at": 1767163175.702328    // float
}
```
**Output:** `datetime(2026, 1, 1, 12, 44, 29)`

### 2. ISO Format
```json
{
  "created_at": "2025-01-04T10:30:00"         // Standard ISO
  "published_at": "2025-01-04T10:30:00Z"      // ISO with timezone
  "updated_at": "2025-01-04T10:30:00+07:00"   // ISO with offset
}
```

### 3. Common String Formats
```json
{
  "created_at": "2025-01-04 10:30:00",   // YYYY-MM-DD HH:MM:SS
  "published_at": "2025-01-04",          // YYYY-MM-DD (date only)
  "updated_at": "04/01/2025 10:30:00",   // DD/MM/YYYY HH:MM:SS
  "date": "04/01/2025"                   // DD/MM/YYYY
}
```

## 🎯 Chuẩn Hóa Datetime

### Priority Order (từ cao → thấp)

Khi normalize document, hệ thống tìm datetime theo thứ tự:

**1. `published_at` field:**
```python
published_at = (
    doc.get('published_at') or                      # Direct field
    doc.get('meta_data', {}).get('timestamp') or    # Facebook timestamp
    doc.get('created_at')                           # Fallback
)
```

**2. `created_at` field:**
```python
created_at = doc.get('created_at')  # System creation time
```

**3. `updated_at` field:**
```python
updated_at = doc.get('updated_at')  # System update time
```

## 📱 Facebook Data Example

### Input (Raw Facebook Post)
```json
{
  "meta_data": {
    "post_id": "1418547042966200",
    "timestamp": 1767246269,              // ← Unix timestamp (post time)
    "comments_count": 199,
    "reactions_count": 291,
    "reshare_count": 26,
    "reactions": {
      "like": 201,
      "love": 8,
      "haha": 67
    },
    "author": {
      "id": "100044327531510",
      "name": "Nhật Ký Yêu Nước"
    }
  },
  "created_at": 1767163175.702328,        // ← Unix timestamp (crawl time)
  "updated_at": 1767163175.7024,
  "data_type": "facebook",
  "content": "...",
  "url": "https://www.facebook.com/..."
}
```

### Output (Normalized)
```json
{
  "id": 8238,
  "source_type": "facebook",
  "platform": "facebook",
  "url": "https://www.facebook.com/...",
  
  "published_at": "2026-01-01T12:44:29",      // ✅ Từ meta_data.timestamp
  "created_at": "2025-12-31T13:39:35.702328", // ✅ Từ created_at
  "updated_at": "2025-12-31T13:39:35.702400", // ✅ Từ updated_at
  
  "engagement": {
    "comments": 199,
    "reactions": 291,
    "shares": 26
  },
  
  "author": {
    "id": "100044327531510",
    "name": "Nhật Ký Yêu Nước",
    "url": "https://www.facebook.com/NhatKyYeuNuocVN"
  },
  
  "metadata": {
    "post_id": "1418547042966200",
    "post_type": "post",
    "reactions": {
      "like": 201,
      "love": 8,
      "haha": 67
    }
  }
}
```

## 🧪 Testing

### Test Timestamp Parsing
```bash
cd /home/ai_team/lab/pipeline_mxh/fastapi-base
python test_data_timestamp.py
```

**Expected Output:**
```
✅ Unix timestamp (int)     → 2025-12-31 13:39:35
✅ Unix timestamp (float)   → 2025-12-31 13:39:35.702328
✅ ISO format               → 2025-01-04 10:30:00
✅ ISO with Z               → 2025-01-04 10:30:00+00:00
✅ YYYY-MM-DD HH:MM:SS     → 2025-01-04 10:30:00
✅ DD/MM/YYYY              → 2025-01-04 00:00:00
```

## 🔍 Implementation Details

### DataNormalizer Class

**Method: `_parse_timestamp(value)`**

```python
def _parse_timestamp(self, value) -> Optional[datetime]:
    """Parse various timestamp formats to datetime"""
    
    # 1. Unix timestamp (int or float)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    
    # 2. ISO format string
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except:
            pass
        
        # Try common formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y'
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except:
                continue
    
    # 3. Already datetime
    if isinstance(value, datetime):
        return value
    
    return None
```

### Facebook Metadata Extraction

**Method: `_extract_facebook_metadata(doc)`**

```python
def _extract_facebook_metadata(self, doc: Dict) -> Dict:
    """Extract and normalize Facebook-specific metadata"""
    meta_data = doc.get('meta_data', {})
    
    extracted = {
        'post_id': meta_data.get('post_id'),
        'post_type': meta_data.get('type'),
        'post_url': meta_data.get('url'),
        
        # Parse timestamp
        'published_at': self._parse_timestamp(meta_data.get('timestamp')),
        
        # Engagement metrics
        'comments_count': meta_data.get('comments_count', 0),
        'reactions_count': meta_data.get('reactions_count', 0),
        'shares_count': meta_data.get('reshare_count', 0),
        
        # Reactions breakdown
        'reactions': meta_data.get('reactions', {}),
        
        # Author info
        'author_id': meta_data.get('author', {}).get('id'),
        'author_name': meta_data.get('author', {}).get('name'),
        'author_url': meta_data.get('author', {}).get('url'),
        
        # Media
        'has_image': bool(meta_data.get('image') or meta_data.get('album_preview')),
        'has_video': bool(meta_data.get('video') or meta_data.get('video_files')),
        'media_count': len(meta_data.get('album_preview', [])),
    }
    
    return {k: v for k, v in extracted.items() if v is not None}
```

## 📊 Database Storage

Khi save vào database (`articles` table), datetime được convert sang ISO string:

```python
# In SQLAlchemy model
class Article(Base):
    published_at = Column(DateTime)  # Stores as TIMESTAMP
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

# When inserting
article = Article(
    published_at=datetime.fromtimestamp(1767246269),  # Auto-converted
    created_at=datetime.now(),
    updated_at=datetime.now()
)
```

## 🎯 Best Practices

### 1. Always Use `_parse_timestamp()` for Datetime Fields
```python
# ✅ Good
published_at = self._parse_timestamp(doc.get('published_at'))

# ❌ Bad
published_at = doc.get('published_at')  # Might be int, str, or datetime
```

### 2. Handle Multiple Sources
```python
# Try multiple fields with fallback
published_at = (
    self._parse_timestamp(doc.get('published_at')) or
    self._parse_timestamp(doc.get('meta_data', {}).get('timestamp')) or
    self._parse_timestamp(doc.get('created_at'))
)
```

### 3. Validate Before Saving
```python
# Check if datetime is valid
if published_at and published_at > datetime.now():
    warnings.append("Published date is in the future")
```

### 4. Use ISO Format for API Responses
```python
# Convert to ISO string for JSON serialization
response = {
    "published_at": published_at.isoformat() if published_at else None
}
```

## 🚨 Common Issues & Solutions

### Issue 1: "Timestamp is in milliseconds"
**Problem:** JavaScript timestamps (1767246269000)
```python
# Solution: Detect and divide by 1000
if isinstance(value, int) and value > 1e12:
    value = value / 1000
return datetime.fromtimestamp(value)
```

### Issue 2: "Timezone mismatch"
**Problem:** Timestamps không có timezone
```python
# Solution: Add default timezone (UTC+7 for Vietnam)
from datetime import timezone, timedelta
vn_tz = timezone(timedelta(hours=7))
dt = datetime.fromtimestamp(value, tz=vn_tz)
```

### Issue 3: "Invalid format string"
**Problem:** Format không match
```python
# Solution: Try multiple formats with fallback
formats = [
    '%Y-%m-%d %H:%M:%S',
    '%d/%m/%Y %H:%M:%S',
    '%m/%d/%Y %H:%M:%S',  # US format
    '%Y/%m/%d %H:%M:%S'   # Asian format
]
```

## 📈 Performance Tips

1. **Cache parsed timestamps** (if parsing same value multiple times)
2. **Use bulk operations** when processing many documents
3. **Index datetime columns** in database for faster queries

## 🔗 Related Files

- **Service:** [app/services/etl/data_normalizer.py](app/services/etl/data_normalizer.py)
- **Test:** [test_data_timestamp.py](test_data_timestamp.py)
- **Pipeline:** [app/services/etl/data_pipeline.py](app/services/etl/data_pipeline.py)
- **Guide:** [DATA_PIPELINE_GUIDE.md](DATA_PIPELINE_GUIDE.md)

## 📝 Summary

✅ **Supported:** Unix timestamp (int/float), ISO format, common string formats  
✅ **Facebook:** Auto-extract `meta_data.timestamp` → `published_at`  
✅ **Normalized:** All datetime → Python `datetime` objects  
✅ **Database:** Auto-convert to TIMESTAMP type  
✅ **API:** Return as ISO string (`isoformat()`)

**One command to test:**
```bash
python test_data_timestamp.py
```
