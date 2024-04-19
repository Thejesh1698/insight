package com.example.insight.features.article.models.requests

data class ArticleReactionCountUpdateMessage (
    val reactionId: Long,
    val userId: Long,
    val articleId: String,
    val action: String
)