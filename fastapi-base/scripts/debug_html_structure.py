"""
Script để debug HTML structure của trang web
"""
import requests
from bs4 import BeautifulSoup
import urllib3
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# URL test
url = sys.argv[1] if len(sys.argv) > 1 else 'https://thongkehungyen.nso.gov.vn/tinh-hinh-kinh-te-xa-hoi/16'

print(f"Fetching: {url}")
print("=" * 80)

try:
    resp = requests.get(url, verify=False, timeout=90)
    soup = BeautifulSoup(resp.content, 'html.parser')
    
    # Lưu HTML ra file
    with open('/tmp/page.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    print(f"✅ Saved HTML to /tmp/page.html ({len(resp.content):,} bytes)")
    
    # Phân tích cấu trúc
    print("\n" + "=" * 80)
    print("ANALYZING STRUCTURE...")
    print("=" * 80)
    
    # Xóa nav/header/footer
    for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
        tag.decompose()
    
    # Tìm các container có thể chứa content
    print("\nLooking for main content containers...")
    for selector in ['article', 'main', 'body']:
        elem = soup.find(selector)
        if elem:
            text = elem.get_text(separator='\n', strip=True)
            print(f"\n{selector}: {len(text):,} chars")
            print(f"  First 500 chars: {text[:500]}")
            
            # Tìm xem "I. TÌNH HÌNH" ở đâu
            if 'I. TÌNH HÌNH' in text:
                idx = text.find('I. TÌNH HÌNH')
                print(f"  Found 'I. TÌNH HÌNH' at position {idx}")
                print(f"  Text before it: ...{text[max(0, idx-200):idx]}")
    
    # Tìm tất cả text nodes
    print("\n" + "=" * 80)
    print("Looking for 'I. TÌNH HÌNH KINH TẾ' or '1. Sản xuất nông nghiệp'...")
    all_text = soup.get_text(separator='\n')
    
    keywords = ['I. TÌNH HÌNH KINH TẾ', 'SẢN XUẤT NÔNG NGHIỆP', '1. Sản xuất nông nghiệp']
    for kw in keywords:
        if kw in all_text:
            idx = all_text.find(kw)
            print(f"\nFound '{kw}' at position {idx}")
            print(f"Text before (200 chars): ...{all_text[max(0, idx-200):idx]}")
            print(f"Text at keyword: {all_text[idx:idx+100]}...")
            break
    
    print("\n✅ Done!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
