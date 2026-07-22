# Báo cáo Review Dự án: Pipeline MXH — Hệ thống Phân tích Tin tức & Mạng xã hội bằng AI

> Tài liệu tổng hợp phục vụ buổi review dự án. Nội dung dựa trên phân tích trực tiếp mã nguồn, cấu trúc thư mục, migrations và lịch sử commit tại `/home/ai_team/lab/pipeline_mxh` (cập nhật 2026-07-10).

---

## 1. Mục tiêu & Phạm vi dự án

Hệ thống backend phục vụ **phân tích quản lý nhà nước và kinh tế - xã hội**, thu thập dữ liệu từ báo chí và mạng xã hội, tự động trích xuất **20+ nhóm chỉ số kinh tế - xã hội** (GRDP, CPI, IIP, FDI, PII, y tế, giáo dục, an ninh, PAR Index...), phân tích chủ đề/cảm xúc bằng AI, và đồng bộ dữ liệu ra Apache Superset để trực quan hóa.

**Đối tượng phục vụ:** cơ quan quản lý nhà nước cần theo dõi tình hình kinh tế - xã hội - dư luận qua dữ liệu báo chí/MXH thay vì thống kê thủ công.

---

## 2. Kiến trúc tổng thể

```
Nguồn dữ liệu (Báo chí, Facebook, TikTok, Threads, Văn bản)
        │
        ▼
┌───────────────────┐     ┌────────────────────┐     ┌─────────────────────┐
│   1. FETCH         │ ──▶ │   2. PROCESS (ETL)  │ ──▶ │   3. DATABASE        │
│  Scrapy/Playwright  │     │  Clean + Dedupe     │     │  PostgreSQL (30+     │
│  Feedparser/HTTPX   │     │  (MD5+Simhash,      │     │  bảng dữ liệu)       │
└───────────────────┘     │   Semantic Vector)   │     └──────────┬───────────┘
                            └────────────────────┘                │
                                                                   ▼
                            ┌──────────────────────────────────────────────┐
                            │   4. AI PROCESSING LAYER                      │
                            │  • BERTopic (Topic Modeling tiếng Việt)       │
                            │  • Field Classification (phân ngành)         │
                            │  • Sentiment Analysis (cảm xúc theo lĩnh vực) │
                            │  • LLM Extraction (OpenRouter/GPT-4o-mini)    │
                            │    → trích số liệu kinh tế - xã hội           │
                            └──────────────────────┬─────────────────────────┘
                                                    ▼
                            ┌──────────────────────────────────────────────┐
                            │   5. INDICATOR TABLES (27 bảng chi tiết)      │
                            │  Kinh tế, Xã hội, Hành chính - Chính trị      │
                            └──────────────────────┬─────────────────────────┘
                                                    ▼
                            ┌──────────────────────────────────────────────┐
                            │   6. SUPERSET SYNC → Dashboard trực quan hóa  │
                            └──────────────────────────────────────────────┘
```

**Công nghệ chính:**

| Nhóm | Công nghệ |
|---|---|
| Backend Framework | FastAPI + Uvicorn/Gunicorn, Pydantic |
| Database | PostgreSQL (chính) + SQLAlchemy/Alembic; Redis, MongoDB, Minio hỗ trợ |
| Thu thập dữ liệu | Scrapy, Playwright (JS render), BeautifulSoup4, Feedparser, HTTPX/Aiohttp |
| NLP / Topic Modeling | BERTopic, Sentence-Transformers, Underthesea (tách từ tiếng Việt), UMAP + HDBSCAN, FAISS |
| LLM / RAG | OpenAI GPT-4o-mini qua OpenRouter, LangChain, Google Generative AI (dự phòng) |
| Auth & Bảo mật | Keycloak SSO |
| Trực quan hóa | Apache Superset |
| DevOps | Docker & Docker Compose (dev + `docker-compose.prod.yml` cho production), Prometheus metrics |

**Quy mô mã nguồn:** ~38.000 dòng Python, **30 models** (bảng dữ liệu), **33 module API**, **30 router** được đăng ký trong `app/main.py`.

---

## 3. Luồng xử lý End-to-End

### Bước 1 — Thu thập dữ liệu (Fetch)
`POST /api/fetch` — endpoint hợp nhất, lấy dữ liệu từ nhiều nguồn (`sources: ["facebook", "newspaper", "tiktok", "threads"]`). Có cơ chế **Smart Selection**: loại rác ngay tại cổng crawl bằng heuristic để giảm tải hệ thống.

### Bước 2 — Xử lý & làm sạch (ETL/Process)
`POST /api/process` — chuẩn hóa văn bản, tách từ tiếng Việt (Pyvi/Underthesea), và **de-duplication 2 lớp**:
- Lớp 1 (MD5 + Simhash): loại bài trùng lặp 100%.
- Lớp 2 (Semantic Vector Search): loại bài bị "viết lại" ngữ nghĩa tương tự.

Kết quả nạp vào PostgreSQL (bảng `articles` + các bảng liên quan).

### Bước 3 — Phân loại & phân tích AI
- **Field Classification**: gán bài viết vào lĩnh vực (Y tế, Giáo dục, Kinh tế, Chính trị...).
- **Sentiment Analysis**: chấm điểm cảm xúc dư luận (Tích cực/Tiêu cực/Trung lập) theo từng lĩnh vực.
- **BERTopic (Topic Modeling)** — "trái tim" của hệ thống:
  1. Tách từ tiếng Việt (Underthesea) → tránh hiểu sai cụm từ ghép.
  2. Embedding đa ngôn ngữ (`paraphrase-multilingual-MiniLM-L12-v2`).
  3. UMAP giảm chiều + HDBSCAN phân cụm tự động (không cần khai báo số cụm trước).
  4. C-TF-IDF trích từ khóa đặc trưng từng cụm.
  5. **Hybrid với LLM**: GPT đặt tên chủ đề tự nhiên từ keyword thô; phân loại nội dung ngắn (< 200 ký tự, ví dụ status MXH) vào topic đã khám phá.
  6. **Dynamic Topic Modeling**: theo dõi topic tăng/giảm theo thời gian (ngày/tuần/tháng).
  7. Lưu Session huấn luyện để so sánh hiệu quả qua các lần train; lọc nhiễu (Topic -1).

### Bước 4 — Trích xuất chỉ số kinh tế - xã hội bằng LLM (điểm kỹ thuật nổi bật nhất)
Vì để LLM tự sinh số liệu có rủi ro **hallucination** (bịa số) — không chấp nhận được với dữ liệu phục vụ quản lý nhà nước — hệ thống dùng pipeline 4 bước kiểm soát chặt:

```
Bài viết trong DB
  → (1) Pre-filter theo URL/Tiêu đề bằng Regex (chưa dùng LLM, loại ~95% bài không liên quan)
  → (2) LLM Classifier xác nhận bối cảnh — CHỈ trả lời YES/NO dạng JSON (GPT-4o-mini qua OpenRouter)
  → (3) Regex Value Extractor lấy số liệu trực tiếp từ văn bản gốc (không để LLM tự sinh số)
  → (4) Pydantic Validator kiểm tra range hợp lệ trước khi lưu
  → Lưu vào bảng chỉ số tương ứng trong DB
```

### Bước 5 — Lưu trữ chỉ số (27 bảng chi tiết, 3 khối lớn)
| Khối | Chỉ số |
|---|---|
| Kinh tế | GRDP, CPI, IIP, FDI, PII (Đổi mới sáng tạo), Kinh tế số, Chuyển đổi số |
| Xã hội | Y tế, Giáo dục (THPT, TVET), Văn hóa - Lối sống, An ninh trật tự, Chất lượng không khí (AQI) |
| Hành chính - Chính trị | PAR Index, SIPAS (hài lòng), Cán bộ công chức, Xây dựng Đảng, Bài viết trọng tâm/cảnh báo |

### Bước 6 — Đồng bộ & trực quan hóa
`POST /superset/sync` đẩy dữ liệu chuẩn hóa sang Apache Superset để dựng dashboard; `GET /superset/status` theo dõi tình trạng đồng bộ.

### Điều phối toàn bộ (Orchestrator)
`POST /api/orchestrator/run-pipeline` cho phép chạy **toàn bộ chuỗi** (Sync → Classify → Sentiment → Statistics → Keywords → BERTopic training) theo 3 chế độ: `full`, `quick`, `custom`, hỗ trợ chạy nền (`background=true`) và giới hạn số lượng bài xử lý (`limit`).

---

## 4. Bảo mật & Vận hành
- **Xác thực**: tích hợp SSO Keycloak (realm/client cấu hình qua biến môi trường), có thể bật/tắt qua `KEYCLOAK_VERIFY`.
- **Giám sát**: Prometheus metrics (`metrics.py`) theo dõi hiệu năng server; có `docker-compose-monitoring.yml` riêng.
- **Quản lý chi phí LLM**: cơ chế pre-filter Regex trước khi gọi LLM giúp giảm mạnh chi phí gọi API (loại ~95% bài không liên quan trước khi tốn token).
- **Triển khai**: Docker Compose cho dev (`docker-compose.yml`) và production (`docker-compose.prod.yml`, mới thêm 2026-06-03).
- **Backup**: có thư mục `backups/` chứa dump PostgreSQL định kỳ (`.sql.gz`), gần nhất ghi nhận 2026-01-21.

---

## 5. Tình trạng hiện tại & Lịch sử phát triển

- Dự án đã trải qua **refactor API** đáng kể: gộp từ **71 → 30 endpoints** để giảm phức tạp và trùng lặp (xem `API_REFACTORING_PLAN.md`).
- Lịch sử commit cho thấy phát triển tích cực xuyên suốt tháng 1/2026 (nhiều commit theo ngày: 9/1, 12/1, 15/1, 17/1, 26/1, 31/1), sau đó có đợt bổ sung hạ tầng triển khai production vào 2026-06-03 (thêm `docker-compose.prod.yml`, cấu hình `.gitignore` cho backups).
- Nhánh làm việc hiện tại: `feature/backup` — đang có nhiều thay đổi chưa commit liên quan đến tài liệu, cấu hình, migrations và backup files (cần rà soát/commit trước khi review nếu muốn trình bày trạng thái sạch).
- Codebase đã có tài liệu nội bộ khá đầy đủ: `SYSTEM_ARCHITECTURE.md`, `DATA_SUMMARY.md`, `EXTERNAL_API_SOURCES.md`, `LLM_AUTO_FILL_README.md`, `QUICK_REFERENCE.md`, và `docs/project_overview.md`, `docs/PIPELINE_OVERVIEW.md`.

---

## 6. Điểm mạnh nổi bật để trình bày

1. **Kiến trúc chống hallucination cho LLM** — kết hợp Regex pre-filter + LLM classifier nhị phân + Regex extractor + Pydantic validation, đảm bảo độ tin cậy số liệu cho báo cáo nhà nước.
2. **NLP tiếng Việt chuyên sâu**: Underthesea tách từ ghép, kết hợp BERTopic không giám sát + GPT để đặt tên chủ đề tự nhiên và xử lý nội dung ngắn (MXH).
3. **Dedup 2 lớp** (hash + semantic) giải quyết vấn đề tin đăng lại/viết lại — phổ biến trong dữ liệu báo chí/MXH Việt Nam.
4. **Hệ sinh thái chỉ số toàn diện**: 27 bảng chi tiết bao phủ cả kinh tế, xã hội, hành chính - chính trị, đủ để phục vụ báo cáo đa ngành.
5. **Orchestrator thống nhất**: một endpoint điều phối toàn bộ pipeline, dễ vận hành/lên lịch (cron) thay vì gọi tay từng bước.
6. **Đã refactor giảm 58% số endpoint**, cho thấy dự án có ý thức quản lý technical debt.

## 7. Điểm cần lưu ý / rủi ro khi review

- Nhiều thay đổi working-tree chưa commit trên nhánh `feature/backup` — nên dọn dẹp/commit rõ ràng trước khi trình bày để tránh mất mát dữ liệu.
- Phụ thuộc nhiều vào LLM ngoài (OpenRouter/GPT-4o-mini) cho bước classifier — cần làm rõ chi phí vận hành & SLA khi có sự cố nhà cung cấp.
- Tài liệu dự án hiện có ở nhiều file rời rạc (README, docs/, SYSTEM_ARCHITECTURE.md...) — nên hợp nhất để tránh lệch thông tin giữa các bản.

---

*File này được tạo tự động từ phân tích mã nguồn thực tế để phục vụ báo cáo review. Có thể chỉnh sửa trực tiếp trước khi trình bày.*
