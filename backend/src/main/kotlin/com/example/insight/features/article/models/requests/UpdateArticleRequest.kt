package com.example.insight.features.article.models.requests

data class UpdateArticleRequest(
    val title: String,
    val shortDescription: String? = null,
    val publishedTime: String,
    val lastUpdatedTime: String? = null,
    val tags: ArrayList<String>? = null,
    val articleImage: String? = null,
    val authors: List<String> = listOf(),
    val isPremiumArticle: Boolean? = null,
    val cleanedText: String? = null
)