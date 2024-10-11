package com.example.insight.common.utils.thirdParties.kite.models.requests

import com.fasterxml.jackson.annotation.JsonProperty

data class KiteRefreshTokenRequest(
    @JsonProperty("api_key") val apiKey: String,
    @JsonProperty("refresh_token") val refreshToken: String,
    @JsonProperty("checksum") val checksum: String
)
