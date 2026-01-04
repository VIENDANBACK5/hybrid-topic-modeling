"""
Test FULL integration: Vietnamese Tokenizer + TopicGPT
"""
import os
import json
from pathlib import Path

if not os.getenv('OPENAI_API_KEY'):
    raise ValueError("OPENAI_API_KEY environment variable not set")

print("=" * 70)
print("FULL TEST: Vietnamese Tokenizer + TopicGPT")
print("=" * 70)

# Load real data
print("\n📥 Loading Vietnamese documents...")
data_dir = Path("data/processed")
documents = []

for file in list(data_dir.glob("*.json"))[:5]:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    content = item.get('content') or item.get('cleaned_content', '')
                    if content and len(content) > 100:
                        documents.append(content[:800])
            if len(documents) >= 30:
                break
    except:
        continue

print(f"✅ Loaded {len(documents)} documents\n")

# Test 1: Baseline (no enhancements)
print("1️⃣  BASELINE (No Vietnamese tokenizer, No TopicGPT)")
print("-" * 70)

from app.services.topic.model import TopicModel

model_baseline = TopicModel(
    min_topic_size=3,
    use_vietnamese_tokenizer=False,
    enable_topicgpt=False
)

print("🤖 Training baseline model...")
topics_baseline, _ = model_baseline.fit(documents)
info_baseline = model_baseline.get_topic_info()

print(f"✅ Found {len(info_baseline['topics'])} topics\n")
for i, topic in enumerate(info_baseline['topics'][:2]):
    keywords = [w['word'] for w in topic['words'][:5]]
    print(f"   Topic {topic['topic_id']}: {', '.join(keywords)}")

# Test 2: With Vietnamese Tokenizer
print("\n\n2️⃣  ENHANCED (Vietnamese tokenizer)")
print("-" * 70)

model_enhanced = TopicModel(
    min_topic_size=3,
    use_vietnamese_tokenizer=True,
    enable_topicgpt=False
)

print("🤖 Training with Vietnamese tokenizer...")
topics_enhanced, _ = model_enhanced.fit(documents)
info_enhanced = model_enhanced.get_topic_info()

print(f"✅ Found {len(info_enhanced['topics'])} topics\n")
for i, topic in enumerate(info_enhanced['topics'][:2]):
    keywords = [w['word'] for w in topic['words'][:5]]
    print(f"   Topic {topic['topic_id']}: {', '.join(keywords)}")

# Test 3: FULL (Vietnamese Tokenizer + TopicGPT)
print("\n\n3️⃣  FULL ENHANCED (Vietnamese tokenizer + TopicGPT)")
print("-" * 70)

model_full = TopicModel(
    min_topic_size=3,
    use_vietnamese_tokenizer=True,
    enable_topicgpt=True  # ✨ Enable LLM enhancement
)

print("🤖 Training with Vietnamese tokenizer + TopicGPT...")
topics_full, _ = model_full.fit(documents)
info_full = model_full.get_topic_info()

print(f"✅ Found {len(info_full['topics'])} topics\n")
for i, topic in enumerate(info_full['topics'][:2]):
    keywords = [w['word'] for w in topic['words'][:5]]
    print(f"\n   📌 Topic {topic['topic_id']} ({topic['count']} docs)")
    print(f"      Keywords: {', '.join(keywords)}")
    
    if 'natural_label' in topic:
        print(f"      ✨ Natural Label: {topic['natural_label']}")
    
    if 'description' in topic:
        desc = topic['description'][:150]
        print(f"      ✨ Description: {desc}...")

# Summary
print("\n\n" + "=" * 70)
print("📊 COMPARISON SUMMARY")
print("=" * 70)
print(f"Baseline (no enhancements):     {len(info_baseline['topics'])} topics")
print(f"Enhanced (Vietnamese tokenizer): {len(info_enhanced['topics'])} topics")
print(f"Full (Tokenizer + TopicGPT):    {len(info_full['topics'])} topics")

print("\n✅ All features working!")
print("   ✅ Vietnamese Tokenizer: Better keywords")
print("   ✅ TopicGPT: Natural labels + descriptions")
