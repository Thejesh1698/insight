package com.example.insight.features.article.models.requests

data class UpdateArticleReactionCount (
    val userId: Long,
    val reactionId: Long,
    val action: String
)