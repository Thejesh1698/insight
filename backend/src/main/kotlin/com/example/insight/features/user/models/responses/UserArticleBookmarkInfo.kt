package com.example.insight.features.user.models.responses

import com.example.insight.features.article.models.responses.ArticleInfoForUserResponse

data class UserArticleBookmarkInfo(
    val bookmarkId: Long,
    val articleInfo: ArticleInfoForUserResponse
)