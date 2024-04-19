package com.example.insight.features.article.models.requests

import org.bson.types.ObjectId

data class InsertArticleRequest(
    val url: String,
    val source: String,
    val categoryName: String? = null,
    val title: String? = null,
    val shortDescription: String? = null,
    val publishedTime: String? = null,
    val lastUpdatedTime: String? = null,
    val tags: ArrayList<String>? = null,
    val articleImage: String? = null,
    val authors: List<String> = listOf(),
    val isPremiumArticle: Boolean? = null
) {
    lateinit var sourceId: ObjectId
}