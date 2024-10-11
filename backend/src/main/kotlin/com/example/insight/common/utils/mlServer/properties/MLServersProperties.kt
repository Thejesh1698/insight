package com.example.insight.common.utils.mlServer.properties

import org.springframework.boot.context.properties.ConfigurationProperties

@ConfigurationProperties(prefix = "ml-servers")
data class MLServersProperties(
    val cambrianServer: CambrianServerProperties,
    val hubbleServer: HubbleServerProperties
) {
    data class CambrianServerProperties(
        val serverBaseUrl: String
    )
    data class HubbleServerProperties(
        val serverBaseUrl: String
    )
}