package com.example.insight.features.footPrints.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse

data class ArticleVisibilityTrackingResponse (
    val errorRequests: ArrayList<HashMap<String, Any?>>,
    override val message: String = ApiMessages.Common.success200
): CommonResponse