package com.example.insight.common.utils.thirdParties.google.properties

import org.springframework.boot.context.properties.ConfigurationProperties

@ConfigurationProperties(prefix = "google")
data class GoogleProperties(
    val oauth: OauthProperties
) {
    data class OauthProperties(
        val clientId: String,
    )
}