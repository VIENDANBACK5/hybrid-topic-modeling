"""
Economic Indicators Service - Xử lý dữ liệu chỉ số kinh tế
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from app.models.model_economic_indicators import EconomicIndicator, EconomicIndicatorGPT
from app.schemas.schema_economic_indicators import (
    EconomicIndicatorCreate,
    EconomicIndicatorUpdate,
    EconomicIndicatorQuery,
    EconomicIndicatorGPTRequest,
    EconomicIndicatorSummary
)

logger = logging.getLogger(__name__)


class EconomicIndicatorService:
    """Service xử lý các chỉ số kinh tế"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_indicator(self, data: EconomicIndicatorCreate) -> EconomicIndicator:
        """Tạo mới một economic indicator"""
        try:
            indicator = EconomicIndicator(**data.model_dump())
            self.db.add(indicator)
            self.db.commit()
            self.db.refresh(indicator)
            logger.info(f" Created economic indicator: {data.period_label}")
            return indicator
        except Exception as e:
            self.db.rollback()
            logger.error(f" Failed to create indicator: {e}")
            raise
    
    def get_indicator(self, indicator_id: int) -> Optional[EconomicIndicator]:
        """Lấy một indicator theo ID"""
        return self.db.query(EconomicIndicator).filter(
            EconomicIndicator.id == indicator_id
        ).first()
    
    def update_indicator(
        self, 
        indicator_id: int, 
        data: EconomicIndicatorUpdate
    ) -> Optional[EconomicIndicator]:
        """Cập nhật một indicator"""
        try:
            indicator = self.get_indicator(indicator_id)
            if not indicator:
                return None
            
            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(indicator, key, value)
            
            self.db.commit()
            self.db.refresh(indicator)
            logger.info(f" Updated economic indicator {indicator_id}")
            return indicator
        except Exception as e:
            self.db.rollback()
            logger.error(f" Failed to update indicator: {e}")
            raise
    
    def delete_indicator(self, indicator_id: int) -> bool:
        """Xóa một indicator"""
        try:
            indicator = self.get_indicator(indicator_id)
            if not indicator:
                return False
            
            self.db.delete(indicator)
            self.db.commit()
            logger.info(f" Deleted economic indicator {indicator_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f" Failed to delete indicator: {e}")
            raise
    
    def query_indicators(self, query: EconomicIndicatorQuery) -> Dict[str, Any]:
        """Query indicators với filters và pagination"""
        try:
            # Build base query
            base_query = self.db.query(EconomicIndicator)
            
            # Apply filters
            if query.period_type:
                base_query = base_query.filter(
                    EconomicIndicator.period_type == query.period_type
                )
            if query.year:
                base_query = base_query.filter(EconomicIndicator.year == query.year)
            if query.month:
                base_query = base_query.filter(EconomicIndicator.month == query.month)
            if query.quarter:
                base_query = base_query.filter(EconomicIndicator.quarter == query.quarter)
            if query.province:
                base_query = base_query.filter(EconomicIndicator.province == query.province)
            if query.region:
                base_query = base_query.filter(EconomicIndicator.region == query.region)
            
            # Count total
            total = base_query.count()
            
            # Apply sorting
            order_func = desc if query.order == "desc" else asc
            if hasattr(EconomicIndicator, query.sort_by):
                base_query = base_query.order_by(
                    order_func(getattr(EconomicIndicator, query.sort_by))
                )
            
            # Apply pagination
            offset = (query.page - 1) * query.page_size
            indicators = base_query.offset(offset).limit(query.page_size).all()
            
            return {
                "total": total,
                "page": query.page,
                "page_size": query.page_size,
                "total_pages": (total + query.page_size - 1) // query.page_size,
                "data": indicators
            }
        except Exception as e:
            logger.error(f" Failed to query indicators: {e}")
            raise
    
    def get_latest_indicator(
        self,
        period_type: Optional[str] = None,
        province: Optional[str] = None
    ) -> Optional[EconomicIndicator]:
        """Lấy indicator mới nhất"""
        query = self.db.query(EconomicIndicator)
        
        if period_type:
            query = query.filter(EconomicIndicator.period_type == period_type)
        if province:
            query = query.filter(EconomicIndicator.province == province)
        
        return query.order_by(desc(EconomicIndicator.period_start)).first()
    
    def get_summary(
        self,
        period_type: str,
        year: int,
        month: Optional[int] = None,
        quarter: Optional[int] = None,
        province: Optional[str] = None
    ) -> EconomicIndicatorSummary:
        """Lấy tóm tắt các chỉ số kinh tế cho một kỳ"""
        try:
            # Build query
            query = self.db.query(EconomicIndicator).filter(
                and_(
                    EconomicIndicator.period_type == period_type,
                    EconomicIndicator.year == year
                )
            )
            
            if month:
                query = query.filter(EconomicIndicator.month == month)
            if quarter:
                query = query.filter(EconomicIndicator.quarter == quarter)
            if province:
                query = query.filter(EconomicIndicator.province == province)
            
            indicator = query.first()
            
            # Build period label
            if month:
                period_label = f"Tháng {month}/{year}"
            elif quarter:
                period_label = f"Quý {quarter}/{year}"
            else:
                period_label = f"Năm {year}"
            
            if not indicator:
                return EconomicIndicatorSummary(
                    period_label=period_label,
                    total_indicators=0,
                    available_indicators=[],
                    missing_indicators=self._get_all_indicator_names(),
                    key_metrics={}
                )
            
            # Check which indicators are available
            available = []
            missing = []
            key_metrics = {}
            
            indicator_fields = [
                ("grdp", "GRDP"),
                ("grdp_growth_rate", "Tăng trưởng GRDP"),
                ("iip", "IIP"),
                ("iip_growth_rate", "Tăng trưởng IIP"),
                ("agricultural_production_index", "Chỉ số sản xuất nông nghiệp"),
                ("retail_services_total", "Tổng bán lẻ & dịch vụ"),
                ("export_value", "Kim ngạch xuất khẩu"),
                ("total_investment", "Tổng đầu tư"),
                ("fdi_disbursed", "FDI giải ngân"),
                ("state_budget_revenue", "Thu ngân sách"),
                ("cpi", "CPI"),
                ("cpi_growth_rate", "Lạm phát"),
            ]
            
            for field_name, display_name in indicator_fields:
                value = getattr(indicator, field_name, None)
                if value is not None:
                    available.append(display_name)
                    key_metrics[field_name] = value
                else:
                    missing.append(display_name)
            
            return EconomicIndicatorSummary(
                period_label=period_label,
                total_indicators=len(available),
                available_indicators=available,
                missing_indicators=missing,
                key_metrics=key_metrics
            )
        except Exception as e:
            logger.error(f" Failed to get summary: {e}")
            raise
    
    def _get_all_indicator_names(self) -> List[str]:
        """Lấy danh sách tất cả các chỉ số"""
        return [
            "GRDP",
            "Tăng trưởng GRDP",
            "IIP",
            "Tăng trưởng IIP",
            "Chỉ số sản xuất nông nghiệp",
            "Tổng bán lẻ & dịch vụ",
            "Kim ngạch xuất khẩu",
            "Tổng đầu tư",
            "FDI giải ngân",
            "Thu ngân sách",
            "CPI",
            "Lạm phát",
        ]
    
    def ask_gpt_for_indicator(
        self,
        request: EconomicIndicatorGPTRequest
    ) -> EconomicIndicatorGPT:
        """
        Hỏi GPT để lấy dữ liệu chỉ số kinh tế khi không có trong DB
        TODO: Implement GPT integration
        """
        try:
            # Build period label
            if request.month:
                period_label = f"Tháng {request.month}/{request.year}"
            elif request.quarter:
                period_label = f"Quý {request.quarter}/{request.year}"
            else:
                period_label = f"Năm {request.year}"
            
            # TODO: Build prompt and call GPT API
            # For now, create a placeholder entry
            gpt_entry = EconomicIndicatorGPT(
                period_type=request.period_type,
                period_label=period_label,
                year=request.year,
                month=request.month,
                quarter=request.quarter,
                province=request.province,
                indicator_name=request.indicator_name,
                indicator_value=None,
                indicator_unit=None,
                gpt_response="TODO: Call GPT API",
                gpt_summary="GPT integration pending",
                prompt_used=f"Get {request.indicator_name} for {period_label}",
                model_used="gpt-4",
                confidence_score=0.0
            )
            
            self.db.add(gpt_entry)
            self.db.commit()
            self.db.refresh(gpt_entry)
            
            logger.info(f" Created GPT entry for {request.indicator_name}")
            return gpt_entry
        except Exception as e:
            self.db.rollback()
            logger.error(f" Failed to create GPT entry: {e}")
            raise
    
    def batch_import_indicators(
        self,
        indicators_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Import hàng loạt indicators từ file hoặc API
        """
        try:
            created = 0
            updated = 0
            errors = []
            
            for data in indicators_data:
                try:
                    # Check if exists
                    existing = self.db.query(EconomicIndicator).filter(
                        and_(
                            EconomicIndicator.period_type == data.get("period_type"),
                            EconomicIndicator.year == data.get("year"),
                            EconomicIndicator.month == data.get("month"),
                            EconomicIndicator.quarter == data.get("quarter"),
                            EconomicIndicator.province == data.get("province")
                        )
                    ).first()
                    
                    if existing:
                        # Update
                        for key, value in data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                        updated += 1
                    else:
                        # Create new
                        indicator = EconomicIndicator(**data)
                        self.db.add(indicator)
                        created += 1
                except Exception as e:
                    errors.append(f"Row error: {str(e)}")
            
            self.db.commit()
            
            return {
                "created": created,
                "updated": updated,
                "total": len(indicators_data),
                "errors": errors
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f" Failed to batch import: {e}")
            raise
