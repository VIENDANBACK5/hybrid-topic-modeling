"""
Script fill analyses trực tiếp vào database (không cần API)
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.model_economic_indicators import EconomicIndicator
from app.services.openai_economic_service import generate_all_analyses
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fill_analyses_for_all_indicators(limit=10):
    """
    Fill analyses cho tất cả indicators trong database
    """
    db = SessionLocal()
    
    try:
        # Lấy indicators
        indicators = db.query(EconomicIndicator).limit(limit).all()
        
        logger.info(f"🔄 Processing {len(indicators)} indicators...")
        
        results = {
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        for indicator in indicators:
            try:
                logger.info(f"\n📊 Processing indicator {indicator.id} - {indicator.period_label}")
                
                # Convert to dict
                indicator_dict = {
                    "id": indicator.id,
                    "period_label": indicator.period_label,
                    "province": indicator.province,
                    "detailed_data": indicator.detailed_data or {},
                    "source_article_url": indicator.source_article_url,
                }
                
                # Generate all analyses
                analyses = generate_all_analyses(indicator_dict)
                
                if analyses:
                    # Update các trường
                    if "grdp_analysis" in analyses:
                        indicator.grdp_analysis = analyses["grdp_analysis"]
                        logger.info(f"  ✅ GRDP analysis: {len(analyses['grdp_analysis'])} chars")
                    
                    if "iip_analysis" in analyses:
                        indicator.iip_analysis = analyses["iip_analysis"]
                        logger.info(f"  ✅ IIP analysis: {len(analyses['iip_analysis'])} chars")
                    
                    if "agricultural_analysis" in analyses:
                        indicator.agricultural_analysis = analyses["agricultural_analysis"]
                        logger.info(f"  ✅ Agricultural analysis: {len(analyses['agricultural_analysis'])} chars")
                    
                    if "retail_services_analysis" in analyses:
                        indicator.retail_services_analysis = analyses["retail_services_analysis"]
                        logger.info(f"  ✅ Retail/Services analysis: {len(analyses['retail_services_analysis'])} chars")
                    
                    if "export_import_analysis" in analyses:
                        indicator.export_import_analysis = analyses["export_import_analysis"]
                        logger.info(f"  ✅ Export/Import analysis: {len(analyses['export_import_analysis'])} chars")
                    
                    if "investment_analysis" in analyses:
                        indicator.investment_analysis = analyses["investment_analysis"]
                        logger.info(f"  ✅ Investment analysis: {len(analyses['investment_analysis'])} chars")
                    
                    if "budget_analysis" in analyses:
                        indicator.budget_analysis = analyses["budget_analysis"]
                        logger.info(f"  ✅ Budget analysis: {len(analyses['budget_analysis'])} chars")
                    
                    if "labor_analysis" in analyses:
                        indicator.labor_analysis = analyses["labor_analysis"]
                        logger.info(f"  ✅ Labor analysis: {len(analyses['labor_analysis'])} chars")
                    
                    results["success"] += 1
                    logger.info(f"  ✅ Generated {len(analyses)} analyses")
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Indicator {indicator.id}: No analyses generated")
                    logger.warning(f"  ⚠️ No analyses generated")
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Indicator {indicator.id}: {str(e)}")
                logger.error(f"  ❌ Error: {e}")
        
        # Commit changes
        db.commit()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ Completed!")
        logger.info(f"Success: {results['success']}/{len(indicators)}")
        logger.info(f"Failed: {results['failed']}/{len(indicators)}")
        
        if results['errors']:
            logger.info(f"\nErrors:")
            for error in results['errors']:
                logger.info(f"  - {error}")
        
        logger.info(f"{'='*60}\n")
        
        return results
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Fatal error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fill analyses for economic indicators")
    parser.add_argument("--limit", type=int, default=10, help="Number of indicators to process")
    
    args = parser.parse_args()
    
    print("="*60)
    print("FILL ANALYSES FOR ECONOMIC INDICATORS")
    print("="*60)
    print(f"Limit: {args.limit} indicators")
    print("="*60)
    
    fill_analyses_for_all_indicators(limit=args.limit)
