# Tổng quan Dự án: Topic Modeling & ETL Pipeline Service

## 1. Mở đầu
Đây là một service backend viết bằng **FastAPI**, đóng vai trò là một Data Pipeline kết hợp với Topic Modeling và LLM Information Extraction. Hệ thống tập trung vào việc thu thập, xử lý, trích xuất và phân tích dữ liệu văn bản từ nhiều nguồn (Mạng xã hội, Báo chí, Văn bản nội bộ/bên ngoài) để đưa ra các chỉ số kinh tế, xã hội, giáo dục, y tế và môi trường.

## 2. Các Công nghệ sử dụng
### Core Framework & Server
- **FastAPI**: Web framework chính để xây dựng các API.
- **Uvicorn & Gunicorn**: ASGI Server phục vụ ứng dụng.
- **Python**: Ngôn ngữ lập trình chính (yêu cầu quản lý qua `requirements.txt`).
- **Pydantic**: Data validation và settings management.

### Database & ORM
- **PostgreSQL**: Cơ sở dữ liệu chính lưu trữ dữ liệu đã xử lý.
- **SQLAlchemy & Alembic**: ORM để giao tiếp với DB và quản lý migration.
- **FastAPI-SQLAlchemy**: Middleware quản lý DB session cho các API.
- **MongoDB / Redis / Minio**: Được định nghĩa trong requirements hoặc config để phục vụ caching, object storage hoặc NoSQL storage.

### Data Fetching & Web Scraping (ETL Giai đoạn 1)
- **Scrapy**: Web crawling framework.
- **BeautifulSoup4 & lxml**: Cắt tách, phân tích HTML từ các bài báo, website.
- **Playwright**: Render và chạy Javascript để crawl các trang web động (Crawl data từ mạng xã hội).
- **Feedparser**: Phân tích cú pháp RSS/Atom feeds (báo chí).
- **Aiohttp & HTTPX**: Hỗ trợ gọi API bất đồng bộ.

### Natural Language Processing (NLP) & Topic Modeling
- **BERTopic**: Framework chính cho Topic Modeling.
- **Sentence-Transformers**: Mô hình nhúng biểu diễn ngôn ngữ.
- **Underthesea**: Gói NLP chuyên dụng để Tokenization, phân tích từ ngữ tiếng Việt.
- **HDBScan & UMAP-learn**: Phân cụm và giảm chiều dữ liệu cho máy học.
- **Scikit-learn / Faiss-cpu**: Hỗ trợ xử lý văn bản, TF-IDF, và tìm kiếm vector nội dung.

### Large Language Models (LLM) & RAG
- **OpenAI (GPT-4o-mini)**: Tích hợp lấy dữ liệu hoặc gọi thông qua OpenRouter.
- **Langchain & Langchain-OpenAI, Langchain-Google-GenAI**: Tích hợp các luồng RAG và pipelines gọi Model.
- **Google Generative AI**: Cung cấp LLM dự phòng hoặc đặc thù.

### DevOps, Monitoring & Miscellaneous
- **Docker & Docker Compose**: Ứng dụng được đóng gói toàn bộ và triển khai bằng Docker (tích hợp `docker-compose-monitoring.yml`).
- **Prometheus-client**: Cung cấp metrics để theo dõi hiệu năng của FastAPI server.
- **AnyIO**: Xử lý async / background tasks.

---

## 3. Chi tiết về cơ chế BERTopic trong dự án
BERTopic đóng vai trò là "trái tim" của hệ thống phân tích chủ đề, thay vì dựa trên từ khóa cố định, nó tự động phát hiện xu hướng từ dữ liệu thô.

### Cơ chế hoạt động & Pipeline
1. **Tiền xử lý (Underthesea):** Thực hiện Vietnamese Word Segmentation giúp mô hình hiểu đúng các cụm từ ghép (vd: "kinh tế số", "vốn đầu tư").
2. **Nhúng văn bản (Embeddings):** Chuyển đổi văn bản thành vector bằng model đa ngôn ngữ `paraphrase-multilingual-MiniLM-L12-v2`.
3. **Giảm chiều & Phân cụm:** Sử dụng **UMAP** để nén vector và **HDBSCAN** để tự động gom nhóm bài viết thành các cụm chủ đề mà không cần khai báo trước số lượng cụm.
4. **Trích xuất Keyword (C-TF-IDF):** Xác định các từ khóa đặc trưng nhất cho từng cụm chủ đề được tìm thấy.

### Mô hình Lai (Hybrid) với LLM
- **Naming & Labeling:** Kết hợp với GPT để đặt tên chủ đề (natural label) và viết mô tả dựa trên các keyword thô từ BERTopic.
- **Short Content Handling:** Với các nội dung ngắn (<200 ký tự) khó phân cụm, hệ thống dùng GPT để phân loại chúng vào các chủ đề mà BERTopic đã khám phá được ở nội dung dài.

### Dynamic Topic Modeling (DTM)
Sử dụng tính năng **Topics Over Time** để theo dõi sự biến đổi, tăng trưởng hoặc suy giảm của các chủ đề theo từng mốc thời gian (ngày/tuần/tháng).

---

## 4. Các Tính năng Chính
- **ETL Component**: Cung cấp các API để fetch data từ mạng xã hội (Facebook, Threads, TikTok), báo chí và tải tài liệu (Document). Sau đó làm sạch, chuẩn hóa (process) và tải lên cơ sở dữ liệu.
- **Topic Modeling Service**: Phân loại tự động các bài đã thu thập thành những Topic (Chủ đề) khác nhau dựa trên NLP tiếng Việt (BERTopic). Có hỗ trợ cả các chủ đề do user tự định nghĩa (Custom topics).
- **LLM Information Extraction**: 
  - Khai phá các số liệu đặc thù qua Prompt Engineering mà không dựa vào regex cơ bản.
  - Phân tích và điền tự động dữ liệu cho các bảng kinh tế chi tiết.
- **Báo cáo Thống kê**: Tự động tổng hợp và sinh thống kê từ bài viết thành các metrics kinh tế số, FDI, IIP, giáo dục, trật tự xã hội v.v..
- **Đồng bộ hóa**: Cung cấp các công cụ như `Superset Sync` để đồng bộ dữ liệu chuẩn hóa phục vụ lên biểu đồ và báo cáo.

---

## 5. Các Module Cốt lõi của Dự án

Dự án được chia làm nhiều luồng phân tích thông qua `router` trong `app/main.py`:

### a. Module ETL & Data Pipeline (`api_fetch_*` & `api_process_*`)
- Thu thập (Fetch) nội dung từ Social Media (Facebook, Tiktok, Threads) và Newspaper.
- Xử lý ngôn ngữ, làm sạch rác, lưu trữ vào Database dạng raw và pre-processed.
- Fetch và process tài liệu dạng file (Document).

### b. Module Topic Modeling
- `topic_service.py` / `custom_topics.py`: APIs phân tích chủ đề, quản lý danh sách các Topic.

### c. Module Economic Indicators (Chỉ số Kinh tế)
Chuyên bóc tách và truy vấn số liệu về:
- **Kinh tế số (Digital Economy)** & **Chuyển đổi số (Digital Transformation)**.
- **FDI** (Đầu tư trực tiếp nước ngoài).
- **GRDP**, **CPI** (Chỉ số giá tiêu dùng) & **IIP** (Chỉ số sản xuất công nghiệp).
- **PII** (Bộ chỉ số Đổi mới sáng tạo).

### d. Module Social Indicators (Chỉ số Xã hội) 
Cung cấp API cho 27 bảng detail của 9 Lĩnh vực:
- **Giáo dục & Việc làm**: Xét điểm thi tốt nghiệp THPT (`highschool_graduation`), Giáo dục nghề nghiệp & Việc làm (`tvet_employment`).
- **Y tế, Văn hóa & Xã hội**: Thống kê y tế (`health_statistics`), Lối sống và văn hóa (`culture_lifestyle`).
- **An ninh & Khí hậu**: Trật tự an ninh (`security`), Chất lượng không khí từ external API (`aqi`).
- **Quản trị công**: Chỉ số cải cách hành chính (`par_index`), Chỉ số hài lòng (`sipas`), Cán bộ công chức viên chức (`cadre_statistics`).

### e. Module LLM Extraction & Orchestration
- `api_llm_extraction.py`: Module chung cho phép gửi nội dung vào quy trình gọi OpenRouter/OpenAI theo batches để lấy kết quả dạng JSON cho các model schemas phức tạp.
- `orchestrator.py`: Orchestrator API để điều phối workflow cho pipeline thống nhất.
- `important_posts.py` & `statistics.py`: Đánh giá, lưu trữ tin tức quan trọng từ đó tự động chạy pipeline thống kê chính trị - xã hội.
- `xay_dung_dang.py`: Module phân tích, xuất các báo cáo về công tác Xây dựng Đảng dựa trên dữ liệu báo chí, mạng xã hội.

### f. Utils & Monitoring
- `metrics.py`: Tích hợp với Prometheus để xuất các chỉ số server hoạt động.
- Các config middlewares hỗ trợ CORS, Exception handlers (Custom Exception), và Rate Limit. 

Searched for "BERTopic"
Viewed model.py:1-436
Viewed bertopic_trainer.py:1-373
Viewed hybrid_topic_classifier.py:1-184

Trong dự án này, **BERTopic** đóng vai trò là "trái tim" của hệ thống phân tích chủ đề (Topic Modeling). Thay vì phân loại dựa trên các từ khóa cố định (như Regex), BERTopic sử dụng học máy (Machine Learning) để tự động phát hiện ra các xu hướng và chủ đề đang diễn ra trong dữ liệu.

Dưới đây là chi tiết các nhiệm vụ và quy trình mà BERTopic thực hiện:

### 1. Engine Khám phá Chủ đề Tự động (Unsupervised Topic Discovery)
BERTopic được sử dụng để quét qua hàng nghìn bài viết và tự động gom nhóm chúng lại thành các cụm (clusters) dựa trên sự tương đồng về ngữ nghĩa.
- **Phạm vi:** Ưu tiên xử lý các bài viết có nội dung dài (**> 200 ký tự**) để đảm bảo đủ thông tin về ngữ cảnh.
- **Xử lý đa ngôn ngữ:** Sử dụng model `paraphrase-multilingual-MiniLM-L12-v2` giúp hiểu sâu sắc tiếng Việt.

### 2. Quy trình Pipeline NLP Chuyên sâu
Hệ thống cấu hình một Pipeline phức tạp cho BERTopic bao gồm:
- **Tiền xử lý (Preprocessing):** Tích hợp thư viện `Underthesea` để thực hiện **Vietnamese Word Segmentation** (tách từ ghép như "kinh_tế_số", "chuyển_đổi_số") giúp mô hình không hiểu nhầm các từ đơn lẻ.
- **Nhúng văn bản (Embeddings):** Chuyển đổi văn bản thành các vector toán học mang ý nghĩa ngữ nghĩa.
- **Giảm chiều dữ liệu (UMAP):** Nén các vector phức tạp để thuật toán phân cụm hoạt động hiệu quả và nhanh hơn.
- **Phân cụm (HDBSCAN):** Tự động tìm ra các cụm bài viết mà không cần biết trước có bao nhiêu chủ đề (khác với K-Means cần khai báo số cụm).
- **Trích xuất đặc trưng (C-TF-IDF):** Tìm ra tập hợp các từ khóa quan trọng nhất đại diện cho mỗi cụm.

### 3. Mô hình Lai (Hybrid Approach) với LLM (GPT)
Dự án không chỉ dùng BERTopic thuần túy mà kết hợp nó với GPT để tối ưu kết quả:
- **Đặt tên chủ đề (Labeling):** BERTopic cung cấp các từ khóa thô (ví dụ: "thuế", "doanh_nghiệp", "ưu_đãi"), sau đó GPT sẽ dựa vào đó để đặt tên chủ đề tự nhiên hơn (ví dụ: "Chính sách ưu đãi thuế cho doanh nghiệp").
- **Xử lý nội dung ngắn:** Với các bài đăng ngắn (như status Facebook/TikTok), BERTopic thường phân cụm kém chính xác. Khi đó, hệ thống sẽ lấy tập hợp các chủ đề mà BERTopic đã tìm thấy, sau đó dùng GPT làm "trọng tài" để phân loại nội dung ngắn vào đúng chủ đề đó.

### 4. Theo dõi Xu hướng theo Thời gian (Dynamic Topic Modeling)
Hệ thống sử dụng tính năng **Topics Over Time** của BERTopic để:
- Phân tích xem một chủ đề (ví dụ: "Ô nhiễm không khí") tăng hay giảm tần suất xuất hiện theo từng tuần/tháng.
- Nhận diện các từ khóa của cùng một chủ đề thay đổi thế nào theo thời gian.

### 5. Lưu trữ và Quản trị (Knowledge Management)
Kết quả từ BERTopic không chỉ để xem một lần mà được "vật chất hóa" vào Database:
- **Lưu Session:** Mỗi lần chạy train BERTopic được lưu thành một phiên (Session) để có thể so sánh hiệu quả.
- **Ánh xạ bài viết:** Lưu chính xác một bài viết thuộc về chủ đề nào với độ tin cậy (Probability) là bao nhiêu.
- **Xử lý nhiễu (Outliers):** BERTopic tự động lọc ra các bài viết không thuộc bất kỳ chủ đề rõ ràng nào (Topic -1) để đảm bảo chất lượng dữ liệu thống kê.

### Tóm tắt các File quan trọng liên quan:
*   [model.py](file:///home/ai_team/lab/pipeline_mxh/fastapi-base/app/services/topic/model.py): Cấu hình chính cho class `TopicModel` bao gồm UMAP, HDBSCAN và Vectorizer.
*   [bertopic_trainer.py](file:///home/ai_team/lab/pipeline_mxh/fastapi-base/app/services/topic/bertopic_trainer.py): Service điều phối việc lấy dữ liệu từ DB, train mô hình và lưu kết quả.
*   [hybrid_topic_classifier.py](file:///home/ai_team/lab/pipeline_mxh/fastapi-base/app/services/topic/hybrid_topic_classifier.py): Logic kết hợp BERTopic (cho nội dung dài) và GPT (cho nội dung ngắn).