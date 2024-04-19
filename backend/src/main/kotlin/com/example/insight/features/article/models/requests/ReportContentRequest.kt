package com.example.insight.features.article.models.requests

import com.example.insight.features.article.utils.ArticleConstants

data class ReportContentRequest(
        val reasonId: Int,
        val contentType: ArticleConstants.AppContentType,
        val details: String?
)
