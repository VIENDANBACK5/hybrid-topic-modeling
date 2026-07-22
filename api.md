# Hướng Dẫn Vận Hành & Đặc Tả Chi Tiết API Hệ Thống Pipeline MXH

Tài liệu này chứa hướng dẫn chi tiết cách cài đặt, chạy hệ thống và đặc tả chi tiết toàn bộ các API Backend của hệ thống phân tích tin tức và mạng xã hội bằng AI (Pipeline MXH).

---

## 🚀 Hướng Dẫn Khởi Chạy Toàn Bộ Hệ Thống

Để vận hành hệ thống này dưới máy tính cục bộ hoặc server, làm theo các bước dưới đây:

### 1. Chuẩn Bị Môi Trường & Dependencies
Yêu cầu hệ thống cần cài đặt **Python 3.10** và cơ sở dữ liệu **PostgreSQL**.

```bash
# Di chuyển tới thư mục fastapi-base
cd /home/ai_team/lab/pipeline_mxh/fastapi-base

# Tạo môi trường ảo (nếu chưa có)
python3 -m venv ../.venv
source ../.venv/bin/activate

# Cài đặt toàn bộ thư viện cần thiết
pip install -r requirements.txt
```

### 2. Cấu Hình Các Biến Môi Trường (Environment Variables)
Cấu hình các tham số kết nối Database và API Key cho AI thông qua các biến môi trường hoặc file `.env` nằm trong thư mục `fastapi-base`:

```bash
# Chuỗi kết nối PostgreSQL (Thay đổi thông tin user:password@host:port/dbname cho phù hợp)
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/pipeline_db

# API Key cho LLM (sử dụng OpenRouter cho các model gpt-4o-mini, v.v...)
export OPENAI_API_KEY=sk-or-v1-your-openrouter-key

# Cấu hình Keycloak SSO Authentication (Tùy chọn)
export KEYCLOAK_SERVER_URL=https://sso.example.com/auth/
export KEYCLOAK_REALM=ai-realm
export KEYCLOAK_CLIENT_ID=fastapi-client
export KEYCLOAK_CLIENT_SECRET=your-secret
export KEYCLOAK_VERIFY=True
```

### 3. Chạy Server Backend
```bash
# Chạy ở chế độ Development (Auto reload khi đổi code, chạy ở cổng 8001)
uvicorn app.main:app --reload --port 8001

# Hoặc khởi chạy thông qua Docker-compose ở production
docker-compose up -d
```

Sau khi khởi chạy, bạn có thể truy cập tài liệu API tự động tại:
- **Swagger UI (OpenAPI Docs)**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/re-docs`

---

## 🔄 Trình Tự Gọi Các API (Pipeline Flow)

Để xây dựng một tool tự động gọi các API vận hành quy trình crawl, làm sạch, phân tích và đồng bộ, hãy tuân theo luồng chạy dưới đây:

```
[Bắt đầu]
   │
   ▼
1. POST /api/fetch (Thu thập dữ liệu thô từ FB, TikTok, Newspaper,...)
   │
   ▼
2. GET /api/fetch/status (Kiểm tra trạng thái crawl xong chưa)
   │
   ▼
3. POST /api/process (Làm sạch văn bản, Simhash khử trùng lặp và lưu DB)
   │
   ▼
4. POST /api/llm/extract-{linh-vuc} (Gọi AI trích xuất các chỉ số chi tiết)
   │
   ▼
5. POST /topic-service/train (Huấn luyện phân cụm chủ đề BERTopic)
   │
   ▼
6. POST /superset/sync (Đồng bộ dữ liệu sang Apache Superset Dashboard)
   │
   ▼
[Hoàn thành]
```

### Chi tiết các bước gọi:
1. **Thu thập dữ liệu thô (Fetch)**: Gửi request tới `POST /api/fetch` truyền vào danh sách các nguồn cần quét (`sources: ["facebook", "newspaper"]`). Việc fetch chạy bất đồng bộ (async).
2. **Kiểm tra trạng thái (Status check)**: Gọi liên tục `GET /api/fetch/status` hoặc `GET /api/process/status` để biết các tác vụ nền đã hoàn thành hay chưa.
3. **Lọc và chuẩn hóa (ETL/Process)**: Gửi request tới `POST /api/process` với nguồn tương ứng để thực hiện loại bỏ ký tự rác, tính Simhash để bỏ các bài viết trùng lặp 100% hoặc trùng ngữ nghĩa.
4. **Trích xuất thông minh (LLM Extract)**: Gọi các API `/api/llm/extract-{linh-vuc}` để AI tự động lọc và trích xuất chỉ số (ví dụ: số tai nạn giao thông, số giường bệnh, tỷ lệ tốt nghiệp THPT) lưu vào 27 bảng dữ liệu.
5. **Học máy phân nhóm (BERTopic)**: Gọi `/topic-service/train` định kỳ để nhóm các bài viết thành các xu hướng chủ đề mới nổi.
6. **Đồng bộ visualization**: Trigger `POST /superset/sync` để các biểu đồ trên dashboard Apache Superset cập nhật dữ liệu mới nhất.

---

## 📖 Đặc Tả Chi Tiết Các Endpoint API

Dưới đây là mô tả chi tiết đầu vào và đầu ra của tất cả các API trong hệ thống:


## Fetch API (Crawl thu thập dữ liệu)

### `POST /api/fetch/social/all`
**Tóm tắt**: Fetch All Social Types
**Mô tả**: Fetch tất cả các loại social media và báo chí

Example:
```bash
curl -X POST http://localhost:7777/api/fetch/social/all \
  -H "Content-Type: application/json" \
  -d '{"page_size": 100, "max_pages": 5}'
```
**Request Body (JSON)**:
Schema: `FetchConfig`
```json
{
  - `page_size` (any): Default 500 (max) for fastest fetch. Set lower to reduce memory.
  - `max_pages` (any): None = fetch all pages
  - `sort_by` (string): 
  - `order` (string): 
  - `type_newspaper` (any): Filter by type_newspaper (education, medical, etc.). None = fetch all types
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/fetch/social/{data_type}`
**Tóm tắt**: Fetch Social Data
**Mô tả**: Fetch data từ external API cho social media và báo chí

Supported data_type:
- facebook: Facebook posts
- tiktok: TikTok videos
- threads: Threads posts
- newspaper: News articles

Example:
```bash
curl -X POST http://localhost:7777/api/fetch/social/facebook \
  -H "Content-Type: application/json" \
  -d '{"page_size": 100, "max_pages": 10}'

curl -X POST http://localhost:7777/api/fetch/social/newspaper \
  -H "Content-Type: application/json" \
  -d '{"page_size": 100, "type_newspaper": "economy"}'
```
**Tham số URL/Query**:
- `data_type` (string, path, bắt buộc): 
**Request Body (JSON)**:
Schema: `FetchConfig`
```json
{
  - `page_size` (any): Default 500 (max) for fastest fetch. Set lower to reduce memory.
  - `max_pages` (any): None = fetch all pages
  - `sort_by` (string): 
  - `order` (string): 
  - `type_newspaper` (any): Filter by type_newspaper (education, medical, etc.). None = fetch all types
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `FetchResult`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/fetch/social/status`
**Tóm tắt**: Get Social Fetch Status
**Mô tả**: Xem trạng thái fetch social media & news

Returns: Thống kê về số file và records của mỗi data type
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`

---
### `GET /api/fetch/social/files/{data_type}`
**Tóm tắt**: List Social Files By Type
**Mô tả**: List các file đã fetch theo data_type

Args:
- data_type: facebook | tiktok | threads | newspaper
**Tham số URL/Query**:
- `data_type` (string, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/fetch/document/all`
**Tóm tắt**: Fetch All Document Types
**Mô tả**: Fetch tất cả các loại documents (internal + external)

Example:
```bash
curl -X POST http://localhost:7777/api/fetch/document/all \
  -H "Content-Type: application/json" \
  -d '{"page_size": 100, "max_pages": 5}'
```
**Request Body (JSON)**:
Schema: `DocumentFetchConfig`
```json
{
  - `page_size` (any): Default 500 (max) for fastest fetch.
  - `max_pages` (any): None = fetch all pages
  - `sort_by` (string): 
  - `order` (string): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/fetch/document/{document_type}`
**Tóm tắt**: Fetch Document Data
**Mô tả**: Fetch documents từ external API

Supported document_type:
- internal: Tài liệu nội bộ (PDF, Word, etc.)
- external: Tài liệu bên ngoài

Response format:
- url: Path to document file
- title: Document title
- content: Extracted content/description
- meta_data: {original_filename, file_size, content_type, upload_date, type_newspaper, description}
- document_type: internal | external

Example:
```bash
curl -X POST http://localhost:7777/api/fetch/document/internal \
  -H "Content-Type: application/json" \
  -d '{"page_size": 100, "max_pages": 10}'

curl -X POST http://localhost:7777/api/fetch/document/external \
  -H "Content-Type: application/json" \
  -d '{"page_size": 50}'
```
**Tham số URL/Query**:
- `document_type` (string, path, bắt buộc): 
**Request Body (JSON)**:
Schema: `DocumentFetchConfig`
```json
{
  - `page_size` (any): Default 500 (max) for fastest fetch.
  - `max_pages` (any): None = fetch all pages
  - `sort_by` (string): 
  - `order` (string): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `DocumentFetchResult`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/fetch/document/status`
**Tóm tắt**: Get Document Fetch Status
**Mô tả**: Xem trạng thái fetch documents

Returns: Thống kê về số file và records của mỗi document type
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`

---
### `GET /api/fetch/document/files/{document_type}`
**Tóm tắt**: List Document Files By Type
**Mô tả**: List các file đã fetch theo document_type

Args:
- document_type: internal | external
**Tham số URL/Query**:
- `document_type` (string, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/aqi/fetch-and-fill`
**Tóm tắt**: Fetch And Fill Aqi Data
**Mô tả**: Lấy dữ liệu AQI từ AQICN API và fill vào bảng air_quality_detail

- **province**: Tỉnh/thành phố (mặc định: Hưng Yên)
- **limit_stations**: Giới hạn số trạm đo (None = tất cả)
- **store_mode**: 
    - "historical" (mặc định): Lưu record mới mỗi lần fetch để có nhiều data points theo thời gian (dùng cho Superset)
    - "latest": Chỉ cập nhật record mới nhất của quarter hiện tại

API Source: https://aqicn.org/data-platform/api/

Dữ liệu bao gồm:
- AQI Score (Chỉ số chất lượng không khí)
- PM2.5, PM10, NO2, SO2, CO, O3
- Good days percentage (Tỷ lệ ngày không khí tốt)
- Timestamp (last_updated) để vẽ biểu đồ theo thời gian
**Request Body (JSON)**:
Schema: `AQIFetchRequest`
```json
{
  - `province` (string): Tỉnh/thành phố
  - `limit_stations` (any): Giới hạn số trạm đo
  - `store_mode` (string): latest = cập nhật record hiện tại, historical = lưu record mới với timestamp
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `AQIFetchResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---

## Process API (Làm sạch & Đồng bộ database)

### `POST /api/process/social/all`
**Tóm tắt**: Process All Social Types
**Mô tả**: Xử lý tất cả các social/news data types

Example:
```bash
curl -X POST http://localhost:7777/api/process/social/all
```
**Request Body (JSON)**:
Schema: `ProcessConfig`
```json
{
  - `raw_file` (any): Path to raw file (if not provided, use latest)
  - `skip_duplicates` (boolean): Skip duplicate URLs within file
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/process/social/load-to-db`
**Tóm tắt**: Load Social To Database
**Mô tả**: Load processed social data vào database

Example:
```bash
# Load all latest files
curl -X POST http://localhost:7777/api/process/social/load-to-db

# Load chỉ facebook và newspaper
curl -X POST http://localhost:7777/api/process/social/load-to-db \
  -H "Content-Type: application/json" \
  -d '{"data_types": ["facebook", "newspaper"]}'
```
**Request Body (JSON)**:
Schema: `LoadConfig`
```json
{
  - `processed_file` (any): Path to processed file. If None, will load all latest files
  - `data_types` (any): Data types to load (facebook, tiktok, threads, newspaper). If None, load all
  - `update_existing` (boolean): Update existing records
  - `analyze_sentiment` (boolean): Run sentiment analysis
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/process/social/{data_type}`
**Tóm tắt**: Process Social Data
**Mô tả**: Xử lý raw social/news data

Supported data_type:
- facebook: Facebook posts
- tiktok: TikTok videos  
- threads: Threads posts
- newspaper: News articles

Example:
```bash
curl -X POST http://localhost:7777/api/process/social/facebook

curl -X POST http://localhost:7777/api/process/social/newspaper \
  -H "Content-Type: application/json" \
  -d '{"skip_duplicates": true}'
```
**Tham số URL/Query**:
- `data_type` (string, path, bắt buộc): 
**Request Body (JSON)**:
Schema: `ProcessConfig`
```json
{
  - `raw_file` (any): Path to raw file (if not provided, use latest)
  - `skip_duplicates` (boolean): Skip duplicate URLs within file
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ProcessResult`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/process/social/status`
**Tóm tắt**: Get Social Process Status
**Mô tả**: Xem tổng quan files đã xử lý cho social/news
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`

---
### `GET /api/process/social/files/{data_type}`
**Tóm tắt**: List Social Processed Files
**Mô tả**: List các file đã xử lý theo data_type
**Tham số URL/Query**:
- `data_type` (string, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/process/social/db-stats`
**Tóm tắt**: Get Social Database Stats
**Mô tả**: Xem số lượng data trong các bảng (social data)
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `object`

---
### `POST /api/process/document/all`
**Tóm tắt**: Process All Document Types
**Mô tả**: Xử lý tất cả các document types (internal + external)

Example:
```bash
curl -X POST http://localhost:7777/api/process/document/all
```
**Request Body (JSON)**:
Schema: `DocumentProcessConfig`
```json
{
  - `raw_file` (any): Path to raw file (if not provided, use latest)
  - `skip_duplicates` (boolean): Skip duplicate URLs within file
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/process/document/load-to-db`
**Tóm tắt**: Load Documents To Database
**Mô tả**: Load processed documents vào important_posts table

Example:
```bash
# Load all latest files
curl -X POST http://localhost:7777/api/process/document/load-to-db

# Load chỉ internal
curl -X POST http://localhost:7777/api/process/document/load-to-db \
  -H "Content-Type: application/json" \
  -d '{"document_types": ["internal"]}'
```
**Request Body (JSON)**:
Schema: `DocumentLoadConfig`
```json
{
  - `processed_file` (any): Path to processed file. If None, will load all latest files
  - `document_types` (any): Document types to load (internal, external). If None, load all
  - `update_existing` (boolean): Update existing records
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/process/document/{document_type}`
**Tóm tắt**: Process Document Data
**Mô tả**: Xử lý raw document data

Supported document_type:
- internal: Tài liệu nội bộ (PDF, Word, etc.)
- external: Tài liệu bên ngoài

Example:
```bash
curl -X POST http://localhost:7777/api/process/document/internal

curl -X POST http://localhost:7777/api/process/document/external \
  -H "Content-Type: application/json" \
  -d '{"skip_duplicates": true}'
```
**Tham số URL/Query**:
- `document_type` (string, path, bắt buộc): 
**Request Body (JSON)**:
Schema: `DocumentProcessConfig`
```json
{
  - `raw_file` (any): Path to raw file (if not provided, use latest)
  - `skip_duplicates` (boolean): Skip duplicate URLs within file
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `DocumentProcessResult`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/process/document/status`
**Tóm tắt**: Get Document Process Status
**Mô tả**: Xem tổng quan files đã xử lý cho documents
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`

---
### `GET /api/process/document/files/{document_type}`
**Tóm tắt**: List Document Processed Files
**Mô tả**: List các file đã xử lý theo document_type
**Tham số URL/Query**:
- `document_type` (string, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/process/document/db-stats`
**Tóm tắt**: Get Document Database Stats
**Mô tả**: Xem số lượng documents trong important_posts
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `object`

---

## Economic & Social Indicator Detail APIs (Các chi tiết chỉ số kinh tế - xã hội)

### `POST /api/v1/economic-indicators/`
**Tóm tắt**: Create Indicator
**Mô tả**: Tạo mới một chỉ số kinh tế

**Ví dụ:**
```json
{
  "period_type": "monthly",
  "period_start": "2025-01-01",
  "period_end": "2025-01-31",
  "period_label": "Tháng 1/2025",
  "year": 2025,
  "month": 1,
  "province": "Hà Nội",
  "grdp_growth_rate": 6.5,
  "iip_growth_rate": 8.2,
  "cpi_growth_rate": 3.1,
  "export_value": 1500.5,
  "fdi_disbursed": 1200.0,
  "state_budget_revenue": 45000.0,
  "data_source": "GSO"
}
```
**Request Body (JSON)**:
Schema: `EconomicIndicatorCreate`
```json
{
  - `period_type` (string): Loại kỳ: monthly, quarterly, yearly
  - `period_start` (string): Ngày bắt đầu kỳ
  - `period_end` (string): Ngày kết thúc kỳ
  - `period_label` (any): Nhãn kỳ: Tháng 12/2025
  - `year` (any): Năm
  - `month` (any): Tháng (1-12)
  - `quarter` (any): Quý (1-4)
  - `province` (any): Tỉnh/thành phố
  - `region` (any): Miền: Bắc, Trung, Nam
  - `detailed_data` (any): Dữ liệu chi tiết
  - `data_source` (any): Nguồn dữ liệu
  - `source_url` (any): URL nguồn
  - `source_article_id` (any): ID bài viết nguồn từ bảng articles
  - `source_article_url` (any): URL bài viết nguồn
  - `source_article_domain` (any): Domain bài viết nguồn
  - `notes` (any): Ghi chú
  - `grdp_analysis` (any): Nhận xét về GRDP
  - `iip_analysis` (any): Nhận xét về IIP
  - `agricultural_analysis` (any): Nhận xét về nông nghiệp
  - `retail_services_analysis` (any): Nhận xét về bán lẻ & dịch vụ
  - `export_import_analysis` (any): Nhận xét về xuất nhập khẩu
  - `investment_analysis` (any): Nhận xét về đầu tư
  - `budget_analysis` (any): Nhận xét về ngân sách
  - `labor_analysis` (any): Nhận xét về lao động
  - `summary` (any): Tóm tắt tổng quan về tình hình kinh tế kỳ này
  - `is_verified` (any): Đã xác minh: 0=No, 1=Yes
  - `is_estimated` (any): Ước tính: 0=No, 1=Yes
}
```
**Phản hồi (Responses)**:
- `201`: Successful Response
  Schema: `EconomicIndicatorResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/economic-indicators/`
**Tóm tắt**: Query Indicators
**Mô tả**: Query các chỉ số kinh tế với filters và pagination

**Filters:**
- `period_type`: monthly, quarterly, yearly
- `year`: Năm
- `month`: Tháng (1-12)
- `quarter`: Quý (1-4)
- `province`: Tỉnh/thành phố
- `region`: Miền (Bắc, Trung, Nam)

**Pagination:**
- `page`: Trang hiện tại
- `page_size`: Số items mỗi trang

**Sorting:**
- `sort_by`: Trường để sort (period_start, grdp_growth_rate, cpi_growth_rate, etc.)
- `order`: asc hoặc desc
**Tham số URL/Query**:
- `period_type` (string, query, tùy chọn): Loại kỳ: monthly, quarterly, yearly
- `year` (string, query, tùy chọn): Năm
- `month` (string, query, tùy chọn): Tháng (1-12)
- `quarter` (string, query, tùy chọn): Quý (1-4)
- `province` (string, query, tùy chọn): Tỉnh/thành phố
- `region` (string, query, tùy chọn): Miền
- `page` (integer, query, tùy chọn): Trang
- `page_size` (integer, query, tùy chọn): Số items mỗi trang
- `sort_by` (string, query, tùy chọn): Sắp xếp theo trường
- `order` (string, query, tùy chọn): Thứ tự: asc, desc
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `object`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/economic-indicators/{indicator_id}`
**Tóm tắt**: Get Indicator
**Mô tả**: Lấy thông tin một chỉ số kinh tế theo ID
**Tham số URL/Query**:
- `indicator_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `EconomicIndicatorResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `PUT /api/v1/economic-indicators/{indicator_id}`
**Tóm tắt**: Update Indicator
**Mô tả**: Cập nhật một chỉ số kinh tế
**Tham số URL/Query**:
- `indicator_id` (integer, path, bắt buộc): 
**Request Body (JSON)**:
Schema: `EconomicIndicatorUpdate`
```json
{
  - `period_type` (any): 
  - `period_start` (any): 
  - `period_end` (any): 
  - `period_label` (any): 
  - `year` (any): 
  - `month` (any): 
  - `quarter` (any): 
  - `province` (any): 
  - `region` (any): 
  - `detailed_data` (any): 
  - `data_source` (any): 
  - `source_url` (any): 
  - `source_article_id` (any): 
  - `source_article_url` (any): 
  - `source_article_domain` (any): 
  - `notes` (any): 
  - `grdp_analysis` (any): 
  - `iip_analysis` (any): 
  - `agricultural_analysis` (any): 
  - `retail_services_analysis` (any): 
  - `export_import_analysis` (any): 
  - `investment_analysis` (any): 
  - `budget_analysis` (any): 
  - `labor_analysis` (any): 
  - `summary` (any): 
  - `is_verified` (any): 
  - `is_estimated` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `EconomicIndicatorResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/v1/economic-indicators/{indicator_id}`
**Tóm tắt**: Delete Indicator
**Mô tả**: Xóa một chỉ số kinh tế
**Tham số URL/Query**:
- `indicator_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/economic-indicators/latest/indicator`
**Tóm tắt**: Get Latest Indicator
**Mô tả**: Lấy chỉ số kinh tế mới nhất
**Tham số URL/Query**:
- `period_type` (string, query, tùy chọn): Loại kỳ
- `province` (string, query, tùy chọn): Tỉnh/thành phố
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `EconomicIndicatorResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/economic-indicators/summary/period`
**Tóm tắt**: Get Period Summary
**Mô tả**: Lấy tóm tắt các chỉ số kinh tế cho một kỳ cụ thể

**Ví dụ:**
- Tháng: `?period_type=monthly&year=2025&month=1`
- Quý: `?period_type=quarterly&year=2025&quarter=1`
- Năm: `?period_type=yearly&year=2025`
- Theo tỉnh: `?period_type=monthly&year=2025&month=1&province=Hà Nội`

**Trả về:**
- Số lượng chỉ số có sẵn
- Danh sách chỉ số có sẵn và còn thiếu
- Các chỉ số chính (key metrics)
**Tham số URL/Query**:
- `period_type` (string, query, bắt buộc): Loại kỳ: monthly, quarterly, yearly
- `year` (integer, query, bắt buộc): Năm
- `month` (string, query, tùy chọn): Tháng (1-12)
- `quarter` (string, query, tùy chọn): Quý (1-4)
- `province` (string, query, tùy chọn): Tỉnh/thành phố
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `EconomicIndicatorSummary`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/v1/economic-indicators/gpt/ask`
**Tóm tắt**: Ask Gpt For Indicator
**Mô tả**: Hỏi GPT để lấy dữ liệu chỉ số kinh tế khi không có trong DB

**Ví dụ:**
```json
{
  "indicator_name": "grdp_growth_rate",
  "period_type": "monthly",
  "year": 2025,
  "month": 1,
  "province": "Hà Nội",
  "additional_context": "Latest economic growth data"
}
```

**Note:** Hiện tại chưa tích hợp GPT API thực tế, trả về placeholder data
**Request Body (JSON)**:
Schema: `EconomicIndicatorGPTRequest`
```json
{
  - `indicator_name` (string): Tên chỉ số: grdp, iip, cpi, etc.
  - `period_type` (string): Loại kỳ: monthly, quarterly, yearly
  - `year` (integer): Năm
  - `month` (any): Tháng (1-12)
  - `quarter` (any): Quý (1-4)
  - `province` (any): Tỉnh/thành phố
  - `additional_context` (any): Thông tin thêm cho GPT
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `EconomicIndicatorGPTResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/v1/economic-indicators/batch/import`
**Tóm tắt**: Batch Import Indicators
**Mô tả**: Import hàng loạt chỉ số kinh tế từ file hoặc API

**Ví dụ:**
```json
[
  {
    "period_type": "monthly",
    "period_start": "2025-01-01",
    "period_end": "2025-01-31",
    "year": 2025,
    "month": 1,
    "grdp_growth_rate": 6.5,
    "iip_growth_rate": 8.2
  },
  ...
]
```

**Trả về:**
- Số lượng records được tạo mới
- Số lượng records được cập nhật
- Danh sách lỗi (nếu có)
**Request Body (JSON)**:
```json
{
  "items": {
    "additionalProperties": true,
    "type": "object"
  },
  "type": "array",
  "title": "Indicators"
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/v1/economic-indicators/{indicator_id}/fill-missing`
**Tóm tắt**: Fill Missing Data
**Mô tả**: Dùng OpenAI để fill các trường NULL trong indicator

**Chức năng:**
- Kiểm tra các trường quan trọng bị NULL
- Gọi OpenAI để tìm kiếm dữ liệu
- Cập nhật vào database

**Ví dụ:**
```
POST /api/v1/economic-indicators/5/fill-missing
```
**Tham số URL/Query**:
- `indicator_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/v1/economic-indicators/batch/fill-missing`
**Tóm tắt**: Batch Fill Missing Data
**Mô tả**: Fill missing data hàng loạt cho nhiều indicators

**Chức năng:**
- Tìm các indicators có trường NULL
- Dùng OpenAI fill từng indicator
- Trả về kết quả tổng hợp

**Ví dụ:**
```
POST /api/v1/economic-indicators/batch/fill-missing?year=2025&limit=5
```
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): Chỉ fill cho năm cụ thể
- `month` (string, query, tùy chọn): Chỉ fill cho tháng cụ thể
- `limit` (integer, query, tùy chọn): Số lượng records tối đa
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/v1/economic-indicators/generate-summaries`
**Tóm tắt**: Generate Summaries For Indicators
**Mô tả**: Tự động tạo summary cho economic indicators bằng OpenAI

**Tham số:**
- `indicator_ids`: List các ID cụ thể cần gen summary. Nếu None = gen cho tất cả
- `regenerate`: True = gen lại cả những record đã có summary. False = chỉ gen cho NULL
- `limit`: Số lượng records tối đa xử lý

**Ví dụ:**
```
POST /api/v1/economic-indicators/generate-summaries?limit=5
POST /api/v1/economic-indicators/generate-summaries?regenerate=true&limit=10

Body (optional):
{
  "indicator_ids": [1, 2, 3]
}
```
**Tham số URL/Query**:
- `regenerate` (boolean, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): Số lượng records tối đa
**Request Body (JSON)**:
```json
{
  "anyOf": [
    {
      "type": "array",
      "items": {
        "type": "integer"
      }
    },
    {
      "type": "null"
    }
  ],
  "title": "Indicator Ids"
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `object`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/v1/economic-indicators/generate-analyses`
**Tóm tắt**: Generate Analyses For Indicators
**Mô tả**: Tự động tạo phân tích chi tiết cho từng nhóm chỉ số bằng OpenAI

**Tham số:**
- `indicator_ids`: List các ID cụ thể. Nếu None = gen cho tất cả
- `regenerate`: True = gen lại cả những record đã có. False = chỉ gen cho NULL
- `limit`: Số lượng records tối đa xử lý

**Ví dụ:**
```
POST /api/v1/economic-indicators/generate-analyses?limit=5
POST /api/v1/economic-indicators/generate-analyses?regenerate=true

Body (optional):
{"indicator_ids": [1, 2, 3]}
```
**Tham số URL/Query**:
- `regenerate` (boolean, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): Số lượng records tối đa
**Request Body (JSON)**:
```json
{
  "anyOf": [
    {
      "type": "array",
      "items": {
        "type": "integer"
      }
    },
    {
      "type": "null"
    }
  ],
  "title": "Indicator Ids"
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `object`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/grdp`
**Tóm tắt**: List Grdp
**Mô tả**: List GRDP data with filters
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `quarter` (string, query, tùy chọn): 
- `period_type` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `GRDPDetailListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/grdp`
**Tóm tắt**: Create Or Update Grdp
**Mô tả**: Create or update GRDP data (upsert by year+quarter)
**Request Body (JSON)**:
Schema: `GRDPDetailCreate`
```json
{
  - `province` (string): 
  - `period_type` (string): 
  - `year` (integer): 
  - `quarter` (any): 
  - `actual_value` (any): 
  - `forecast_value` (any): 
  - `change_yoy` (any): 
  - `change_qoq` (any): 
  - `change_prev_period` (any): 
  - `data_status` (string): 
  - `data_source` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `GRDPDetailResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/grdp/{id}`
**Tóm tắt**: Get Grdp
**Mô tả**: Get GRDP by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `GRDPDetailResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/grdp/{id}`
**Tóm tắt**: Delete Grdp
**Mô tả**: Delete GRDP record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/grdp/extract-from-db`
**Tóm tắt**: Extract Grdp From Database Sources
**Mô tả**: Extract GRDP từ BẢNG DATABASE (articles hoặc important_posts) sử dụng LLM

⚠️ NOTE: Extract TẤT CẢ records (cả internal + external documents)
Document type được giữ nguyên từ source record.

Sources:
- 'articles': Bảng articles (external news/content)
- 'important_posts': Bảng important_posts (gov.vn + external sources)
- 'both': Extract từ cả 2 bảng

Process:
1. Query table(s) based on source param
2. Filter: type_newspaper='economic', year, quarter
3. For each record: LLM extract GRDP
4. Save to grdp_detail (preserving document_type from source)

Returns: Aggregated results from all sources
**Tham số URL/Query**:
- `source` (string, query, tùy chọn): Source table: 'articles' or 'important_posts' or 'both'
- `year` (string, query, tùy chọn): Filter by year
- `quarter` (string, query, tùy chọn): Filter by quarter (1-4)
- `limit` (integer, query, tùy chọn): Max records to process per source
- `force_update` (boolean, query, tùy chọn): Update if exists
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/grdp/crawl-official`
**Tóm tắt**: Crawl All Official Sources
**Mô tả**: Crawl TẤT CẢ nguồn chính thức:
- https://thongkehungyen.nso.gov.vn (Playwright - JS rendered)
- https://hungyen.gov.vn (Requests - static HTML)

ETL Pipeline đầy đủ:
1. Smart fetch theo loại trang
2. Enhanced parsing với tables
3. Multi-layer extraction
4. Validation
5. Auto-fill missing fields từ dữ liệu có sẵn

Returns: Danh sách records đã crawl
**Tham số URL/Query**:
- `use_llm` (boolean, query, tùy chọn): Use LLM for extraction
- `force_update` (boolean, query, tùy chọn): Update existing records
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/digital-economy`
**Tóm tắt**: List Digital Economy
**Mô tả**: List Digital Economy data with filters
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `quarter` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `period_type` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `DigitalEconomyDetailListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/digital-economy`
**Tóm tắt**: Create Or Update Digital Economy
**Mô tả**: Create or update Digital Economy data (upsert by year+quarter+province)
**Request Body (JSON)**:
Schema: `DigitalEconomyDetailCreate`
```json
{
  - `province` (string): 
  - `period_type` (string): 
  - `year` (integer): 
  - `quarter` (any): 
  - `month` (any): 
  - `actual_value` (any): 
  - `forecast_value` (any): 
  - `change_yoy` (any): 
  - `change_qoq` (any): 
  - `change_mom` (any): 
  - `digital_economy_gdp` (any): 
  - `digital_economy_gdp_share` (any): 
  - `ecommerce_revenue` (any): 
  - `ecommerce_users` (any): 
  - `digital_payment_volume` (any): 
  - `digital_companies` (any): 
  - `internet_penetration` (any): 
  - `data_status` (string): 
  - `data_source` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `DigitalEconomyDetailResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/digital-economy/{id}`
**Tóm tắt**: Get Digital Economy
**Mô tả**: Get Digital Economy by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `DigitalEconomyDetailResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/digital-economy/{id}`
**Tóm tắt**: Delete Digital Economy
**Mô tả**: Delete Digital Economy record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/fdi`
**Tóm tắt**: List Fdi
**Mô tả**: List FDI data with filters
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `quarter` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `FDIDetailListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/fdi`
**Tóm tắt**: Create Or Update Fdi
**Mô tả**: Create or update FDI data (upsert)
**Request Body (JSON)**:
Schema: `FDIDetailCreate`
```json
{
  - `province` (string): 
  - `period_type` (string): 
  - `year` (integer): 
  - `quarter` (any): 
  - `month` (any): 
  - `actual_value` (any): 
  - `forecast_value` (any): 
  - `change_yoy` (any): 
  - `change_qoq` (any): 
  - `change_mom` (any): 
  - `registered_capital` (any): 
  - `new_projects_capital` (any): 
  - `disbursed_capital` (any): 
  - `disbursement_rate` (any): 
  - `total_projects` (any): 
  - `new_projects` (any): 
  - `manufacturing_fdi` (any): 
  - `japan_fdi` (any): 
  - `korea_fdi` (any): 
  - `fdi_employment` (any): 
  - `data_status` (string): 
  - `data_source` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `FDIDetailResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/fdi/{id}`
**Tóm tắt**: Get Fdi
**Mô tả**: Get FDI by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `FDIDetailResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/fdi/{id}`
**Tóm tắt**: Delete Fdi
**Mô tả**: Delete FDI record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/digital-transformation`
**Tóm tắt**: List Digital Transformation
**Mô tả**: List Digital Transformation data with filters
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `quarter` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `DigitalTransformationDetailListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/digital-transformation`
**Tóm tắt**: Create Or Update Digital Transformation
**Mô tả**: Create or update Digital Transformation data (upsert)
**Request Body (JSON)**:
Schema: `DigitalTransformationDetailCreate`
```json
{
  - `province` (string): 
  - `period_type` (string): 
  - `year` (integer): 
  - `quarter` (any): 
  - `month` (any): 
  - `actual_value` (any): 
  - `forecast_value` (any): 
  - `change_yoy` (any): 
  - `change_qoq` (any): 
  - `change_mom` (any): 
  - `dx_index` (any): 
  - `dx_readiness_index` (any): 
  - `egov_index` (any): 
  - `online_public_services` (any): 
  - `level3_services` (any): 
  - `level4_services` (any): 
  - `online_service_usage_rate` (any): 
  - `cloud_adoption_rate` (any): 
  - `sme_dx_adoption` (any): 
  - `companies_using_ai` (any): 
  - `companies_using_iot` (any): 
  - `data_status` (string): 
  - `data_source` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `DigitalTransformationDetailResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/digital-transformation/{id}`
**Tóm tắt**: Get Digital Transformation
**Mô tả**: Get Digital Transformation by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `DigitalTransformationDetailResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/digital-transformation/{id}`
**Tóm tắt**: Delete Digital Transformation
**Mô tả**: Delete Digital Transformation record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/pii`
**Tóm tắt**: List Pii
**Mô tả**: List PII (Provincial Industrial Index) data with filters
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `quarter` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `PIIDetailListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/pii`
**Tóm tắt**: Create Or Update Pii
**Mô tả**: Create or update PII data (upsert)
**Request Body (JSON)**:
Schema: `PIIDetailCreate`
```json
{
  - `province` (string): 
  - `period_type` (string): 
  - `year` (integer): 
  - `quarter` (any): 
  - `month` (any): 
  - `actual_value` (any): 
  - `forecast_value` (any): 
  - `change_yoy` (any): 
  - `change_qoq` (any): 
  - `change_mom` (any): 
  - `pii_overall` (any): 
  - `pii_growth_rate` (any): 
  - `industrial_output_value` (any): 
  - `mining_index` (any): 
  - `manufacturing_index` (any): 
  - `electricity_index` (any): 
  - `food_processing_index` (any): 
  - `textile_index` (any): 
  - `electronics_index` (any): 
  - `state_owned_pii` (any): 
  - `private_pii` (any): 
  - `fdi_pii` (any): 
  - `labor_productivity` (any): 
  - `industrial_enterprises` (any): 
  - `industrial_workers` (any): 
  - `data_status` (string): 
  - `data_source` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `PIIDetailResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/pii/{id}`
**Tóm tắt**: Get Pii
**Mô tả**: Get PII by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `PIIDetailResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/pii/{id}`
**Tóm tắt**: Delete Pii
**Mô tả**: Delete PII record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/iip`
**Tóm tắt**: List Iip
**Mô tả**: List IIP data with filters
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `quarter` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `IIPListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/iip`
**Tóm tắt**: Create Or Update Iip
**Mô tả**: Create or update IIP data (upsert)
**Request Body (JSON)**:
Schema: `IIPCreate`
```json
{
  - `province` (any): 
  - `year` (any): 
  - `quarter` (any): 
  - `month` (any): 
  - `iip_index` (any): 
  - `growth_rate` (any): 
  - `mining_index` (any): 
  - `manufacturing_index` (any): 
  - `electricity_index` (any): 
  - `data_status` (any): 
  - `data_source` (any): 
  - `document_type` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `IIPResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/iip/by-id/{id}`
**Tóm tắt**: Get Iip
**Mô tả**: Get IIP by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `IIPResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/iip/by-id/{id}`
**Tóm tắt**: Delete Iip
**Mô tả**: Delete IIP record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/iip/extract-from-db`
**Tóm tắt**: Extract From Database Sources
**Mô tả**: Extract IIP từ database sources sử dụng LLM

Sources:
- 'articles': Bảng articles
- 'important_posts': Bảng important_posts  
- 'both': Extract từ cả 2 bảng
**Tham số URL/Query**:
- `source` (string, query, tùy chọn): Source: 'articles', 'important_posts', or 'both'
- `year` (string, query, tùy chọn): Filter by year
- `quarter` (string, query, tùy chọn): Filter by quarter (1-4)
- `limit` (integer, query, tùy chọn): Max records per source
- `force_update` (boolean, query, tùy chọn): Update if exists
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/iip/crawl-official`
**Tóm tắt**: Crawl Iip From Official
**Mô tả**: Crawl IIP data from official statistical website

Default source: https://thongkehungyen.nso.gov.vn

Note: This is a placeholder implementation. Full crawling logic needs to be
implemented based on the actual website structure.

Returns: List of crawled records with status
**Tham số URL/Query**:
- `url` (string, query, tùy chọn): URL to crawl
- `force_update` (boolean, query, tùy chọn): Update existing records
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/cpi`
**Tóm tắt**: List Cpi
**Mô tả**: List CPI data with filters
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `month` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `CPIListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/cpi`
**Tóm tắt**: Create Or Update Cpi
**Mô tả**: Create or update CPI data (upsert)
**Request Body (JSON)**:
Schema: `CPICreate`
```json
{
  - `province` (any): 
  - `year` (any): 
  - `quarter` (any): 
  - `month` (any): 
  - `cpi_index` (any): 
  - `inflation_rate` (any): 
  - `food_cpi` (any): 
  - `housing_cpi` (any): 
  - `transport_cpi` (any): 
  - `education_cpi` (any): 
  - `healthcare_cpi` (any): 
  - `data_status` (any): 
  - `data_source` (any): 
  - `document_type` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `CPIResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/cpi/by-id/{id}`
**Tóm tắt**: Get Cpi
**Mô tả**: Get CPI by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `CPIResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/cpi/by-id/{id}`
**Tóm tắt**: Delete Cpi
**Mô tả**: Delete CPI record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/cpi/extract-from-db`
**Tóm tắt**: Extract From Database Sources
**Mô tả**: Extract CPI từ database sources sử dụng LLM

Sources:
- 'articles': Bảng articles
- 'important_posts': Bảng important_posts  
- 'both': Extract từ cả 2 bảng
**Tham số URL/Query**:
- `source` (string, query, tùy chọn): Source: 'articles', 'important_posts', or 'both'
- `year` (string, query, tùy chọn): Filter by year
- `quarter` (string, query, tùy chọn): Filter by quarter (1-4)
- `limit` (integer, query, tùy chọn): Max records per source
- `force_update` (boolean, query, tùy chọn): Update if exists
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/cpi/crawl-official`
**Tóm tắt**: Crawl Cpi From Official
**Mô tả**: Crawl CPI data from official statistical website

Default source: https://thongkehungyen.nso.gov.vn

Note: This is a placeholder implementation. Full crawling logic needs to be
implemented based on the actual website structure.

Returns: List of crawled records with status
**Tham số URL/Query**:
- `url` (string, query, tùy chọn): URL to crawl
- `force_update` (boolean, query, tùy chọn): Update existing records
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/highschool-graduation`
**Tóm tắt**: List Highschool Graduation
**Mô tả**: List highschool graduation data
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `HighschoolGraduationListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/highschool-graduation`
**Tóm tắt**: Create Or Update Highschool Graduation
**Mô tả**: Create or update highschool graduation data
**Request Body (JSON)**:
Schema: `HighschoolGraduationCreate`
```json
{
  - `province` (any): 
  - `year` (any): 
  - `quarter` (any): 
  - `month` (any): 
  - `graduation_rate` (any): 
  - `total_candidates` (any): 
  - `passed_candidates` (any): 
  - `average_score` (any): 
  - `math_avg_score` (any): 
  - `literature_avg_score` (any): 
  - `english_avg_score` (any): 
  - `excellent_rate` (any): 
  - `fail_rate` (any): 
  - `data_status` (any): 
  - `data_source` (any): 
  - `document_type` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `HighschoolGraduationResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/highschool-graduation/by-id/{id}`
**Tóm tắt**: Get Highschool Graduation
**Mô tả**: Get highschool graduation by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `HighschoolGraduationResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/highschool-graduation/by-id/{id}`
**Tóm tắt**: Delete Highschool Graduation
**Mô tả**: Delete highschool graduation record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/highschool-graduation/extract-from-db`
**Tóm tắt**: Extract From Database Sources
**Mô tả**: Extract Highschool Graduation từ database sources sử dụng LLM

Sources:
- 'articles': Bảng articles
- 'important_posts': Bảng important_posts  
- 'both': Extract từ cả 2 bảng
**Tham số URL/Query**:
- `source` (string, query, tùy chọn): Source: 'articles', 'important_posts', or 'both'
- `year` (string, query, tùy chọn): Filter by year
- `quarter` (string, query, tùy chọn): Filter by quarter (1-4)
- `limit` (integer, query, tùy chọn): Max records per source
- `force_update` (boolean, query, tùy chọn): Update if exists
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/tvet-employment`
**Tóm tắt**: List Tvet Employment
**Mô tả**: List TVET employment data
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `TVETEmploymentListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/tvet-employment`
**Tóm tắt**: Create Or Update Tvet Employment
**Mô tả**: Create or update TVET employment data
**Request Body (JSON)**:
Schema: `TVETEmploymentCreate`
```json
{
  - `province` (any): 
  - `year` (any): 
  - `quarter` (any): 
  - `month` (any): 
  - `total_graduates` (any): 
  - `employed_graduates` (any): 
  - `employment_rate` (any): 
  - `skilled_employment_rate` (any): 
  - `average_salary` (any): 
  - `certification_rate` (any): 
  - `training_completion_rate` (any): 
  - `data_status` (any): 
  - `data_source` (any): 
  - `document_type` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `TVETEmploymentResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/tvet-employment/by-id/{id}`
**Tóm tắt**: Get Tvet Employment
**Mô tả**: Get TVET employment by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `TVETEmploymentResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/tvet-employment/by-id/{id}`
**Tóm tắt**: Delete Tvet Employment
**Mô tả**: Delete TVET employment record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/tvet-employment/extract-from-db`
**Tóm tắt**: Extract From Database Sources
**Mô tả**: Extract TVET Employment từ database sources sử dụng LLM

Sources:
- 'articles': Bảng articles
- 'important_posts': Bảng important_posts  
- 'both': Extract từ cả 2 bảng
**Tham số URL/Query**:
- `source` (string, query, tùy chọn): Source: 'articles', 'important_posts', or 'both'
- `year` (string, query, tùy chọn): Filter by year
- `quarter` (string, query, tùy chọn): Filter by quarter (1-4)
- `limit` (integer, query, tùy chọn): Max records per source
- `force_update` (boolean, query, tùy chọn): Update if exists
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/cadre-statistics`
**Tóm tắt**: List Cadre Statistics
**Mô tả**: List cadre statistics with filters
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `CadreStatisticsListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/cadre-statistics`
**Tóm tắt**: Create Or Update Cadre Statistics
**Mô tả**: Create or update cadre statistics (upsert)
**Request Body (JSON)**:
Schema: `CadreStatisticsCreate`
```json
{
  - `province` (any): 
  - `year` (any): 
  - `quarter` (any): 
  - `month` (any): 
  - `total_authorized` (any): 
  - `provincial_level` (any): 
  - `commune_level` (any): 
  - `contract_workers` (any): 
  - `data_status` (any): 
  - `data_source` (any): 
  - `document_type` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `CadreStatisticsResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/cadre-statistics/by-id/{id}`
**Tóm tắt**: Get Cadre Statistics
**Mô tả**: Get cadre statistics by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `CadreStatisticsResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/cadre-statistics/by-id/{id}`
**Tóm tắt**: Delete Cadre Statistics
**Mô tả**: Delete cadre statistics record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/cadre-statistics/extract-from-db`
**Tóm tắt**: Extract From Database Sources
**Mô tả**: Extract Cadre Statistics từ database sources sử dụng LLM

Sources:
- 'articles': Bảng articles
- 'important_posts': Bảng important_posts  
- 'both': Extract từ cả 2 bảng
**Tham số URL/Query**:
- `source` (string, query, tùy chọn): Source: 'articles', 'important_posts', or 'both'
- `year` (string, query, tùy chọn): Filter by year
- `quarter` (string, query, tùy chọn): Filter by quarter (1-4)
- `limit` (integer, query, tùy chọn): Max records per source
- `force_update` (boolean, query, tùy chọn): Update if exists
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/health-statistics`
**Tóm tắt**: List Health Statistics
**Mô tả**: List health statistics
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `HealthStatisticsListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/health-statistics`
**Tóm tắt**: Create Or Update Health Statistics
**Mô tả**: Create or update health statistics
**Request Body (JSON)**:
Schema: `HealthStatisticsCreate`
```json
{
  - `province` (any): 
  - `year` (any): 
  - `quarter` (any): 
  - `month` (any): 
  - `hospital_beds` (any): 
  - `doctors_per_10k` (any): 
  - `health_insurance_coverage` (any): 
  - `maternal_mortality_rate` (any): 
  - `infant_mortality_rate` (any): 
  - `vaccination_rate` (any): 
  - `data_status` (any): 
  - `data_source` (any): 
  - `document_type` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `HealthStatisticsResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/health-statistics/by-id/{id}`
**Tóm tắt**: Get Health Statistics
**Mô tả**: Get health statistics by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `HealthStatisticsResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/health-statistics/by-id/{id}`
**Tóm tắt**: Delete Health Statistics
**Mô tả**: Delete health statistics record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/health-statistics/extract-from-db`
**Tóm tắt**: Extract From Database Sources
**Mô tả**: Extract Health Statistics từ database sources sử dụng LLM

Sources:
- 'articles': Bảng articles
- 'important_posts': Bảng important_posts  
- 'both': Extract từ cả 2 bảng
**Tham số URL/Query**:
- `source` (string, query, tùy chọn): Source: 'articles', 'important_posts', or 'both'
- `year` (string, query, tùy chọn): Filter by year
- `quarter` (string, query, tùy chọn): Filter by quarter (1-4)
- `limit` (integer, query, tùy chọn): Max records per source
- `force_update` (boolean, query, tùy chọn): Update if exists
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/culture-lifestyle`
**Tóm tắt**: List Culture Lifestyle
**Mô tả**: List culture & lifestyle statistics
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `CultureLifestyleListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/culture-lifestyle`
**Tóm tắt**: Create Or Update Culture Lifestyle
**Mô tả**: Create or update culture & lifestyle data
**Request Body (JSON)**:
Schema: `CultureLifestyleCreate`
```json
{
  - `province` (any): 
  - `year` (any): 
  - `quarter` (any): 
  - `month` (any): 
  - `cultural_facilities` (any): 
  - `sports_facilities` (any): 
  - `cultural_events` (any): 
  - `sports_events` (any): 
  - `participants` (any): 
  - `data_status` (any): 
  - `data_source` (any): 
  - `document_type` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `CultureLifestyleResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/culture-lifestyle/by-id/{id}`
**Tóm tắt**: Get Culture Lifestyle
**Mô tả**: Get culture & lifestyle by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `CultureLifestyleResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/culture-lifestyle/by-id/{id}`
**Tóm tắt**: Delete Culture Lifestyle
**Mô tả**: Delete culture & lifestyle record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/culture-lifestyle/extract-from-db`
**Tóm tắt**: Extract From Database Sources
**Mô tả**: Extract Culture & Lifestyle từ database sources sử dụng LLM

Sources:
- 'articles': Bảng articles
- 'important_posts': Bảng important_posts  
- 'both': Extract từ cả 2 bảng
**Tham số URL/Query**:
- `source` (string, query, tùy chọn): Source: 'articles', 'important_posts', or 'both'
- `year` (string, query, tùy chọn): Filter by year
- `quarter` (string, query, tùy chọn): Filter by quarter (1-4)
- `limit` (integer, query, tùy chọn): Max records per source
- `force_update` (boolean, query, tùy chọn): Update if exists
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/security`
**Tóm tắt**: List Security
**Mô tả**: List security statistics
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `SecurityListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/security`
**Tóm tắt**: Create Or Update Security
**Mô tả**: Create or update security data
**Request Body (JSON)**:
Schema: `SecurityCreate`
```json
{
  - `province` (any): 
  - `year` (any): 
  - `quarter` (any): 
  - `month` (any): 
  - `crime_cases` (any): 
  - `solved_cases` (any): 
  - `traffic_accidents` (any): 
  - `fire_incidents` (any): 
  - `public_safety_score` (any): 
  - `data_status` (any): 
  - `data_source` (any): 
  - `document_type` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `SecurityResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/security/by-id/{id}`
**Tóm tắt**: Get Security
**Mô tả**: Get security statistics by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `SecurityResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/security/by-id/{id}`
**Tóm tắt**: Delete Security
**Mô tả**: Delete security record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/security/extract-from-db`
**Tóm tắt**: Extract From Database Sources
**Mô tả**: Extract Security statistics từ database sources sử dụng LLM

Sources:
- 'articles': Bảng articles
- 'important_posts': Bảng important_posts  
- 'both': Extract từ cả 2 bảng
**Tham số URL/Query**:
- `source` (string, query, tùy chọn): Source: 'articles', 'important_posts', or 'both'
- `year` (string, query, tùy chọn): Filter by year
- `quarter` (string, query, tùy chọn): Filter by quarter (1-4)
- `limit` (integer, query, tùy chọn): Max records per source
- `force_update` (boolean, query, tùy chọn): Update if exists
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/par-index`
**Tóm tắt**: List Par Index
**Mô tả**: List PAR index data
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `PARIndexListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/par-index`
**Tóm tắt**: Create Or Update Par Index
**Mô tả**: Create or update PAR index data
**Request Body (JSON)**:
Schema: `PARIndexCreate`
```json
{
  - `province` (any): 
  - `year` (any): 
  - `quarter` (any): 
  - `par_index_score` (any): 
  - `ranking` (any): 
  - `improved_procedures` (any): 
  - `digital_services_rate` (any): 
  - `citizen_satisfaction` (any): 
  - `data_status` (any): 
  - `data_source` (any): 
  - `document_type` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `PARIndexResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/par-index/by-id/{id}`
**Tóm tắt**: Get Par Index
**Mô tả**: Get PAR index by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `PARIndexResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/par-index/by-id/{id}`
**Tóm tắt**: Delete Par Index
**Mô tả**: Delete PAR index record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/par-index/extract-from-db`
**Tóm tắt**: Extract From Database Sources
**Mô tả**: Extract PAR Index từ database sources sử dụng LLM

Sources:
- 'articles': Bảng articles
- 'important_posts': Bảng important_posts  
- 'both': Extract từ cả 2 bảng
**Tham số URL/Query**:
- `source` (string, query, tùy chọn): Source: 'articles', 'important_posts', or 'both'
- `year` (string, query, tùy chọn): Filter by year
- `quarter` (string, query, tùy chọn): Filter by quarter (1-4)
- `limit` (integer, query, tùy chọn): Max records per source
- `force_update` (boolean, query, tùy chọn): Update if exists
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/sipas`
**Tóm tắt**: List Sipas
**Mô tả**: List SIPAS data
**Tham số URL/Query**:
- `year` (string, query, tùy chọn): 
- `province` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `SIPASListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/sipas`
**Tóm tắt**: Create Or Update Sipas
**Mô tả**: Create or update SIPAS data
**Request Body (JSON)**:
Schema: `SIPASCreate`
```json
{
  - `province` (any): 
  - `year` (any): 
  - `quarter` (any): 
  - `sipas_score` (any): 
  - `ranking` (any): 
  - `service_quality_score` (any): 
  - `staff_attitude_score` (any): 
  - `procedure_efficiency_score` (any): 
  - `data_status` (any): 
  - `data_source` (any): 
  - `document_type` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `SIPASResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/sipas/by-id/{id}`
**Tóm tắt**: Get Sipas
**Mô tả**: Get SIPAS by ID
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `SIPASResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/sipas/by-id/{id}`
**Tóm tắt**: Delete Sipas
**Mô tả**: Delete SIPAS record
**Tham số URL/Query**:
- `id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/sipas/extract-from-db`
**Tóm tắt**: Extract From Database Sources
**Mô tả**: Extract SIPAS từ database sources sử dụng LLM

Sources:
- 'articles': Bảng articles
- 'important_posts': Bảng important_posts  
- 'both': Extract từ cả 2 bảng
**Tham số URL/Query**:
- `source` (string, query, tùy chọn): Source: 'articles', 'important_posts', or 'both'
- `year` (string, query, tùy chọn): Filter by year
- `quarter` (string, query, tùy chọn): Filter by quarter (1-4)
- `limit` (integer, query, tùy chọn): Max records per source
- `force_update` (boolean, query, tùy chọn): Update if exists
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/social-indicators/fields`
**Tóm tắt**: Get All Fields
**Mô tả**: Lấy danh sách tất cả 9 lĩnh vực và các chỉ số

Mỗi lĩnh vực bao gồm:
- key: Mã lĩnh vực
- name: Tên lĩnh vực
- indicators: Danh sách 3 chỉ số
- categories: Các giá trị category trong articles tương ứng với lĩnh vực này
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `array`

---
### `GET /api/social-indicators/fields/{field_key}`
**Tóm tắt**: Get Field Info
**Mô tả**: Lấy thông tin chi tiết của 1 lĩnh vực
**Tham số URL/Query**:
- `field_key` (string, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `FieldInfo`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/social-indicators/{field_key}/extract`
**Tóm tắt**: Extract Field Data
**Mô tả**: Trích xuất dữ liệu từ articles và fill vào các bảng của lĩnh vực

- **field_key**: Key của lĩnh vực (vd: xay_dung_dang, van_hoa_the_thao, ...)
- **limit**: Số bài viết tối đa để xử lý
- **year_filter**: Lọc theo năm
- **province_filter**: Lọc theo tỉnh/thành
- **use_category_filter**: Nếu True, sẽ lọc theo category của article (nhanh hơn)

SMART EXTRACTION:
- Tự động dùng LLM (nếu có OpenAI API key) + Regex
- LLM hiểu context phức tạp: "giảm 30%" vs "đạt 70%"
- Regex làm backup: đảm bảo không bỏ sót
- Merge kết quả: ưu tiên LLM > Regex

CATEGORY TRONG ARTICLES (8 giá trị chuẩn):
- medical/health → y_te (Y tế & Chăm sóc sức khỏe)
- education → giao_duc (Giáo dục & Đào tạo)
- security/police → an_ninh_trat_tu (An ninh, Trật tự)
- politics → xay_dung_dang (Xây dựng Đảng)
- social/culture → van_hoa_the_thao (Văn hóa, Thể thao)
- environment → moi_truong (Môi trường)
- welfare → an_sinh_xa_hoi (An sinh xã hội)
- administration → hanh_chinh_cong (Hành chính công)
- infrastructure/transport → ha_tang_giao_thong (Hạ tầng Giao thông)

CATEGORY TRONG ARTICLES (8 giá trị chuẩn):
- "medical" → y_te (Y tế & Chăm sóc sức khỏe)
- "education" → giao_duc (Giáo dục & Đào tạo)
- "transportation" → ha_tang_giao_thong (Hạ tầng & Giao thông)
- "environment" → moi_truong (Môi trường & Biến đổi khí hậu)
- "policy" → an_sinh_xa_hoi (An sinh xã hội & Chính sách)
- "security" → an_ninh_trat_tu (An ninh, Trật tự & Quốc phòng)
- "management" → hanh_chinh_cong (Hành chính công & Quản lý Nhà nước)
- "politics" → xay_dung_dang (Xây dựng Đảng & Hệ thống chính trị)
- "social" → van_hoa_the_thao (Văn hóa, Thể thao & Đời sống tinh thần)

CHÚ Ý: 
- Chỉ trích xuất số liệu có trong văn bản gốc (không bịa)
- Nếu không tìm thấy số liệu, để NULL
**Tham số URL/Query**:
- `field_key` (string, path, bắt buộc): 
**Request Body (JSON)**:
Schema: `ExtractionRequest`
```json
{
  - `limit` (integer): Max số bài viết để xử lý
  - `year_filter` (any): Lọc theo năm
  - `province_filter` (any): Lọc theo tỉnh/thành
  - `use_category_filter` (boolean): Lọc theo category của article (nhanh hơn nếu category đã được set)
  - `use_llm` (boolean): Sử dụng LLM (GPT) để extract indicators
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ExtractionResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/social-indicators/{field_key}/summary`
**Tóm tắt**: Get Field Summary
**Mô tả**: Lấy tổng quan dữ liệu của 1 lĩnh vực

Bao gồm:
- Số lượng records trong mỗi bảng chỉ số
- Năm/quý mới nhất có dữ liệu
**Tham số URL/Query**:
- `field_key` (string, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `app__api__api_social_indicators__FieldSummaryResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/social-indicators/{field_key}/{indicator_key}/data`
**Tóm tắt**: Get Indicator Data
**Mô tả**: Lấy dữ liệu của 1 chỉ số cụ thể
**Tham số URL/Query**:
- `field_key` (string, path, bắt buộc): 
- `indicator_key` (string, path, bắt buộc): 
- `province` (string, query, tùy chọn): Lọc theo tỉnh/thành
- `year` (string, query, tùy chọn): Lọc theo năm
- `limit` (integer, query, tùy chọn): Số records tối đa
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `IndicatorDataResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/social-indicators/extract-all`
**Tóm tắt**: Extract All Fields
**Mô tả**: Trích xuất dữ liệu cho TẤT CẢ 9 lĩnh vực

Chạy tuần tự qua từng lĩnh vực và tổng hợp kết quả
**Request Body (JSON)**:
Schema: `ExtractionRequest`
```json
{
  - `limit` (integer): Max số bài viết để xử lý
  - `year_filter` (any): Lọc theo năm
  - `province_filter` (any): Lọc theo tỉnh/thành
  - `use_category_filter` (boolean): Lọc theo category của article (nhanh hơn nếu category đã được set)
  - `use_llm` (boolean): Sử dụng LLM (GPT) để extract indicators
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/social-indicators/summary-all`
**Tóm tắt**: Get All Fields Summary
**Mô tả**: Lấy tổng quan dữ liệu của TẤT CẢ 9 lĩnh vực
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`

---
### `POST /api/social-indicators/xay-dung-dang/extract`
**Tóm tắt**: Extract Xay Dung Dang
**Mô tả**: Lĩnh vực 1: Xây dựng Đảng & Hệ thống chính trị
**Request Body (JSON)**:
Schema: `ExtractionRequest`
```json
{
  - `limit` (integer): Max số bài viết để xử lý
  - `year_filter` (any): Lọc theo năm
  - `province_filter` (any): Lọc theo tỉnh/thành
  - `use_category_filter` (boolean): Lọc theo category của article (nhanh hơn nếu category đã được set)
  - `use_llm` (boolean): Sử dụng LLM (GPT) để extract indicators
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ExtractionResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/social-indicators/van-hoa-the-thao/extract`
**Tóm tắt**: Extract Van Hoa The Thao
**Mô tả**: Lĩnh vực 2: Văn hóa, Thể thao & Đời sống tinh thần
**Request Body (JSON)**:
Schema: `ExtractionRequest`
```json
{
  - `limit` (integer): Max số bài viết để xử lý
  - `year_filter` (any): Lọc theo năm
  - `province_filter` (any): Lọc theo tỉnh/thành
  - `use_category_filter` (boolean): Lọc theo category của article (nhanh hơn nếu category đã được set)
  - `use_llm` (boolean): Sử dụng LLM (GPT) để extract indicators
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ExtractionResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/social-indicators/moi-truong/extract`
**Tóm tắt**: Extract Moi Truong
**Mô tả**: Lĩnh vực 3: Môi trường & Biến đổi khí hậu
**Request Body (JSON)**:
Schema: `ExtractionRequest`
```json
{
  - `limit` (integer): Max số bài viết để xử lý
  - `year_filter` (any): Lọc theo năm
  - `province_filter` (any): Lọc theo tỉnh/thành
  - `use_category_filter` (boolean): Lọc theo category của article (nhanh hơn nếu category đã được set)
  - `use_llm` (boolean): Sử dụng LLM (GPT) để extract indicators
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ExtractionResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/social-indicators/an-sinh-xa-hoi/extract`
**Tóm tắt**: Extract An Sinh Xa Hoi
**Mô tả**: Lĩnh vực 4: An sinh xã hội & Chính sách
**Request Body (JSON)**:
Schema: `ExtractionRequest`
```json
{
  - `limit` (integer): Max số bài viết để xử lý
  - `year_filter` (any): Lọc theo năm
  - `province_filter` (any): Lọc theo tỉnh/thành
  - `use_category_filter` (boolean): Lọc theo category của article (nhanh hơn nếu category đã được set)
  - `use_llm` (boolean): Sử dụng LLM (GPT) để extract indicators
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ExtractionResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/social-indicators/an-ninh-trat-tu/extract`
**Tóm tắt**: Extract An Ninh Trat Tu
**Mô tả**: Lĩnh vực 5: An ninh, Trật tự & Quốc phòng
**Request Body (JSON)**:
Schema: `ExtractionRequest`
```json
{
  - `limit` (integer): Max số bài viết để xử lý
  - `year_filter` (any): Lọc theo năm
  - `province_filter` (any): Lọc theo tỉnh/thành
  - `use_category_filter` (boolean): Lọc theo category của article (nhanh hơn nếu category đã được set)
  - `use_llm` (boolean): Sử dụng LLM (GPT) để extract indicators
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ExtractionResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/social-indicators/hanh-chinh-cong/extract`
**Tóm tắt**: Extract Hanh Chinh Cong
**Mô tả**: Lĩnh vực 6: Hành chính công & Quản lý Nhà nước
**Request Body (JSON)**:
Schema: `ExtractionRequest`
```json
{
  - `limit` (integer): Max số bài viết để xử lý
  - `year_filter` (any): Lọc theo năm
  - `province_filter` (any): Lọc theo tỉnh/thành
  - `use_category_filter` (boolean): Lọc theo category của article (nhanh hơn nếu category đã được set)
  - `use_llm` (boolean): Sử dụng LLM (GPT) để extract indicators
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ExtractionResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/social-indicators/y-te/extract`
**Tóm tắt**: Extract Y Te
**Mô tả**: Lĩnh vực 7: Y tế & Chăm sóc sức khỏe
**Request Body (JSON)**:
Schema: `ExtractionRequest`
```json
{
  - `limit` (integer): Max số bài viết để xử lý
  - `year_filter` (any): Lọc theo năm
  - `province_filter` (any): Lọc theo tỉnh/thành
  - `use_category_filter` (boolean): Lọc theo category của article (nhanh hơn nếu category đã được set)
  - `use_llm` (boolean): Sử dụng LLM (GPT) để extract indicators
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ExtractionResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/social-indicators/giao-duc/extract`
**Tóm tắt**: Extract Giao Duc
**Mô tả**: Lĩnh vực 8: Giáo dục & Đào tạo
**Request Body (JSON)**:
Schema: `ExtractionRequest`
```json
{
  - `limit` (integer): Max số bài viết để xử lý
  - `year_filter` (any): Lọc theo năm
  - `province_filter` (any): Lọc theo tỉnh/thành
  - `use_category_filter` (boolean): Lọc theo category của article (nhanh hơn nếu category đã được set)
  - `use_llm` (boolean): Sử dụng LLM (GPT) để extract indicators
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ExtractionResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/social-indicators/ha-tang-giao-thong/extract`
**Tóm tắt**: Extract Ha Tang Giao Thong
**Mô tả**: Lĩnh vực 9: Hạ tầng & Giao thông
**Request Body (JSON)**:
Schema: `ExtractionRequest`
```json
{
  - `limit` (integer): Max số bài viết để xử lý
  - `year_filter` (any): Lọc theo năm
  - `province_filter` (any): Lọc theo tỉnh/thành
  - `use_category_filter` (boolean): Lọc theo category của article (nhanh hơn nếu category đã được set)
  - `use_llm` (boolean): Sử dụng LLM (GPT) để extract indicators
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ExtractionResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/social-indicators/category-mapping`
**Tóm tắt**: Get Category Mapping
**Mô tả**: Lấy mapping giữa article.category và field_key

Dùng để hiểu article có category nào sẽ được xử lý bởi endpoint nào
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`

---
### `GET /api/social-indicators/articles/category-stats`
**Tóm tắt**: Get Article Category Stats
**Mô tả**: Thống kê số lượng articles theo category

Để biết có bao nhiêu articles đã được gán category
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`

---
### `GET /api/aqi/latest/{province}`
**Tóm tắt**: Get Latest Aqi
**Mô tả**: Lấy dữ liệu AQI mới nhất của tỉnh
**Tham số URL/Query**:
- `province` (string, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/aqi/stats`
**Tóm tắt**: Get Aqi Stats
**Mô tả**: Thống kê tổng quan dữ liệu AQI trong DB
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`

---
### `POST /api/important-posts/`
**Tóm tắt**: Create Important Post
**Mô tả**: Tạo mới một bài viết quan trọng

Args:
    post: Dữ liệu bài viết
    
Returns:
    ImportantPostResponse: Bài viết đã tạo
**Request Body (JSON)**:
Schema: `ImportantPostCreate`
```json
{
  - `url` (string): URL bài viết gốc
  - `title` (string): Tiêu đề bài viết
  - `content` (string): Nội dung đầy đủ bài viết
  - `data_type` (string): Loại dữ liệu
  - `type_newspaper` (any): Phân loại báo: medical, economic, social, etc.
  - `original_id` (any): ID từ hệ thống nguồn
  - `original_created_at` (any): Thời gian tạo từ hệ thống nguồn
  - `original_updated_at` (any): Thời gian cập nhật từ hệ thống nguồn
  - `meta_data` (any): Metadata từ nguồn
  - `author` (any): Tác giả
  - `published_date` (any): Ngày xuất bản
  - `dvhc` (any): Đơn vị hành chính
  - `statistics` (any): Danh sách số liệu thống kê
  - `organizations` (any): Danh sách tổ chức
  - `is_featured` (any): Đánh dấu nổi bật (1=featured, 0=normal)
  - `importance_score` (any): Điểm quan trọng (0-10)
  - `tags` (any): Tags phân loại
  - `categories` (any): Danh mục liên quan
}
```
**Phản hồi (Responses)**:
- `201`: Successful Response
  Schema: `ImportantPostResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/important-posts/`
**Tóm tắt**: List Important Posts
**Mô tả**: Lấy danh sách bài viết quan trọng với filter và pagination

Args:
    page: Số trang (bắt đầu từ 1)
    page_size: Số bài viết mỗi trang
    type_newspaper: Lọc theo loại báo
    data_type: Lọc theo loại dữ liệu
    dvhc: Lọc theo đơn vị hành chính
    is_featured: Lọc bài nổi bật
    min_importance: Điểm quan trọng tối thiểu
    search: Từ khóa tìm kiếm
    sort_by: Trường sắp xếp
    order: Thứ tự sắp xếp (asc/desc)
    
Returns:
    ImportantPostListResponse: Danh sách bài viết với pagination
**Tham số URL/Query**:
- `page` (integer, query, tùy chọn): Số trang
- `page_size` (integer, query, tùy chọn): Số bài viết mỗi trang
- `type_newspaper` (string, query, tùy chọn): Lọc theo loại báo (medical, economic, ...)
- `data_type` (string, query, tùy chọn): Lọc theo loại dữ liệu (newspaper, social, ...)
- `dvhc` (string, query, tùy chọn): Lọc theo đơn vị hành chính
- `is_featured` (string, query, tùy chọn): Lọc bài nổi bật (1) hay không (0)
- `min_importance` (string, query, tùy chọn): Điểm quan trọng tối thiểu
- `search` (string, query, tùy chọn): Tìm kiếm trong title hoặc content
- `sort_by` (string, query, tùy chọn): Sắp xếp theo field (id, created_at, importance_score, ...)
- `order` (string, query, tùy chọn): Thứ tự sắp xếp
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ImportantPostListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/important-posts/{post_id}`
**Tóm tắt**: Get Important Post
**Mô tả**: Lấy chi tiết một bài viết theo ID

Args:
    post_id: ID của bài viết
    
Returns:
    ImportantPostResponse: Chi tiết bài viết
**Tham số URL/Query**:
- `post_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ImportantPostResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `PUT /api/important-posts/{post_id}`
**Tóm tắt**: Update Important Post
**Mô tả**: Cập nhật một bài viết

Args:
    post_id: ID của bài viết
    post_update: Dữ liệu cần cập nhật
    
Returns:
    ImportantPostResponse: Bài viết đã cập nhật
**Tham số URL/Query**:
- `post_id` (integer, path, bắt buộc): 
**Request Body (JSON)**:
Schema: `ImportantPostUpdate`
```json
{
  - `title` (any): 
  - `content` (any): 
  - `type_newspaper` (any): 
  - `meta_data` (any): 
  - `author` (any): 
  - `published_date` (any): 
  - `dvhc` (any): 
  - `statistics` (any): 
  - `organizations` (any): 
  - `is_featured` (any): 
  - `importance_score` (any): 
  - `tags` (any): 
  - `categories` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ImportantPostResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/important-posts/{post_id}`
**Tóm tắt**: Delete Important Post
**Mô tả**: Xóa một bài viết

Args:
    post_id: ID của bài viết
**Tham số URL/Query**:
- `post_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `204`: Successful Response
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/important-posts/by-type/{type_newspaper}`
**Tóm tắt**: Get Posts By Type
**Mô tả**: Lấy danh sách bài viết theo loại báo (medical, economic, ...)

Args:
    type_newspaper: Loại báo
    page: Số trang
    page_size: Số bài viết mỗi trang
    sort_by: Trường sắp xếp
    order: Thứ tự sắp xếp
    
Returns:
    ImportantPostListResponse: Danh sách bài viết
**Tham số URL/Query**:
- `type_newspaper` (string, path, bắt buộc): 
- `page` (integer, query, tùy chọn): 
- `page_size` (integer, query, tùy chọn): 
- `sort_by` (string, query, tùy chọn): 
- `order` (string, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ImportantPostListResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/important-posts/stats/overview`
**Tóm tắt**: Get Posts Statistics
**Mô tả**: Lấy thống kê tổng quan về các bài viết quan trọng

Args:
    type_newspaper: Lọc theo loại báo
    limit_recent: Số bài viết gần nhất cần lấy
    
Returns:
    ImportantPostStatsResponse: Thống kê tổng quan
**Tham số URL/Query**:
- `type_newspaper` (string, query, tùy chọn): Lọc theo loại báo
- `limit_recent` (integer, query, tùy chọn): Số bài viết gần nhất
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ImportantPostStatsResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/important-posts/bulk/import`
**Tóm tắt**: Bulk Import Posts
**Mô tả**: Import hàng loạt bài viết từ API nguồn

Args:
    posts: Danh sách bài viết cần import
    skip_duplicates: Bỏ qua các URL đã tồn tại
    
Returns:
    Dict với thông tin import
**Tham số URL/Query**:
- `skip_duplicates` (boolean, query, tùy chọn): Bỏ qua các URL đã tồn tại
**Request Body (JSON)**:
```json
{
  "type": "array",
  "items": {
    "$ref": "#/components/schemas/ImportantPostCreate"
  },
  "title": "Posts"
}
```
**Phản hồi (Responses)**:
- `201`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `PUT /api/important-posts/bulk/update-featured`
**Tóm tắt**: Bulk Update Featured
**Mô tả**: Cập nhật cờ featured cho nhiều bài viết

Args:
    post_ids: Danh sách ID bài viết
    is_featured: Giá trị featured (0 hoặc 1)
    
Returns:
    Dict với số bài viết đã cập nhật
**Tham số URL/Query**:
- `is_featured` (integer, query, bắt buộc): 
**Request Body (JSON)**:
```json
{
  "type": "array",
  "items": {
    "type": "integer"
  },
  "title": "Post Ids"
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/statistics/economic`
**Tóm tắt**: Create Economic Statistics
**Mô tả**: Create new economic statistics record.
**Request Body (JSON)**:
Schema: `EconomicStatisticsCreate`
```json
{
  - `dvhc` (string): Đơn vị hành chính
  - `source_post_id` (any): 
  - `source_url` (any): 
  - `period` (any): 
  - `year` (any): 
  - `total_production_value` (any): Tổng giá trị sản xuất (tỷ đồng)
  - `growth_rate` (any): Tốc độ tăng trưởng (%)
  - `total_budget_revenue` (any): Tổng thu ngân sách (tỷ đồng)
  - `budget_collection_efficiency` (any): Hiệu suất thu ngân sách (%)
  - `notes` (any): 
  - `extraction_metadata` (any): 
}
```
**Phản hồi (Responses)**:
- `201`: Successful Response
  Schema: `EconomicStatisticsResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/statistics/economic`
**Tóm tắt**: List Economic Statistics
**Mô tả**: List economic statistics with filters.
**Tham số URL/Query**:
- `dvhc` (string, query, tùy chọn): 
- `year` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `array`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/statistics/economic/{stat_id}`
**Tóm tắt**: Get Economic Statistics
**Mô tả**: Get economic statistics by ID.
**Tham số URL/Query**:
- `stat_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `EconomicStatisticsResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `PUT /api/statistics/economic/{stat_id}`
**Tóm tắt**: Update Economic Statistics
**Mô tả**: Update economic statistics record.
**Tham số URL/Query**:
- `stat_id` (integer, path, bắt buộc): 
**Request Body (JSON)**:
Schema: `EconomicStatisticsUpdate`
```json
{
  - `dvhc` (any): 
  - `source_post_id` (any): 
  - `source_url` (any): 
  - `period` (any): 
  - `year` (any): 
  - `total_production_value` (any): 
  - `growth_rate` (any): 
  - `total_budget_revenue` (any): 
  - `budget_collection_efficiency` (any): 
  - `notes` (any): 
  - `extraction_metadata` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `EconomicStatisticsResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/statistics/economic/{stat_id}`
**Tóm tắt**: Delete Economic Statistics
**Mô tả**: Delete economic statistics record.
**Tham số URL/Query**:
- `stat_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/statistics/political`
**Tóm tắt**: Create Political Statistics
**Mô tả**: Create new political statistics record.
**Request Body (JSON)**:
Schema: `PoliticalStatisticsCreate`
```json
{
  - `dvhc` (string): Đơn vị hành chính
  - `source_post_id` (any): 
  - `source_url` (any): 
  - `period` (any): 
  - `year` (any): 
  - `party_organization_count` (any): Số tổ chức Đảng
  - `party_member_count` (any): Số lượng Đảng viên
  - `party_size_description` (any): Mô tả quy mô Đảng bộ
  - `new_party_members` (any): 
  - `party_cells_count` (any): Số chi bộ
  - `notes` (any): 
  - `extraction_metadata` (any): 
}
```
**Phản hồi (Responses)**:
- `201`: Successful Response
  Schema: `PoliticalStatisticsResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/statistics/political`
**Tóm tắt**: List Political Statistics
**Mô tả**: List political statistics with filters.
**Tham số URL/Query**:
- `dvhc` (string, query, tùy chọn): 
- `year` (string, query, tùy chọn): 
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `array`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/statistics/political/{stat_id}`
**Tóm tắt**: Get Political Statistics
**Mô tả**: Get political statistics by ID.
**Tham số URL/Query**:
- `stat_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `PoliticalStatisticsResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `PUT /api/statistics/political/{stat_id}`
**Tóm tắt**: Update Political Statistics
**Mô tả**: Update political statistics record.
**Tham số URL/Query**:
- `stat_id` (integer, path, bắt buộc): 
**Request Body (JSON)**:
Schema: `PoliticalStatisticsUpdate`
```json
{
  - `dvhc` (any): 
  - `source_post_id` (any): 
  - `source_url` (any): 
  - `period` (any): 
  - `year` (any): 
  - `party_organization_count` (any): 
  - `party_member_count` (any): 
  - `party_size_description` (any): 
  - `new_party_members` (any): 
  - `party_cells_count` (any): 
  - `notes` (any): 
  - `extraction_metadata` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `PoliticalStatisticsResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/statistics/political/{stat_id}`
**Tóm tắt**: Delete Political Statistics
**Mô tả**: Delete political statistics record.
**Tham số URL/Query**:
- `stat_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/fields/`
**Tóm tắt**: Get All Fields
**Mô tả**: Lấy danh sách tất cả lĩnh vực
**Tham số URL/Query**:
- `skip` (integer, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `array`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/v1/fields/`
**Tóm tắt**: Create Field
**Mô tả**: Tạo lĩnh vực mới
**Request Body (JSON)**:
Schema: `FieldCreate`
```json
{
  - `name` (string): Tên lĩnh vực
  - `description` (any): Mô tả lĩnh vực
  - `keywords` (array): Từ khóa phân loại
  - `order_index` (integer): Thứ tự hiển thị
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `FieldResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/fields/{field_id}`
**Tóm tắt**: Get Field
**Mô tả**: Lấy thông tin một lĩnh vực
**Tham số URL/Query**:
- `field_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `FieldResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `PUT /api/v1/fields/{field_id}`
**Tóm tắt**: Update Field
**Mô tả**: Cập nhật thông tin lĩnh vực
**Tham số URL/Query**:
- `field_id` (integer, path, bắt buộc): 
**Request Body (JSON)**:
Schema: `FieldUpdate`
```json
{
  - `name` (any): 
  - `description` (any): 
  - `keywords` (any): 
  - `order_index` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `FieldResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/v1/fields/{field_id}`
**Tóm tắt**: Delete Field
**Mô tả**: Xóa lĩnh vực
**Tham số URL/Query**:
- `field_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/v1/fields/classify`
**Tóm tắt**: Classify Articles
**Mô tả**: Phân loại bài viết vào các lĩnh vực
- Nếu không truyền article_ids, sẽ phân loại tất cả bài viết chưa được phân loại
- force_reclassify=True để phân loại lại các bài đã được phân loại
- method: 
    + auto (mặc định): Dùng keyword trước, không match thì dùng LLM
    + keyword: Chỉ dùng keyword matching
    + llm: Chỉ dùng LLM (chậm hơn nhưng chính xác hơn)
**Tham số URL/Query**:
- `use_llm` (boolean, query, tùy chọn): Có sử dụng LLM cho bài không match keyword
**Request Body (JSON)**:
Schema: `ClassificationRequest`
```json
{
  - `article_ids` (any): Danh sách ID bài viết cần phân loại. Nếu None, phân loại tất cả
  - `force_reclassify` (boolean): Có phân loại lại các bài đã được phân loại hay không
  - `method` (string): Phương pháp phân loại: auto (keyword + LLM), keyword, llm
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ClassificationStatsResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/fields/distribution/overview`
**Tóm tắt**: Get Field Distribution
**Mô tả**: Lấy phân bố số lượng bài viết theo lĩnh vực
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `FieldDistributionResponse`

---
### `GET /api/v1/fields/article/{article_id}/classification`
**Tóm tắt**: Get Article Classification
**Mô tả**: Lấy thông tin phân loại của một bài viết
**Tham số URL/Query**:
- `article_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/v1/fields/article/{article_id}/classify`
**Tóm tắt**: Classify Single Article
**Mô tả**: Phân loại một bài viết cụ thể
**Tham số URL/Query**:
- `article_id` (integer, path, bắt buộc): 
- `force` (boolean, query, tùy chọn): Phân loại lại nếu đã tồn tại
- `method` (string, query, tùy chọn): Phương pháp: auto, keyword, llm
- `use_llm` (boolean, query, tùy chọn): Cho phép sử dụng LLM
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/fields/statistics/all`
**Tóm tắt**: Get All Statistics
**Mô tả**: Lấy thống kê của tất cả lĩnh vực
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `array`

---
### `GET /api/v1/fields/statistics/{field_id}`
**Tóm tắt**: Get Field Statistics
**Mô tả**: Lấy thống kê của một lĩnh vực
**Tham số URL/Query**:
- `field_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `FieldStatisticsResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/v1/fields/statistics/update`
**Tóm tắt**: Update Statistics
**Mô tả**: Cập nhật thống kê cho một hoặc tất cả lĩnh vực
**Tham số URL/Query**:
- `field_id` (string, query, tùy chọn): ID lĩnh vực cần update. Nếu None, update tất cả
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/v1/fields/seed`
**Tóm tắt**: Seed Fields
**Mô tả**: Seed dữ liệu các lĩnh vực từ bảng phân loại
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`

---
### `POST /api/v1/fields/summaries/generate`
**Tóm tắt**: Generate Summaries
**Mô tả**: Tạo tóm tắt thông tin gần đây cho lĩnh vực
- Phân tích các bài viết trong kỳ (daily/weekly/monthly)
- Tạo tóm tắt bằng LLM về xu hướng, chủ đề chính
- Lấy top bài viết nổi bật, từ khóa trending
**Request Body (JSON)**:
Schema: `CreateSummaryRequest`
```json
{
  - `field_ids` (any): Danh sách ID lĩnh vực. Nếu None, tạo cho tất cả
  - `period` (string): Kỳ tóm tắt: daily, weekly, monthly
  - `target_date` (any): Ngày tạo summary (YYYY-MM-DD). Mặc định: hôm nay
  - `model` (string): Model OpenAI
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `array`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/fields/summaries/latest`
**Tóm tắt**: Get Latest Summaries
**Mô tả**: Lấy các tóm tắt mới nhất
**Tham số URL/Query**:
- `period` (string, query, tùy chọn): Kỳ: daily, weekly, monthly
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `array`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/fields/summaries/{field_id}`
**Tóm tắt**: Get Field Summaries
**Mô tả**: Lấy tóm tắt của một lĩnh vực cụ thể
**Tham số URL/Query**:
- `field_id` (integer, path, bắt buộc): 
- `period` (string, query, tùy chọn): Kỳ: daily, weekly, monthly
- `limit` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `array`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/fields/summaries/detail/{summary_id}`
**Tóm tắt**: Get Summary Detail
**Mô tả**: Lấy chi tiết một tóm tắt
**Tham số URL/Query**:
- `summary_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `app__schemas__schema_field_classification__FieldSummaryResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/orchestrator/run-pipeline`
**Tóm tắt**: Run Pipeline
**Mô tả**: Chay pipeline xu ly data

Modes:
- full: Chay tat ca steps (sync, classify, sentiment, stats, keywords, bertopic)
- quick: Chi classify + sentiment + keywords (bo sync va training)
- custom: Tu chon cac steps

Args:
- mode: "full" | "quick" | "custom" (default: full)
- sync_data: Sync data tu external API (default: True)
- classify_topics: Classify topics chua xu ly (default: True)
- analyze_sentiment: Phan tich sentiment (default: True)
- calculate_statistics: Tinh statistics (default: True)
- regenerate_keywords: Tao keywords moi (default: True)
- train_bertopic: Train BERTopic de discover topics moi (default: True)
- limit: Gioi han so articles xu ly (None = all)
- background: Chay background khong block (default: False)

Example:
```bash
# Chay full pipeline
curl -X POST http://localhost:7777/api/orchestrator/run-pipeline

# Chay quick update
curl -X POST http://localhost:7777/api/orchestrator/run-pipeline \
  -H "Content-Type: application/json" \
  -d '{"mode": "quick", "limit": 200}'

# Custom config
curl -X POST http://localhost:7777/api/orchestrator/run-pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "custom",
    "classify_topics": true,
    "analyze_sentiment": true,
    "train_bertopic": false,
    "limit": 500
  }'
```
**Tham số URL/Query**:
- `background` (boolean, query, tùy chọn): 
**Request Body (JSON)**:
Schema: `PipelineConfig`
```json
{
  - `mode` (string): 
  - `sync_data` (boolean): 
  - `classify_topics` (boolean): 
  - `analyze_sentiment` (boolean): 
  - `calculate_statistics` (boolean): 
  - `regenerate_keywords` (boolean): 
  - `train_bertopic` (boolean): 
  - `limit` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `object`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/orchestrator/status`
**Tóm tắt**: Get Status
**Mô tả**: Kiem tra trang thai he thong

Returns:
- So luong articles, topics, classifications, sentiments
- Articles chua classify, chua analyze sentiment
- Keywords count
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `object`

---

## LLM Extraction APIs (Trích xuất bằng AI)

Không có endpoint nào trong nhóm này.


## Topic Service & Custom Topics (Học máy phân nhóm chủ đề)

### `POST /topic-service/ingest`
**Tóm tắt**: Ingest Documents
**Mô tả**: Ingest documents with sentiment analysis and auto-update statistics
**Request Body (JSON)**:
Schema: `IngestRequest`
```json
{
  - `documents` (array): 
  - `skip_duplicates` (boolean): 
  - `analyze_sentiment` (boolean): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /topic-service/train`
**Tóm tắt**: Train Topics
**Mô tả**: Train BERTopic model from database articles
**Request Body (JSON)**:
Schema: `TrainRequest`
```json
{
  - `min_topic_size` (integer): 
  - `use_vietnamese_tokenizer` (boolean): 
  - `enable_topicgpt` (boolean): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /topic-service/hybrid-train`
**Tóm tắt**: Hybrid Train
**Mô tả**: Hybrid Training - Smart decision between full training and transform

- Auto-detects if full retrain needed (monthly, drift, new data)
- Uses transform for daily updates
- Force full training with force_full=true

Example:
```bash
# Auto decision
curl -X POST http://localhost:7777/api/topic-service/hybrid-train

# Force full training
curl -X POST "http://localhost:7777/api/topic-service/hybrid-train?force_full=true"
```
**Tham số URL/Query**:
- `force_full` (boolean, query, tùy chọn): 
**Request Body (JSON)**:
Schema: `TrainRequest`
```json
{
  - `min_topic_size` (integer): 
  - `use_vietnamese_tokenizer` (boolean): 
  - `enable_topicgpt` (boolean): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /topic-service/training-recommendation`
**Tóm tắt**: Get Training Recommendation
**Mô tả**: Get recommendation on whether to retrain or transform

Returns analysis without actually training
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`

---
### `GET /topic-service/status`
**Tóm tắt**: Get Status
**Mô tả**: Get service status
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`

---
### `GET /topic-service/topics`
**Tóm tắt**: Get Topics
**Mô tả**: Get list of topics
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`

---
### `GET /topic-service/categories`
**Tóm tắt**: Get Available Categories
**Mô tả**: Get available topic categories
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`

---
### `POST /api/v1/custom-topics/`
**Tóm tắt**: Create Topic
**Mô tả**: Tạo topic mới

**Yêu cầu:**
- Tên topic phải unique
- Ít nhất 3 từ khóa
- (Tùy chọn) Câu văn mẫu để improve accuracy

**Ví dụ:**
```json
{
  "name": "Chính trị Việt Nam",
  "description": "Tin tức chính trị trong nước",
  "keywords": ["quốc hội", "chính phủ", "bộ trưởng", "nghị quyết", "chính sách"],
  "example_docs": [
    "Quốc hội thông qua nghị quyết về kinh tế",
    "Chính phủ ban hành chính sách mới"
  ],
  "min_confidence": 0.6,
  "color": "#EF4444"
}
```
**Request Body (JSON)**:
Schema: `CustomTopicCreate`
```json
{
  - `name` (string): Tên topic
  - `description` (any): Mô tả chi tiết
  - `keywords` (array): Danh sách từ khóa (tối thiểu 3)
  - `keywords_weight` (number): Trọng số keywords
  - `example_docs` (any): Câu văn mẫu
  - `example_weight` (number): 
  - `negative_keywords` (any): Từ khóa loại trừ
  - `classification_method` (any): 
  - `min_confidence` (number): Ngưỡng confidence
  - `color` (string): 
  - `icon` (any): 
  - `display_order` (integer): 
  - `parent_id` (any): 
  - `is_active` (boolean): 
  - `created_by` (any): 
}
```
**Phản hồi (Responses)**:
- `201`: Successful Response
  Schema: `CustomTopicResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/custom-topics/`
**Tóm tắt**: List Topics
**Mô tả**: Danh sách topics

**Filters:**
- `active_only`: Chỉ lấy topics active (default: true)
- `parent_id`: Lấy sub-topics của parent
- `search`: Tìm kiếm theo tên
**Tham số URL/Query**:
- `active_only` (boolean, query, tùy chọn): Chỉ lấy topics đang active
- `parent_id` (string, query, tùy chọn): Lọc theo parent (nested topics)
- `search` (string, query, tùy chọn): Tìm kiếm theo tên
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `array`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/custom-topics/{topic_id}`
**Tóm tắt**: Get Topic
**Mô tả**: Chi tiết 1 topic (kèm children và parent)
**Tham số URL/Query**:
- `topic_id` (integer, path, bắt buộc): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `CustomTopicDetailResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `PUT /api/v1/custom-topics/{topic_id}`
**Tóm tắt**: Update Topic
**Mô tả**: Cập nhật topic

**Note:** Sau khi update, nên chạy lại classification để cập nhật kết quả
**Tham số URL/Query**:
- `topic_id` (integer, path, bắt buộc): 
**Request Body (JSON)**:
Schema: `CustomTopicUpdate`
```json
{
  - `name` (any): 
  - `description` (any): 
  - `keywords` (any): 
  - `keywords_weight` (any): 
  - `example_docs` (any): 
  - `example_weight` (any): 
  - `negative_keywords` (any): 
  - `classification_method` (any): 
  - `min_confidence` (any): 
  - `color` (any): 
  - `icon` (any): 
  - `display_order` (any): 
  - `parent_id` (any): 
  - `is_active` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `CustomTopicResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `DELETE /api/v1/custom-topics/{topic_id}`
**Tóm tắt**: Delete Topic
**Mô tả**: Xóa topic

**Soft delete (default):** Set is_active = False  
**Hard delete:** Xóa vĩnh viễn (mất tất cả mappings)
**Tham số URL/Query**:
- `topic_id` (integer, path, bắt buộc): 
- `hard_delete` (boolean, query, tùy chọn): Xóa vĩnh viễn (mất data)
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/v1/custom-topics/classify`
**Tóm tắt**: Classify Articles
**Mô tả**: Phân loại bài viết vào custom topics

**Modes:**
- `article_ids`: Phân loại specific articles
- `all_unclassified`: Phân loại tất cả chưa có custom topic
- `all_articles`: Phân loại lại tất cả (re-classify)

**Methods:**
- `keyword`: So khớp từ khóa (nhanh, độ chính xác trung bình)
- `embedding`: Semantic similarity (chậm, chính xác cao)
- `hybrid`: Kết hợp cả 2 (khuyên dùng)

**Ví dụ:**
```json
{
  "all_unclassified": true,
  "method": "hybrid",
  "save_results": true,
  "topic_ids": [1, 2, 3]
}
```
**Request Body (JSON)**:
Schema: `ClassifyArticlesRequest`
```json
{
  - `article_ids` (any): Danh sách article IDs
  - `all_unclassified` (boolean): Phân loại tất cả chưa có topic
  - `all_articles` (boolean): Phân loại lại tất cả
  - `topic_ids` (any): Chỉ phân loại vào các topics này
  - `method` (any): 
  - `save_results` (boolean): Lưu kết quả vào database
  - `min_confidence` (any): Override min_confidence
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `BulkClassificationResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/custom-topics/articles/{article_id}/topics`
**Tóm tắt**: Get Article Topics
**Mô tả**: Lấy danh sách topics của 1 article
**Tham số URL/Query**:
- `article_id` (integer, path, bắt buộc): 
- `min_confidence` (number, query, tùy chọn): Lọc theo confidence
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `array`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/custom-topics/topics/{topic_id}/articles`
**Tóm tắt**: Get Topic Articles
**Mô tả**: Lấy danh sách articles thuộc 1 topic
**Tham số URL/Query**:
- `topic_id` (integer, path, bắt buộc): 
- `min_confidence` (number, query, tùy chọn): 
- `limit` (integer, query, tùy chọn): 
- `offset` (integer, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `TopicWithArticlesResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/custom-topics/stats/overview`
**Tóm tắt**: Get Classification Overview
**Mô tả**: Tổng quan hệ thống phân loại
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `ClassificationOverview`

---
### `POST /api/v1/custom-topics/templates`
**Tóm tắt**: Create Template
**Mô tả**: Tạo template topics (để tái sử dụng)

**Ví dụ:** Template "News Categories" với Politics, Economy, Sports, ...
**Request Body (JSON)**:
Schema: `TopicTemplateCreate`
```json
{
  - `name` (string): 
  - `description` (any): 
  - `category` (string): 
  - `topics_data` (array): 
  - `is_public` (boolean): 
  - `created_by` (any): 
}
```
**Phản hồi (Responses)**:
- `201`: Successful Response
  Schema: `TopicTemplateResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/custom-topics/templates`
**Tóm tắt**: List Templates
**Mô tả**: Danh sách templates
**Tham số URL/Query**:
- `category` (string, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `array`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /api/v1/custom-topics/templates/apply`
**Tóm tắt**: Apply Template
**Mô tả**: Áp dụng template để tạo hàng loạt topics

**Note:** Sẽ skip topics trùng tên (trừ khi override_existing=true)
**Request Body (JSON)**:
Schema: `ApplyTemplateRequest`
```json
{
  - `template_id` (integer): 
  - `override_existing` (boolean): Ghi đè topics trùng tên
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---

## Superset Sync & Utilities (Đồng bộ Superset & Tiện ích)

### `POST /api/v1/sync/trigger`
**Tóm tắt**: Trigger Sync
**Mô tả**: TRIGGER SYNC NGAY LAP TUC

Chay sync data tu API nguon (one-time)
- Chay background, khong block

Example:
```json
{
  "source_api_base": "http://192.168.30.28:8548",
  "endpoint": "/api/articles",
  "limit": 100,
  "batch_size": 20
}
```
**Request Body (JSON)**:
Schema: `SyncTriggerRequest`
```json
{
  - `source_api_base` (string): Base URL (VD: http://192.168.30.28:8548)
  - `endpoint` (string): Endpoint de lay data
  - `limit` (any): Gioi han so docs (None = all)
  - `batch_size` (integer): 
  - `skip_duplicates` (boolean): 
  - `analyze_sentiment` (boolean): 
  - `headers` (any): 
  - `auth_token` (any): 
  - `auth_type` (any): bearer, basic, api_key
  - `query_params` (any): 
}
```
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `SyncStatusResponse`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /api/v1/sync/status`
**Tóm tắt**: Get Sync Status
**Mô tả**: XEM TRANG THAI SYNC HIEN TAI

- Dang chay hay idle?
- Progress bao nhieu?
- Toc do xu ly?
**Phản hồi (Responses)**:
- `200`: Successful Response
  Schema: `SyncStatusResponse`

---
### `DELETE /api/v1/sync/clear-data`
**Tóm tắt**: Clear Test Data
**Mô tả**: XOA DATA TEST TRONG DATABASE

CANH BAO: Xoa vinh vien, khong the khoi phuc!

Parameters:
- table: Ten bang cu the (articles, sentiment_analysis, etc.)
         Neu None = xoa TAT CA
- confirm: PHAI set = true de xac nhan xoa

Cac bang co the xoa:
- articles: Bang bai viet goc
- sentiment_analysis: Bang phan tich cam xuc
- daily_snapshots: Thong ke theo ngay
- trend_reports: Bao cao xu huong
- hot_topics: Chu de nong
- keyword_stats: Thong ke tu khoa
- topic_mentions: Thong ke topic mentions
- website_stats: Thong ke theo website
- social_stats: Thong ke social media
- trend_alerts: Canh bao xu huong
- hashtag_stats: Thong ke hashtag
- viral_content: Noi dung viral
- category_trends: Xu huong theo danh muc
- all: XOA TAT CA
**Tham số URL/Query**:
- `table` (string, query, tùy chọn): 
- `confirm` (boolean, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `any`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `POST /superset/update-all`
**Tóm tắt**: Update All Superset Tables
**Mô tả**: Update ALL tables for Superset dashboards with 1 click

Updates:
- hot_topics (50 records)
- viral_contents (100 records)
- hashtag_stats
- category_trend_stats
- trend_reports
- keyword_stats
- daily_snapshots
- field_summaries
- topics_over_time
- social_activity_stats

Args:
    period_days: Number of days to analyze (default: 7, ignored if all_time=true)
    all_time: If true, analyze ALL data without time filter (default: false)

Returns:
    Dict with update results for each table

Examples:
    # Last 7 days
    curl -X POST "http://localhost:7777/superset/update-all"
    
    # Last 30 days
    curl -X POST "http://localhost:7777/superset/update-all?period_days=30"
    
    # ALL TIME
    curl -X POST "http://localhost:7777/superset/update-all?all_time=true"
**Tham số URL/Query**:
- `period_days` (integer, query, tùy chọn): 
- `all_time` (boolean, query, tùy chọn): 
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `object`
- `422`: Validation Error
  Schema: `HTTPValidationError`

---
### `GET /superset/status`
**Tóm tắt**: Get Superset Table Status
**Mô tả**: Check status of all Superset tables

Returns record counts and last update times
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `object`

---
### `POST /superset/update-field-summaries`
**Tóm tắt**: Update Field Summaries Only
**Mô tả**: Update ONLY field_summaries with LLM-generated summaries (using OpenRouter)

Creates monthly summaries for January 2026
Uses OpenRouter API with gpt-4o-mini (cheap & good quality)

Returns:
    Dict with field_summaries update results

Example:
    curl -X POST "http://localhost:7777/superset/update-field-summaries"
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `object`

---
### `POST /superset/update-field-sentiments`
**Tóm tắt**: Update Field Sentiments Only
**Mô tả**: Update field_sentiments - Phân tích sentiment theo lĩnh vực

Phân tích cảm xúc (tích cực/tiêu cực/trung lập) của tin tức theo từng lĩnh vực
Sử dụng OpenRouter + LLM để phân tích sentiment

Returns:
    Dict with sentiment analysis results

Example:
    curl -X POST "http://localhost:7777/superset/update-field-sentiments"
**Phản hồi (Responses)**:
- `200`: Successful Response
  Type: `object`

---