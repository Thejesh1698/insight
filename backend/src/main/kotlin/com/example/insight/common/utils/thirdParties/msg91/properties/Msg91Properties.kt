package com.example.insight.common.utils.thirdParties.msg91.properties

import org.springframework.boot.context.properties.ConfigurationProperties

@ConfigurationProperties(prefix = "msg91")
data class Msg91Properties(
    val serverBaseUrl: String,
    val templates: Templates,
    val authentication: AuthenticationProperties
) {
    data class AuthenticationProperties(
        val authKey: String
    )
    data class Templates(
        val otpService: String
    )
}