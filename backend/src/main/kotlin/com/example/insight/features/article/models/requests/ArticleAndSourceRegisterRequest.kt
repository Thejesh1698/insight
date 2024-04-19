package com.example.insight.features.article.models.requests

import com.example.insight.features.article.utils.ArticleConstants
import org.bson.types.ObjectId

data class ArticleAndSourceRegisterRequest (
    val articles: List<InsertArticleWithSourceRequest>
)

data class InsertArticleWithSourceRequest(
        val url: String,
        val source: String,
        val sourceLogoURL: String? = ArticleConstants.SOURCE_DEFAULT_LOGO_URL,
        val categoryName: String? = null,
        val title: String?,
        val shortDescription: String? = null,
        val publishedTime: String?,
        val lastUpdatedTime: String? = null,
        val tags: ArrayList<String>? = null,
        val articleImage: String? = null,
        val authors: List<String> = listOf(),
        val cleanedText: String?
) {
    lateinit var sourceId: ObjectId
}