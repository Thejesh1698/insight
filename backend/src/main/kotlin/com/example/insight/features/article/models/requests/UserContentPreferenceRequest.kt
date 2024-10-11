package com.example.insight.features.article.models.requests

import com.example.insight.features.article.utils.ArticleConstants

data class UserContentPreferenceRequest(
        val contentType: ArticleConstants.AppContentType,
        val preferenceType: ArticleConstants.PreferenceType,
        val value: Boolean
)