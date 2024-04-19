package com.example.insight.common.configurations

import com.example.insight.common.utils.aws.properties.AwsProperties
import com.example.insight.common.utils.mlServer.properties.MLServersProperties
import com.example.insight.common.utils.thirdParties.apple.properties.AppleProperties
import com.example.insight.common.utils.thirdParties.google.properties.GoogleProperties
import com.example.insight.common.utils.thirdParties.smallCase.properties.SmallCaseProperties
import com.example.insight.common.utils.thirdParties.mixpanel.properties.MixpanelProperties
import com.example.insight.common.utils.thirdParties.msg91.properties.Msg91Properties
import org.springframework.boot.context.properties.EnableConfigurationProperties
import org.springframework.context.annotation.Configuration

/**
 * This class is to be used to read configuration from application properties.
 * Can help in eliminating cumbersome usage of @Value annotation
 * */
@Configuration
@EnableConfigurationProperties(
     AwsProperties::class,
     MLServersProperties::class,
     Msg91Properties::class,
     MixpanelProperties::class,
     GoogleProperties::class,
     AppleProperties::class,
     SmallCaseProperties::class
)
class AppConfiguration