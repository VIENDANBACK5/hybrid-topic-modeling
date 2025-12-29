#!/bin/bash
# Script cài đặt Vietnamese NLP dependencies

echo "🇻🇳 Cài đặt Vietnamese NLP Tokenizer..."
echo ""

# Cài đặt underthesea
echo "📦 Cài đặt underthesea..."
pip install underthesea>=1.3.0

# Kiểm tra cài đặt
echo ""
echo "✅ Kiểm tra cài đặt..."
python -c "from underthesea import word_tokenize; print('✅ underthesea đã được cài đặt thành công!')" 2>/dev/null || echo "❌ Lỗi cài đặt underthesea"

# Test tokenizer
echo ""
echo "🧪 Test Vietnamese tokenizer..."
python -c "
from app.services.etl.vietnamese_tokenizer import get_vietnamese_tokenizer
tokenizer = get_vietnamese_tokenizer()
if tokenizer:
    test_text = 'Tôi đang học xử lý ngôn ngữ tự nhiên tiếng Việt'
    result = tokenizer(test_text)
    print(f'✅ Tokenizer hoạt động!')
    print(f'Input: {test_text}')
    print(f'Output: {result[:5]}...')
else:
    print('❌ Tokenizer không khả dụng')
"

echo ""
echo "📝 Lưu ý:"
echo "   - Model cũ đã được train với tokenizer cũ, cần retrain để có kết quả tốt hơn"
echo "   - Các model mới sẽ tự động sử dụng Vietnamese tokenizer"
echo ""
echo "🔄 Để retrain model, gọi API:"
echo "   POST /api/topics/fit với documents mới"


