package com.example.insight.features.user.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.entities.ArticleTopic
import com.example.insight.common.models.responses.CommonResponse

data class UserInterestedTopicsResponse(
    val topics: List<ArticleTopic>, override val message: String = ApiMessages.Common.success200
) : CommonResponse