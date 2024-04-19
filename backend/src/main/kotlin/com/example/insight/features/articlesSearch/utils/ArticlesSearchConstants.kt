package com.example.insight.features.articlesSearch.utils

object ArticlesSearchConstants {
    enum class ArticlesSearchSortBy {
        RELEVANCE, PUBLISHED_TIME
    }

    const val ARTICLES_PER_PAGE = 10
    const val MAX_ARTICLES_PER_QUERY = 100
    const val MAX_SEARCH_QUERY_LENGTH = 140

    val INVALID_CHARS_FOR_SEARCH_QUERY = Regex("[^a-zA-Z0-9 ,.?!']+")
}