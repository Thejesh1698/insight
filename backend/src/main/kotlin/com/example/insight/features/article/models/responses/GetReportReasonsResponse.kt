package com.example.insight.features.article.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.entities.ReportReason
import com.example.insight.common.models.responses.CommonResponse

data class GetReportReasonsResponse(
        val reasons: List<ReportReason>, override val message: String = ApiMessages.Common.success200
): CommonResponse
