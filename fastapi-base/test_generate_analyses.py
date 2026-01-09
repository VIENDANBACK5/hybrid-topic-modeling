"""
Script test để generate analyses cho economic indicators
"""
import requests
import json

# API endpoint
BASE_URL = "http://localhost:7777"

def test_generate_analyses():
    """Test generate analyses endpoint"""
    
    print("🧪 Testing generate analyses endpoint...")
    
    # Test với limit 2 indicators
    url = f"{BASE_URL}/api/v1/economic-indicators/generate-analyses"
    params = {
        "limit": 2,
        "regenerate": False
    }
    
    print(f"\n📡 POST {url}")
    print(f"Params: {params}")
    
    response = requests.post(url, params=params)
    
    print(f"\nStatus: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Success!")
        print(f"Total processed: {data['total_processed']}")
        print(f"Successful: {data['successful']}")
        print(f"Failed: {data['failed']}")
        
        print("\nResults:")
        for result in data['results']:
            print(f"  - ID {result['id']}: {result['status']}")
            if result.get('analyses_count'):
                print(f"    Generated {result['analyses_count']} analyses")
    else:
        print(f"\n❌ Error: {response.text}")


def check_analyses():
    """Check analyses in database"""
    print("\n\n🔍 Checking analyses in database...")
    
    url = f"{BASE_URL}/api/v1/economic-indicators/"
    params = {"limit": 3}
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        indicators = data.get('data', [])
        
        print(f"\nFound {len(indicators)} indicators")
        
        for ind in indicators:
            print(f"\n📊 Indicator {ind['id']} - {ind.get('period_label', '')}")
            print(f"   Province: {ind.get('province', 'N/A')}")
            
            analyses = [
                'grdp_analysis', 'iip_analysis', 'agricultural_analysis',
                'retail_services_analysis', 'export_import_analysis',
                'investment_analysis', 'budget_analysis', 'labor_analysis'
            ]
            
            filled = 0
            for analysis in analyses:
                if ind.get(analysis):
                    filled += 1
                    print(f"   ✅ {analysis}: {len(ind[analysis])} chars")
                else:
                    print(f"   ⚠️  {analysis}: NULL")
            
            print(f"   Summary: {filled}/{len(analyses)} analyses filled")
    else:
        print(f"❌ Error: {response.text}")


if __name__ == "__main__":
    print("=" * 60)
    print("TEST GENERATE ANALYSES FOR ECONOMIC INDICATORS")
    print("=" * 60)
    
    # Test 1: Generate analyses
    test_generate_analyses()
    
    # Test 2: Check results
    check_analyses()
    
    print("\n" + "=" * 60)
    print("✅ Tests completed!")
    print("=" * 60)
