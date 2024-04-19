package com.example.insight.common.utils.thirdParties.apple.properties

import org.springframework.boot.context.properties.ConfigurationProperties

@ConfigurationProperties(prefix = "apple")
data class AppleProperties(
    val oauth: OauthProperties,
) {
    data class OauthProperties(
        val clientId: String,
        val publicAuthKeysApi: String = "https://appleid.apple.com/auth/keys"
    )
}