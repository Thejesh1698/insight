package com.example.insight.features.articlesSearch.models.requests

import com.example.insight.features.articlesSearch.utils.ArticlesSearchConstants

data class ArticlesSearchRequest (
    val searchQuery: String,
    val searchId: Long?,
    val page: Int,
    val sortBy: ArticlesSearchConstants.ArticlesSearchSortBy
)