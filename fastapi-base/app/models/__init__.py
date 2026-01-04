from app.models.model_base import Base
from app.models.model_article import Article
from app.models.model_sentiment import SentimentAnalysis
from app.models.model_custom_topic import (
    CustomTopic,
    ArticleCustomTopic,
    TopicClassificationLog,
    TopicTemplate
)
from app.models.model_bertopic_discovered import (
    BertopicDiscoveredTopic,
    ArticleBertopicTopic,
    TopicTrainingSession
)
from app.models.model_statistics import (
    TrendReport,
    HotTopic,
    KeywordStats,
    TopicMentionStats,
    WebsiteActivityStats,
    SocialActivityStats,
    DailySnapshot
)
from app.models.model_trends import (
    TrendAlert,
    HashtagStats,
    ViralContent,
    CategoryTrendStats
)

# Archived: model_user, model_crawl_history, model_source
