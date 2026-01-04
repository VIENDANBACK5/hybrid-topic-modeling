#!/bin/bash

# 🚀 Quick Start Script cho Demo Pipeline MXH
# Script này giúp khởi động demo một cách an toàn

echo "🔍 Kiểm tra các backend đang chạy..."
echo ""
ps aux | grep uvicorn | grep -v grep | head -5
echo ""

echo "📋 Các port backend đang có:"
echo "   - Port 7777"
echo "   - Port 8000" 
echo "   - Port 8091"
echo ""

read -p "🎯 Nhập port backend muốn sử dụng (mặc định 8000): " BACKEND_PORT
BACKEND_PORT=${BACKEND_PORT:-8000}

read -p "🌐 Nhập port cho frontend demo (mặc định 8085): " FRONTEND_PORT
FRONTEND_PORT=${FRONTEND_PORT:-8085}

echo ""
echo "⚙️  Cấu hình:"
echo "   - Backend API: port $BACKEND_PORT"
echo "   - Frontend Demo: port $FRONTEND_PORT"
echo ""

# Kiểm tra backend có đang chạy không
if lsof -i :$BACKEND_PORT > /dev/null 2>&1; then
    echo "✅ Backend đang chạy ở port $BACKEND_PORT"
else
    echo "❌ Không tìm thấy backend ở port $BACKEND_PORT"
    read -p "   Có muốn khởi động backend ở port $BACKEND_PORT? (y/n): " START_BACKEND
    if [ "$START_BACKEND" = "y" ]; then
        echo "   🚀 Khởi động backend..."
        cd /home/ai_team/lab/pipeline_mxh/fastapi-base
        python -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > /tmp/api-$BACKEND_PORT.log 2>&1 &
        sleep 3
        if lsof -i :$BACKEND_PORT > /dev/null 2>&1; then
            echo "   ✅ Backend đã khởi động thành công!"
        else
            echo "   ❌ Lỗi khởi động backend. Xem log: /tmp/api-$BACKEND_PORT.log"
            exit 1
        fi
    else
        echo "   ⚠️  Cần backend chạy để demo hoạt động!"
        exit 1
    fi
fi

# Cập nhật API_PORT trong demo.html
echo ""
echo "📝 Cập nhật cấu hình API_PORT trong demo.html..."
cd /home/ai_team/lab/pipeline_mxh/fastapi-base
sed -i "s/const API_PORT = [0-9]*;/const API_PORT = $BACKEND_PORT;/" demo.html
echo "   ✅ Đã cập nhật API_PORT = $BACKEND_PORT"

# Dọn dẹp frontend port nếu đang chạy
if lsof -i :$FRONTEND_PORT > /dev/null 2>&1; then
    echo ""
    echo "⚠️  Port $FRONTEND_PORT đang được sử dụng"
    read -p "   Có muốn dừng process cũ? (y/n): " KILL_OLD
    if [ "$KILL_OLD" = "y" ]; then
        lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null
        echo "   ✅ Đã dừng process cũ"
    else
        echo "   ❌ Vui lòng chọn port khác!"
        exit 1
    fi
fi

# Khởi động frontend
echo ""
echo "🚀 Khởi động frontend demo..."
cd /home/ai_team/lab/pipeline_mxh/fastapi-base
python3 -m http.server $FRONTEND_PORT > /tmp/demo-$FRONTEND_PORT.log 2>&1 &
sleep 2

if lsof -i :$FRONTEND_PORT > /dev/null 2>&1; then
    echo "   ✅ Frontend đã khởi động thành công!"
else
    echo "   ❌ Lỗi khởi động frontend. Xem log: /tmp/demo-$FRONTEND_PORT.log"
    exit 1
fi

# Lấy IP
IP=$(hostname -I | awk '{print $1}')

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ DEMO ĐÃ SẴN SÀNG!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Truy cập Demo:"
echo "   🌐 Local:   http://localhost:$FRONTEND_PORT/demo.html"
echo "   🌐 Network: http://$IP:$FRONTEND_PORT/demo.html"
echo ""
echo "📍 Backend API:"
echo "   🔌 API:     http://$IP:$BACKEND_PORT/api"
echo "   📚 Swagger: http://$IP:$BACKEND_PORT/docs"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 Chia sẻ link này cho team:"
echo "   http://$IP:$FRONTEND_PORT/demo.html"
echo ""
echo "🛑 Để dừng demo:"
echo "   lsof -ti:$FRONTEND_PORT | xargs kill -9"
echo ""
