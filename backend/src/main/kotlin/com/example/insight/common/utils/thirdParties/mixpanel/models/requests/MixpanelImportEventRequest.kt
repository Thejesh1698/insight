package com.example.insight.common.utils.thirdParties.mixpanel.models.requests

data class MixpanelImportEventRequest(
    val event: String,
    val properties: Map<String, Any?> = HashMap()
)