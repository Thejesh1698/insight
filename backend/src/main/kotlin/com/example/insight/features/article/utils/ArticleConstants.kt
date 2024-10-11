package com.example.insight.features.article.utils

object ArticleConstants {
    const val AI_GENERATED_INFO_MODEL = "<add-your-ai-model-name-here>"
    enum class ContentType {
        ARTICLE, PODCAST_EPISODE
    }
    enum class SourceType {
        ARTICLE, PODCAST
    }
    enum class PreferenceType {
        NOT_INTERESTED,
        SHOW_MORE_LIKE_THIS
    }
    enum class AppContentType {
        ARTICLE,PODCAST_EPISODE,PODCAST
    }
    const val  REPORT_INTERVAL_IN_SECONDS = 3600
    const val MAX_REPORTS_LIMIT = 5
    const val REPORT_REASON_MAX_CHARACTER_LIMIT = 3000

    enum class ContentSummaryValueTypes {
        STRING, JSON, HTML
    }

    val MODELS_WITH_HTML_SUMMARY_FORMAT = arrayListOf(
        "<add-your-ai-model-name-here>"
    )

    val MODELS_WITH_STRING_SUMMARY_FORMAT = arrayListOf(
        "<add-your-ai-model-name-here>"
    )

    enum class SourceMedium {
        WEB_SEARCH,
        WEB_SCRAPING
    }
    const val ARTICLE_CLEAN_TEXT_LENGTH = 300

    const val SOURCE_DEFAULT_LOGO_URL = "<add-your-default-source-logo-url-here>"
}