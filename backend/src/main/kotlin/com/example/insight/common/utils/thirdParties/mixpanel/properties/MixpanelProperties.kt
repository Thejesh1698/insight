package com.example.insight.common.utils.thirdParties.mixpanel.properties

import org.springframework.boot.context.properties.ConfigurationProperties

@ConfigurationProperties(prefix = "mixpanel")
data class MixpanelProperties(
    val domainUrl: String,
    val userName: String,
    val password: String,
    val projectId: String,
    val projectToken: String
)