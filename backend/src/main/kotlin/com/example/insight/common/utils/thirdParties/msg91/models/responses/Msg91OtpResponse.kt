package com.example.insight.common.utils.thirdParties.msg91.models.responses

import com.fasterxml.jackson.annotation.JsonProperty

data class Msg91OtpResponse(
    val type: String?,
    val message: String?,
    @JsonProperty("request_id")
    val requestId: String?
)