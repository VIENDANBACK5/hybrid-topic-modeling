# Pipeline MXH - AI-Powered News & Social Media Analysis System

**He thong phan tich tin tuc va mang xa hoi tu dong voi AI**: Trich xuat chuyen sau He thong Chi so Kinh te - Xa hoi (GRDP, CPI, PII, ...), Khai thac du lieu Da nen tang, Topic Modeling, va Truc quan hoa du lieu qua Apache Superset.

**Production-ready** voi Vietnamese BERTopic, Tich hop LLM, Smart Crawling va Bao mat SSO Keycloak.

---

## Tong quan

He thong backend hoan chinh duoc thiet ke phuc vu phan tich quan ly nha nuoc va kinh te xa hoi de:
- **Crawl & Data Ingestion**: Thu thap du lieu tu Bao chi, MXH (Facebook, TikTok, Threads) va Tai lieu van ban.
- **Xu ly ETL**: Dedupe thong minh (hash + semantic tokenizer tieng Viet).
- **Phan loai & Trich xuat 20+ Chi so Kinh te - Xa hoi**: GRDP, CPI, IIP, FDI, PII, Y te, Giao duc, An ninh, PAR Index, Tinh hinh xay dung Dang...
- **Phan tich chu de & Cam xuc**: BERTopic Vietnamese, Field Classification, Sentiment Analysis cho tung linh vuc chuyen sau.
- **Tim kiem khong gian vector (RAG)**: Chuc nang Hybrid Search ket hop BM25 + FAISS Vector.
- **Report & Dashboard**: Dong bo real-time voi nen tang Apache Superset.
- **Quan ly chi phi**: Theo doi chat che chi phi cho cac API LLM.

---

## Kien truc he thong

```
pipeline_mxh/
├── fastapi-base/                    # Main Application
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry
│   │   ├── api/                     # API Routers (Fetch, Process, Extract)
│   │   │   ├── data_fetch_*.py      # Fetchers tu Social & Document
│   │   │   ├── data_process_*.py    # Processors & Loaders
│   │   │   ├── api_cpi.py, api_grdp_detail.py... # Cac Indicator Router
│   │   │   ├── api_social_indicators.py           # Xa hoi & Doi song
│   │   │   ├── api_important_posts.py             # Loc bai viet trong tam
│   │   │   ├── routers/
│   │   │   │   ├── superset_sync.py  # Dong bo voi Superset
│   │   │   │   ├── topic_service.py  # Topic modeling
│   │   │   │   └── field_classification.py
│   │   ├── services/
│   │   │   ├── etl/                 # Text pipeline & Tokenizers
│   │   │   ├── topic/               # BERTopic / FAISS
│   │   │   ├── trends/, sentiment/  # AI Phan tich cam xuc & xu huong
│   │   │   ├── social_indicator_extractor.py  # Extractor x hoi
│   │   │   └── universal_economic_extractor.py # Extractor kinh te
│   │   ├── models/                  # Database Models (hon 30 models)
│   │   │   ├── model_economic_*.py  # Models Kinh te
│   │   │   ├── model_field_*.py     # Phan loai Field & Cam xuc
│   │   │   └── model_*.py           # Linh vuc giao duc, y te, PAR Index...
│   │   └── core/                    # Core, DB config, Keycloak Auth
│   ├── alembic/                     # Database migrations
│   └── docker-compose.yml
└── data/                            # Thu muc luu tru noi bo
```

---

## Quick Start

### 1. Cai dat

```bash
cd /home/ai_team/lab/pipeline_mxh/fastapi-base

# Cai dat dependencies
pip install -r requirements.txt
```

### 2. Cau hinh (Environment Variables)

```bash
# Database (Mac dinh dung PostgreSQL)
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/pipeline_db

# LLM APIs - Dung OpenRouter key (bat dau bang sk-or-v1-)
export OPENAI_API_KEY=sk-or-v1-your-openrouter-key

# API Auth & Keycloak (Optional)
export KEYCLOAK_SERVER_URL=https://sso.example.com/auth/
export KEYCLOAK_REALM=ai-realm
export KEYCLOAK_CLIENT_ID=fastapi-client
export KEYCLOAK_CLIENT_SECRET=your-secret
export KEYCLOAK_VERIFY=True
```

### 3. Khoi dong

```bash
# Development
uvicorn app.main:app --reload --port 8001

# Production Docker
docker-compose up -d
```

### 4. Truy cap

- **API Docs**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/re-docs
- *(Dashboard phan tich Data duoc hien thi ben phia ung dung Apache Superset)*

---

## Chi tiet API Endpoints

Du an hien bao gom rat nhieu endpoint xu ly du lieu phuc tap. Qua trinh refactor (gop tu 71 -> 30 endpoints) chia cau truc thanh cac nhom chinh:

### 1. Nhom Data Fetch & Process Pipeline

Chiu trach nhiem Cao, Thu thap va Lam Sach noi dung (ETL Data):
- `POST /api/fetch`: Unified endpoint lay data tu da nguon (Facebook, TikTok, Bao chi, Threads, Lap lich). Tham so dau vao cho phep chon target (`sources: ["facebook", "newspaper"]`).
- `POST /api/process`: Unified ETL endpoint thuc hien don dep ky tu thua (Text Cleaning), Hash-based & Semantic Deduplication, va Load len Database/Storage.
- `GET /api/fetch/status` va `GET /api/process/status`: Theo doi trang thai worker, thong luong, hang doi loi cua cum.

### 2. Nhom Economic & Social Indicators API

Nhom API trich xuat khong lo phuc vu thong tin quan ly nha nuoc (Phan ra lam nhieu Router Detail doc lap):
- `GET /api/v1/economic-indicators/`: Khai thac toan bo du lieu tong hop Kinh te.
- `POST /api/v1/economic-indicators/batch`: Import, fill-missing va generate analyses (hang loat).
- `GET/POST /api/v1/api_grdp_detail/*`: Ti trong va tong thu nhap quoc noi nen kinh te (GRDP).
- `GET/POST /api/v1/api_cpi/`, `/api/iip/`, `/api/api_fdi_detail/`: Quan ly cac chi so Tieu dung (CPI), San xuat Cong nghiep (IIP), Von Dau tu (FDI).
- Khoi Cong nghe - Giao duc: `/api/v1/digital_economy_detail`, `/api/v1/digital_transformation_detail`, `/api/v1/api_tvet_employment/`.
- Khoi Hanh chinh - Chinh sach: `/api/v1/api_par_index/` (PAR Index), `/api/v1/api_sipas/` (SIPAS), `/api/v1/api_xay_dung_dang/`.
- Khoi Xa hoi - Khac: `/api/api_social_indicators/`, `/api/api_culture_lifestyle/`, `/api/api_health_statistics/`, `/api/api_security/`, `/api/api_aqi/`.
- `/api/api_important_posts/`: Bo loc va quan tri rieng cac bai viet/canh bao dac biet quan trong.

### 3. Nhom Topic Service & LLM Extraction (Xu ly AI)

- `POST /topic-service/train`: Huan luyen & Fit model (ho tro ca Standard Mode hoac Hybrid Mode).
- `POST /topic-service/ingest`: Tiem them du lieu moi vao Model da huan luyen.
- `GET /topic-service/metadata`: Truy xuat cac nhom chu de (Topics), Categories, Distribution, va Recommendations.
- `POST /api/llm/*`: Endpoints chuyen sau, dieu huong cho AI trich xuat Keyword, phan lop.
- `/api/v1/field_classification/`: Tu dong gan nhan linh vuc chuyen mon cho thong tin raw.

### 4. Nhom Apache Superset Syncing & Utility

- `POST /superset/sync`: Endpoint trigger ep buoc dong bo Data Model moi nhat tu API qua Database phuc vu truc quan hoa tren giao dien Superset.
- `GET /superset/status`: Kiem tra trang thai dong ho Sync giua Backend va GUI Superset.

---

## Cac he thong tinh nang chinh (Core Features)

Du an la mot he sinh thai phan tich van ban khep kin tu khau thu thap den hien thi truc quan. Duoi day la 7 nhom tinh nang cot loi:

### 1. He thong Thu thap Du lieu Da nen tang (Smart Crawling)

Thu thap tu dong du lieu tu nhieu nguon khac nhau de lam dau vao cho bai toan phan tich:
- Nguon Bao chi & Trang tin tuc dien tu (News).
- Nguon Mang xa hoi chuyen sau: Facebook, TikTok, Threads.
- Van ban / Tai lieu (Internal Documents).
- **Smart Selection:** Chu dong loai bo cac bai rac ngay tu cong crawl thong qua heuristic de giam tai he thong.

### 2. Quy trinh Xu ly & Lam sach (ETL Pipeline)

Du lieu tho sau khi thu thap se duoc di qua "mang loc" 2 lop:
- Lam sach ky tu dac biet, HTML, chuan hoa bo tieng Viet thong qua Pyvi/Underthesea.
- **De-duplication (Loai Bai Trung Lap):**
  - Lop 1 (MD5+Simhash): Bat cac bai copy 100% y het nhau.
  - Lop 2 (Semantic Vector Search): Bat cac bai "xao nau, viet lai ngu nghia" de loai bo.

### 3. Phan loai Dinh huong & Phan tich Cam xuc (Classification & Sentiment)

- **Field Classification (Phan loai Linh vuc):** Bai bao lap tuc duoc phan loai thuoc mang Y te, Giao duc, Chinh tri hay Kinh te vi mo.
- **Field Sentiment Analysis:** AI cham diem cam xuc du luan (Tich cuc, Tieu cuc, Trung lap) doi voi tung su kien cu the.
- **Topic Modeling (BERTopic):** Tu dong phat hien cac chu de dang nong (Trending Topics), cho cau hinh Custom Topics bang tieng Viet.

### 4. He sinh thai Trich xuat Chi so Kinh te - Xa hoi (20+ Chi so Vi mo)

Day la bo phan "Core Business" cuc lon, boc tach 27 Bang du lieu so de thong ke tu dong:
- **Khoi Kinh Te:** Trich xuat GDP/GRDP, CPI (Chi so gia tieu dung), IIP, San luong XNK, Von FDI.
- **Khoi Cong nghe & Khac:** PII (Doi moi sang tao), Phat trien Kinh te so, Y te, Thi THPT/Hoc nghe, O nhiem (AQI).
- **Khoi Hanh Chinh & Chinh Tri:** So lieu PAR Index, SIPAS (Do hai long), Bau cu can bo Dang, va bai viet rui ro an ninh mang.

### 5. Co che LLM Trich xuat So lieu (OpenRouter Architecture)

#### Tai sao can kien truc nay?

Neu dung LLM tu do sinh ra so lieu kinh te, mo hinh co the bia so (Hallucination). Trong he thong quan ly nha nuoc, sai lam nay la khong chap nhan duoc. Do do, he thong to chuc mot quy trinh lai cu ky chat khe:

```
Bai viet DB
  → Buoc 1: Pre-filter bang URL/Title (Regex, chua dung LLM)
  → Buoc 2: LLM Classifier xac nhan boi canh (chi tra loi YES/NO dang JSON)
  → Buoc 3: Regex Value Extractor lay so tu van ban goc
  → Buoc 4: Pydantic Validator kiem tra range cho phep
  → Luu vao DB
```

#### Chi tiet tung buoc:

**Buoc 1 – Pre-filter bang URL va Tieu de (khong dung LLM)**

Truoc khi goi LLM, he thong dung danh sach pattern cung de so loc nhanh:
- Neu URL bai chua tu khoa nhu `bien-che`, `can-bo`, `tai-nan-giao-thong` → bai duoc danh dau la ung vien.
- Neu tieu de chua tu khoa nhu "bien che", "TNGT", "tot nghiep THPT" → tuong tu.
- Muc dich: Loai bo ~95% bai khong lien quan truoc khi ton chi phi goi API LLM.

**Buoc 2 – LLM Classifier: Xac nhan boi canh (CHI tra loi Yes/No)**

- Neu bai vuot Pre-filter, LLM duoc goi qua OpenRouter voi `gpt-4o-mini`.
- Key OpenRouter (`sk-or-v1-...`) → he thong tu nhan dien va route qua `https://openrouter.ai/api/v1`.
- Key OpenAI thuong (`sk-...`) → goi thang OpenAI API.
- Prompt gui den LLM cuc ky chat, chi cho phep tra loi dang JSON:

```json
{"is_relevant": true, "relevant_indicators": ["cadre_statistics"], "confidence": 0.9}
```

- LLM khong duoc extract so, khong duoc dich, khong duoc tom tat. Chi tra loi bai nay CO hay KHONG lien quan den chi so X.

**Buoc 3 – Regex Value Extractor: Lay so tu van ban goc**

Sau khi LLM xac nhan bai lien quan den chi so nao, Regex moi chay de extract gia tri. Moi linh vuc co bo Regex rieng, vi du:
- So can bo bien che: pattern tim "tong so ... N nguoi/bien che" trong doan van co context cap tinh/huyen/xa.
- Ti le tot nghiep THPT: pattern lay phan tram trong khoang [70%, 100%] trong cau co "ty le do/tot nghiep".
- So vu tai nan giao thong: pattern tim so luong "M vu tai nan/TNGT" bat buoc co context "toan tinh/dia ban".
- Tinh Hung Yen duoc hard-code, khong auto-detect de tranh nham du lieu toan quoc.

**Buoc 4 – Pydantic Validation: Kiem tra Range**

So lieu qua Regex duoc kiem tra chat che truoc khi luu:
- Ti le phan tram: phai nam trong [0, 100].
- So giuong benh/10.000 dan: phai trong [1, 100].
- So thi sinh: phai tu 5.000 den 35.000 (phu hop quy mo Hung Yen).
- Du lieu khong hop le → bo qua (NULL), khong duoc ghi DB.

#### Danh sach 11 linh vuc LLM Extraction:

Moi linh vuc co 2 che do goi API:
- **Async** (`POST /api/llm/extract-{linh-vuc}`): Tra ve ngay `202 Accepted`, job chay nen. Dung khi batch lon.
- **Sync** (`POST /api/llm/extract-{linh-vuc}/sync`): Cho hoan thanh, tra ve ket qua. Dung khi debug hoac can du lieu ngay.

| STT | Linh vuc | Endpoint | Bang DB | Chi so trich xuat chinh |
|-----|----------|----------|---------|------------------------|
| 1 | Xay dung Dang & He thong chinh tri | `/api/llm/extract-politics` | `xay_dung_dang` | Tong so bien che, phan cap tinh/huyen/xa, hop dong |
| 2 | Y te & Cham soc suc khoe | `/api/llm/extract-medical` | `health_statistics` | Ti le bao phu BHYT, so nguoi tham gia, ti le tang dan so, giuong benh/van dan |
| 3 | Giao duc & Dao tao | `/api/llm/extract-education` | `highschool_graduation`, `tvet_employment` | Ti le tot nghiep THPT, tong thi sinh du thi, diem trung binh, ti le biet chu, ti le co viec lam sau hoc nghe |
| 4 | An ninh - Trat tu | `/api/llm/extract-security` | `security` | So vu ma tuy, so doi tuong bi bat, so vu vi pham nong do con, ti le giam toi pham |
| 5 | Van hoa - Xa hoi | `/api/llm/extract-society` | `culture_lifestyle` | So di tich duoc quan ly, luot khach du lich, doanh thu du lich |
| 6 | Giao thong & An toan | `/api/llm/extract-transportation` | `transportation` | So vu TNGT, so nguoi tu vong/bi thuong, ti le giam tai nan |
| 7 | Thong ke Kinh te & Chinh tri | `/api/llm/extract-statistics` | `economic_statistics`, `political_statistics` | Tong hop cac chi so tai khoa va chinh tri tu bao cao quan trong |
| 8 | Kinh te so | `/api/llm/extract-digital-economy` | `digital_economy_detail` | Ti le DN so hoa, doanh thu kinh te so, ha tang vien thong |
| 9 | Thu hut FDI | `/api/llm/extract-fdi` | `fdi_detail` | Von dang ky, so du an, tong von giai ngan, thi truong dau tu |
| 10 | Chuyen doi so | `/api/llm/extract-digital-transformation` | `digital_transformation_detail` | So dich vu cong truc tuyen, ti le xu ly ho so online, chi so DTI |
| 11 | PII - Doi moi sang tao | `/api/llm/extract-pii` | `pii_detail` | Chi so nang luc doi moi sang tao cap tinh (PII), xep hang so sanh |

### 6. He thong Hoi-Dap & Tra cuu (Hybrid RAG Search)

- Su dung Vietnamese Embeddings nen du lieu thanh vector. Luu vao thu vien FAISS va truy van hon hop (FAISS Semantic + BM25 Keywords) de dam bao khong rot tu khoa khi Bot AI tra loi cau hoi.

### 7. Bang dieu khien Truc quan (Apache Superset Dashboard)

- Tich hop thang Data Visualization Enterprise cua platform **Apache Superset**.
- So huu endpoint `POST /superset/sync` tu dong day du lieu (Data Warehouse) ve Superset de len bieu do ngay lap tuc.

---

## Quan ly Ngan sach (API LLM)

- **Workflow Routing thong minh:** Phan loai va cham diem News/Social Posts truoc, chi nhung articles chat luong/quan trong cao moi duoc gui qua mo hinh LLM cao cap xu ly.
- Theo doi log tieu thu va budget hang ngay, tranh vuot muc chi phi OpenAI/Gemini Tokens cho he thong Enterprise.

---

## Security & Phan quyen

- He thong ho tro tich hop voi kien truc **Keycloak SSO OpenID**.
- Tang Data Isolation chan SQL injection nho ORM SQLAlchemy.
- Phan quyen theo Access Token Scopes.

---

## TroubleShooting

1. **Loi database khong ket noi:**
   - He thong dung PostgreSQL o production. Chac chan set `DATABASE_URL` dung dang.
2. **Keycloak config rong / khong start duoc Server:**
   - Hay chac chan cac bien `KEYCLOAK_SERVER_URL` cung config lien quan deu valid o file `.env` truoc khi start uvicorn.
3. **LLM khong goi duoc:**
   - Kiem tra `OPENAI_API_KEY`. Key OpenRouter bat dau bang `sk-or-v1-`, key OpenAI thuong bat dau bang `sk-`.

---

## Doi ngu

AI Team - Lab Pipeline MXH

**Last Updated**: April 2026
