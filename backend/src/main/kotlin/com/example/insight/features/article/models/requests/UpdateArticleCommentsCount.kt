package com.example.insight.features.article.models.requests

import java.sql.Timestamp

data class UpdateArticleCommentsCount (
    val userId: Long,
    val commentId: Long,
    val action: String,
    val commentPostedAt: Timestamp?
)