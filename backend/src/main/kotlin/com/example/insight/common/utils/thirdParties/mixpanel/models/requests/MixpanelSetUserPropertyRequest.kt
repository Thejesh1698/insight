package com.example.insight.common.utils.thirdParties.mixpanel.models.requests

import com.fasterxml.jackson.annotation.JsonProperty

data class MixpanelSetUserPropertyRequest (
    @JsonProperty("\$token") var token: String = "",
    @JsonProperty("\$distinct_id") val distinctId: String,
    @JsonProperty("\$ip") val ip: String = "0",
    @JsonProperty("\$set") var properties: Map<String, Any?> = HashMap()
)