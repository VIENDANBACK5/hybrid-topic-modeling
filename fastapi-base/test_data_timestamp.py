"""
Test data normalizer với Facebook data có timestamp và datetime phức tạp
"""
import json
from datetime import datetime
from app.services.etl.data_normalizer import DataNormalizer

# Sample Facebook data (như user cung cấp)
sample_fb_data = {
    "meta_data": {
        "post_id": "1418547042966200",
        "type": "post",
        "url": "https://www.facebook.com/NhatKyYeuNuocVN/posts/pfbid024jVWZY5RYUL457KWE9Qxp3TLNxKiBNGa9sJZgZrty7jPtKzaYKjna3nxc19rqpKEl",
        "message": "ĐỪNG QUÊN HỌ !",
        "timestamp": 1767246269,  # Unix timestamp
        "comments_count": 199,
        "reactions_count": 291,
        "reshare_count": 26,
        "reactions": {
            "angry": 0,
            "care": 10,
            "haha": 67,
            "like": 201,
            "love": 8,
            "sad": 4,
            "wow": 1
        },
        "author": {
            "id": "100044327531510",
            "name": "Nhật Ký Yêu Nước",
            "url": "https://www.facebook.com/NhatKyYeuNuocVN"
        }
    },
    "content": "ĐỪNG QUÊN HỌ !\nHôm nay chúng ta chuẩn bị đón một năm mới trong tình thân thương gia đình bạn bè.\nVà cũng ngày hôm nay, ở Việt Nam, vẫn còn hơn bốn trăm (400) tù nhân lương tâm...",
    "data_type": "facebook",
    "created_at": 1767163175.702328,  # Unix timestamp
    "url": "https://www.facebook.com/NhatKyYeuNuocVN/posts/pfbid024jVWZY5RYUL457KWE9Qxp3TLNxKiBNGa9sJZgZrty7jPtKzaYKjna3nxc19rqpKEl",
    "title": "ĐỪNG QUÊN HỌ ! Hôm nay chúng ta chuẩn bị đón một năm mới...",
    "id": 8238,
    "updated_at": 1767163175.7024
}

def test_normalize_facebook_data():
    """Test chuẩn hóa Facebook data"""
    print("\n" + "="*60)
    print("TEST: NORMALIZE FACEBOOK DATA")
    print("="*60)
    
    normalizer = DataNormalizer()
    
    print("\n📥 INPUT DATA:")
    print(f"  - ID: {sample_fb_data['id']}")
    print(f"  - Type: {sample_fb_data['data_type']}")
    print(f"  - Timestamp (meta_data): {sample_fb_data['meta_data']['timestamp']}")
    print(f"  - Created at: {sample_fb_data['created_at']}")
    print(f"  - Updated at: {sample_fb_data['updated_at']}")
    print(f"  - Comments: {sample_fb_data['meta_data']['comments_count']}")
    print(f"  - Reactions: {sample_fb_data['meta_data']['reactions_count']}")
    print(f"  - Shares: {sample_fb_data['meta_data']['reshare_count']}")
    
    # Normalize
    normalized, errors, warnings = normalizer.normalize_document(sample_fb_data)
    
    print("\n📤 NORMALIZED DATA:")
    print(f"  - ID: {normalized.get('id')}")
    print(f"  - Source Type: {normalized.get('source_type')}")
    print(f"  - Platform: {normalized.get('platform')}")
    print(f"  - URL: {normalized.get('url')}")
    
    print("\n📅 DATETIME FIELDS (PARSED):")
    pub_at = normalized.get('published_at')
    created = normalized.get('created_at')
    updated = normalized.get('updated_at')
    
    if pub_at:
        print(f"  ✅ Published At: {pub_at} (type: {type(pub_at).__name__})")
        print(f"     ISO: {pub_at.isoformat()}")
    else:
        print("  ❌ Published At: None")
    
    if created:
        print(f"  ✅ Created At: {created} (type: {type(created).__name__})")
    else:
        print("  ❌ Created At: None")
    
    if updated:
        print(f"  ✅ Updated At: {updated} (type: {type(updated).__name__})")
    else:
        print("  ❌ Updated At: None")
    
    print("\n📊 ENGAGEMENT METRICS:")
    engagement = normalized.get('engagement', {})
    print(f"  - Comments: {engagement.get('comments', 0)}")
    print(f"  - Reactions: {engagement.get('reactions', 0)}")
    print(f"  - Shares: {engagement.get('shares', 0)}")
    
    print("\n👤 AUTHOR INFO:")
    author = normalized.get('author', {})
    if author:
        print(f"  - ID: {author.get('id')}")
        print(f"  - Name: {author.get('name')}")
        print(f"  - URL: {author.get('url')}")
    else:
        print("  No author info")
    
    print("\n🏷️ METADATA:")
    metadata = normalized.get('metadata', {})
    print(f"  - Post ID: {metadata.get('post_id')}")
    print(f"  - Post Type: {metadata.get('post_type')}")
    print(f"  - Has Image: {metadata.get('has_image')}")
    print(f"  - Has Video: {metadata.get('has_video')}")
    print(f"  - Reactions breakdown: {metadata.get('reactions')}")
    
    print("\n📝 CONTENT:")
    content = normalized.get('content', '')
    print(f"  Length: {len(content)} chars")
    print(f"  Preview: {content[:100]}...")
    
    if errors:
        print(f"\n❌ ERRORS: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✅ NO ERRORS")
    
    if warnings:
        print(f"\n⚠️ WARNINGS: {len(warnings)}")
        for warning in warnings:
            print(f"  - {warning}")
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETED!")
    print("="*60)
    
    return normalized, errors, warnings

def test_various_timestamp_formats():
    """Test nhiều định dạng timestamp khác nhau"""
    print("\n" + "="*60)
    print("TEST: VARIOUS TIMESTAMP FORMATS")
    print("="*60)
    
    normalizer = DataNormalizer()
    
    test_cases = [
        {
            "name": "Unix timestamp (int)",
            "data": {"id": 1, "url": "https://example.com", "content": "test", "created_at": 1767163175, "data_type": "web"}
        },
        {
            "name": "Unix timestamp (float)",
            "data": {"id": 2, "url": "https://example.com", "content": "test", "created_at": 1767163175.702328, "data_type": "web"}
        },
        {
            "name": "ISO format",
            "data": {"id": 3, "url": "https://example.com", "content": "test", "created_at": "2025-01-04T10:30:00", "data_type": "web"}
        },
        {
            "name": "ISO with Z",
            "data": {"id": 4, "url": "https://example.com", "content": "test", "created_at": "2025-01-04T10:30:00Z", "data_type": "web"}
        },
        {
            "name": "YYYY-MM-DD HH:MM:SS",
            "data": {"id": 5, "url": "https://example.com", "content": "test", "created_at": "2025-01-04 10:30:00", "data_type": "web"}
        },
        {
            "name": "DD/MM/YYYY",
            "data": {"id": 6, "url": "https://example.com", "content": "test", "created_at": "04/01/2025", "data_type": "web"}
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Test: {test_case['name']}")
        print(f"   Input: {test_case['data']['created_at']}")
        
        normalized, errors, warnings = normalizer.normalize_document(test_case['data'])
        created_at = normalized.get('created_at')
        
        if created_at:
            print(f"   ✅ Parsed: {created_at} (ISO: {created_at.isoformat()})")
        else:
            print(f"   ❌ Failed to parse")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    # Test 1: Normalize Facebook data
    test_normalize_facebook_data()
    
    # Test 2: Various timestamp formats
    test_various_timestamp_formats()
