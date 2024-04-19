package com.example.insight.features.article.models.responses


data class ArticleInformationResponse(
    val articleId: String,
    val url: String,
    val title: String? = null,
    val shortDescription: String? = null,
    val publishedTime: String? = null,
    val lastUpdatedTime: String? = null,
    val tags: ArrayList<String>?,
    val articleImageUrl: String?,
    val category: String?,
    val authors: List<String>,
    val isPremiumArticle: Boolean?,
    val source: ArticleSourceInformation? = null
) {
    data class ArticleSourceInformation(
        val sourceId: String,
        val sourceName: String,
        val sourceLogo: String
    )
}