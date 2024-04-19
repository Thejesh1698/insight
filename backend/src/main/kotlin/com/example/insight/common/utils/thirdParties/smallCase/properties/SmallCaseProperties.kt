package com.example.insight.common.utils.thirdParties.smallCase.properties

import org.springframework.boot.context.properties.ConfigurationProperties

@ConfigurationProperties(prefix = "smallcase")
data class SmallCaseProperties(
    val secret: String,
    val apiGatewaySecret: String,
    val serverBaseUrl: String,
)