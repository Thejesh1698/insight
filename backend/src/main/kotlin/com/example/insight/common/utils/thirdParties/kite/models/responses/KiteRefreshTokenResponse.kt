package com.example.insight.common.utils.thirdParties.kite.models.responses

import com.fasterxml.jackson.annotation.JsonIgnoreProperties
import com.fasterxml.jackson.annotation.JsonProperty

@JsonIgnoreProperties(ignoreUnknown = true)
data class KiteRefreshTokenResponse(
    val status: String, val data: KiteRefreshTokenData?
)

@JsonIgnoreProperties(ignoreUnknown = true)
data class KiteRefreshTokenData(
    @JsonProperty("access_token") val accessToken: String,
    @JsonProperty("refresh_token") val refreshToken: String
)
