package com.example.insight.features.article.models.requests

import java.sql.Timestamp

data class ArticleCommentsCountUpdateMessage (
    val userId: Long,
    val articleId: String,
    val action: String,
    val commentPostedAt: Timestamp?,
    val commentId: Long
)