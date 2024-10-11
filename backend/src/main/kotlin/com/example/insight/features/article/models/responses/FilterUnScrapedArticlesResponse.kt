package com.example.insight.features.article.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse

class FilterUnScrapedArticlesResponse(
    val urls: List<String>,
    override val message: String = ApiMessages.Common.success200
) : CommonResponse