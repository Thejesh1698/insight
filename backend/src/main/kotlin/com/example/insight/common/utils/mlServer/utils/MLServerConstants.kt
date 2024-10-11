package com.example.insight.common.utils.mlServer.utils


object MLServerConstants {
    enum class ApiEndPoints(val value: String) {
        USER_FEED("get_feed"),
        ARTICLE_SEARCH("search_query"),
        WEB_SEARCH("search_query_web"),
        PORTFOLIO_SEARCH("search_query_portfolio")
    }
}