package com.example.insight.features.user.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse

data class UserArticleReadingHistoryResponse (
    val readingHistory: List<UserArticleReadingHistoryInfo>,
    val cursor: Long?,
    override val message: String = ApiMessages.Common.success200
): CommonResponse