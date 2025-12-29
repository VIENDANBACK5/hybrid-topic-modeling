#!/usr/bin/env python3
"""
Script để fit topic model từ file JSON đã crawl
"""
import json
import requests
import sys

def fit_topics_from_file(file_path: str, n_topics: int = 15, min_topic_size: int = 10, use_openai: bool = False):
    """
    Đọc file JSON và gọi API topic modeling
    """
    print(f"Đang đọc file: {file_path}")
    
    # Đọc file JSON
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract documents
    documents = data.get('documents', [])
    print(f"Tìm thấy {len(documents)} documents")
    
    if not documents:
        print("Không có documents nào trong file!")
        return
    
    # Trích xuất nội dung text từ mỗi document
    texts = []
    for doc in documents:
        content = doc.get('content', '')
        if content and len(content.strip()) > 0:
            texts.append(content)
    
    print(f"Có {len(texts)} documents hợp lệ (có nội dung)")
    
    if len(texts) < 2:
        print("Cần ít nhất 2 documents để chạy topic modeling!")
        return
    
    # Gọi API
    print(f"\nĐang gọi API topic modeling...")
    print(f"- Số topics: {n_topics}")
    print(f"- Min topic size: {min_topic_size}")
    print(f"- Use OpenAI: {use_openai}")
    
    payload = {
        "documents": texts,
        "min_topic_size": min_topic_size,
        "save_model": True,
        "model_name": "vietnamese_phrases_final",
        "use_openai": use_openai
    }
    
    try:
        response = requests.post(
            "http://localhost:7777/api/topics/fit",
            json=payload,
            timeout=600  # 10 phút timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Topic modeling hoàn tất!")
            print(f"Số topics: {result.get('n_topics', 'N/A')}")
            print(f"Model đã lưu: {result.get('model_saved', False)}")
            
            # Hiển thị một số topics
            topics = result.get('topics', [])
            print(f"\nTop 5 topics (từ {len(topics)} topics):")
            for topic in topics[:5]:
                print(f"\nTopic {topic['topic_id']}: {topic['name']}")
                print(f"  Size: {topic['count']} documents")
                if topic.get('keywords'):
                    print(f"  Keywords: {', '.join([kw[0] for kw in topic['keywords'][:5]])}")
            
            return result
        else:
            print(f"\n❌ Lỗi API: {response.status_code}")
            print(response.text)
            return None
            
    except requests.exceptions.Timeout:
        print("\n⏱️ Request timeout! Topic modeling có thể mất nhiều thời gian với dataset lớn.")
        return None
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fit_topics_from_file.py <json_file_path> [n_topics] [min_topic_size] [use_openai]")
        print("Example: python fit_topics_from_file.py data/processed/baohungyen.vn_20251119_112828.json 15 10 false")
        sys.exit(1)
    
    file_path = sys.argv[1]
    n_topics = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    min_topic_size = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    use_openai = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else False
    
    fit_topics_from_file(file_path, n_topics, min_topic_size, use_openai)
