package com.example.insight.features.user.models.responses

import com.example.insight.features.article.models.responses.ArticleInfoForUserResponse

data class UserArticleReadingHistoryInfo(
    val historyId: Long,
    val articleInfo: ArticleInfoForUserResponse
)