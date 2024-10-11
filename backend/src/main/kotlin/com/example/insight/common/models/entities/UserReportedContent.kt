package com.example.insight.common.models.entities

import com.example.insight.features.article.utils.ArticleConstants

data class UserReportedContent(
        val userId: Long,
        val contentId: String,
        val contentType: ArticleConstants.AppContentType,
        val reasonId: Int,
        val details: String?
)
