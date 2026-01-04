from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class CrawlRequest(BaseModel):
    start_urls: List[str] = Field(..., description="List of URLs to start crawling")
    allowed_domains: Optional[List[str]] = Field(None, description="Allowed domains")
    allow_patterns: Optional[List[str]] = Field(None, description="URL patterns to allow")
    deny_patterns: Optional[List[str]] = Field(None, description="URL patterns to deny")
    max_pages: int = Field(100, description="Maximum pages to crawl")


class CrawlResponse(BaseModel):
    status: str
    output_file: str
    total_pages: int
    summary: Dict


class ETLRequest(BaseModel):
    input_file: str = Field(..., description="Raw data filename")
    min_length: int = Field(100, description="Minimum content length")
    remove_duplicates: bool = Field(True, description="Remove duplicate documents")


class ETLResponse(BaseModel):
    status: str
    output_file: str
    stats: Dict


class TopicAnalysisRequest(BaseModel):
    input_file: str = Field(..., description="Processed data filename")
    min_topic_size: int = Field(10, description="Minimum topic size")
    use_gpu: bool = Field(False, description="Use GPU acceleration")
    embedding_model: str = Field("all-MiniLM-L6-v2", description="Embedding model name")


class TopicAnalysisResponse(BaseModel):
    status: str
    output_file: str
    model_file: str
    stats: Dict


class TopicWord(BaseModel):
    word: str
    score: float


class Topic(BaseModel):
    topic_id: int
    count: int
    words: List[TopicWord]
    representative_docs: List[str]


class Document(BaseModel):
    doc_id: int
    topic_id: int
    url: Optional[str]
    title: Optional[str]
    content_preview: str


class TopicsResponse(BaseModel):
    topics: List[Topic]
    documents: List[Document]
