package com.example.insight.common.models.responses

import com.example.insight.common.constants.ApiMessages

data class SuccessResponse(
    override var message: String = ApiMessages.Common.success200
) : CommonResponse