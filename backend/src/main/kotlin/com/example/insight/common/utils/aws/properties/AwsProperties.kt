package com.example.insight.common.utils.aws.properties

import org.springframework.boot.context.properties.ConfigurationProperties

@ConfigurationProperties(prefix = "aws")
data class AwsProperties(
    val authentication: AuthenticationProperties,
    val sqs: SQSProperties
) {
    data class AuthenticationProperties(
        val accessKey: String,
        val secretKey: String
    )
    data class SQSProperties(
        val region: String
    )
}