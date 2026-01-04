from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

API_DOCS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Pipeline API Documentation</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
        .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .method { font-weight: bold; padding: 5px 10px; border-radius: 3px; color: white; }
        .post { background: #49cc90; }
        .get { background: #61affe; }
        code { background: #eee; padding: 2px 5px; border-radius: 3px; }
        pre { background: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>Pipeline API Documentation</h1>
    
    <h2>Base URL</h2>
    <p><code>http://localhost:8001/api</code></p>
    
    <h2>Crawl Endpoints</h2>
    
    <div class="endpoint">
        <span class="method post">POST</span> <code>/crawl</code>
        <p>Crawl data from various sources (web, rss, file, api)</p>
        <pre>{
  "source_type": "web",
  "source": "https://example.com",
  "clean": true,
  "dedupe": true
}</pre>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span> <code>/crawl/status</code>
        <p>Check crawler status and available sources</p>
    </div>
    
    <h2>Topic Modeling Endpoints</h2>
    
    <div class="endpoint">
        <span class="method post">POST</span> <code>/topics/fit</code>
        <p>Fit BERTopic model on documents</p>
        <pre>{
  "documents": ["text 1", "text 2", ...],
  "min_topic_size": 10,
  "save_model": true,
  "model_name": "my_model"
}</pre>
    </div>
    
    <div class="endpoint">
        <span class="method post">POST</span> <code>/topics/transform</code>
        <p>Transform documents using existing model</p>
        <pre>{
  "documents": ["new text 1", "new text 2"],
  "model_name": "my_model"
}</pre>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span> <code>/topics</code>
        <p>Get all topics with keywords and counts</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span> <code>/topics/{topic_id}</code>
        <p>Get detailed info about specific topic</p>
    </div>
    
    <div class="endpoint">
        <span class="method post">POST</span> <code>/search</code>
        <p>Semantic search using FAISS</p>
        <pre>{
  "query": "your search query",
  "k": 10
}</pre>
    </div>
    
    <h2>Examples</h2>
    
    <h3>1. Crawl Web Page</h3>
    <pre>curl -X POST "http://localhost:8001/api/crawl" \\
  -H "Content-Type: application/json" \\
  -d '{"source_type": "web", "source": "https://example.com"}'</pre>
    
    <h3>2. Fit Topic Model</h3>
    <pre>curl -X POST "http://localhost:8001/api/topics/fit" \\
  -H "Content-Type: application/json" \\
  -d '{"documents": ["text 1", "text 2"], "min_topic_size": 5}'</pre>
    
    <h3>3. Search Documents</h3>
    <pre>curl -X POST "http://localhost:8001/api/search" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "machine learning", "k": 10}'</pre>
    
    <h2>🔗 Links</h2>
    <ul>
        <li><a href="/docs">Swagger UI</a></li>
        <li><a href="/redoc">ReDoc</a></li>
    </ul>
</body>
</html>
"""


@router.get("/docs/pipeline", response_class=HTMLResponse)
async def get_pipeline_docs():
    return API_DOCS_HTML
