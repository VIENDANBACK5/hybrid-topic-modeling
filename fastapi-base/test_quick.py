"""
Quick test: Underthesea tokenizer + TopicGPT integration
"""
print("🚀 QUICK TEST - Vietnamese Tokenizer & TopicGPT\n")

# Test 1: Underthesea tokenizer
print("1️⃣  Testing Underthesea tokenizer...")
try:
    from app.services.etl.vietnamese_tokenizer import get_vietnamese_tokenizer
    tokenizer = get_vietnamese_tokenizer()
    if tokenizer:
        test_text = "Ủy ban nhân dân tỉnh họp bàn về phát triển kinh tế xã hội năm 2025"
        tokens = tokenizer(test_text)
        print(f"   ✅ Input: {test_text}")
        print(f"   ✅ Tokens (first 8): {tokens[:8]}")
    else:
        print("   ❌ Tokenizer not available")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: TopicModel với Vietnamese tokenizer
print("\n2️⃣  Testing TopicModel integration...")
try:
    from app.services.topic.model import TopicModel
    
    # Small test data
    test_docs = [
        "Kinh tế Việt Nam tăng trưởng tốt trong năm 2025",
        "Doanh nghiệp FDI quan tâm môi trường đầu tư",
        "UBND tỉnh họp bàn phát triển kinh tế",
        "Giáo dục cần đổi mới chương trình học",
        "Học sinh được học trực tuyến hiệu quả",
        "Trường học triển khai công nghệ mới",
        "Nông nghiệp phát triển bền vững",
        "Nông dân áp dụng công nghệ cao",
        "Sản xuất nông sản sạch tăng",
        "Y tế cải thiện chất lượng khám chữa bệnh",
        "Bệnh viện đầu tư thiết bị hiện đại",
        "Nhân viên y tế được đào tạo tốt"
    ]
    
    model = TopicModel(
        min_topic_size=2,
        use_vietnamese_tokenizer=True,
        enable_topicgpt=False
    )
    
    print("   🤖 Training...")
    topics, _ = model.fit(test_docs)
    info = model.get_topic_info()
    
    print(f"   ✅ Found {len(info['topics'])} topics")
    for topic in info['topics'][:3]:
        keywords = [w['word'] for w in topic['words'][:3]]
        print(f"      Topic {topic['topic_id']}: {', '.join(keywords)}")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: TopicGPT availability
print("\n3️⃣  Checking TopicGPT...")
import os
has_key = bool(os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY"))
if has_key:
    print("   ✅ API key found - TopicGPT available")
    print("   💡 Set enable_topicgpt=True to use")
else:
    print("   ⚠️  No API key - TopicGPT disabled")
    print("   💡 Set OPENAI_API_KEY or GEMINI_API_KEY to enable")

print("\n✨ Test completed!")
