package com.example.insight.features.userAuthentication.utils

import java.time.Duration

object UserAuthenticationConstants {
    val authTokenTTLDifference: Duration = Duration.ofDays(180)

    enum class OauthTypes {
        GOOGLE, APPLE
    }

    enum class SignUpType(val mixpanelValue: String) {
        PHONE_NUMBER("Phone Number"),
        GOOGLE_OAUTH("Google Oauth"),
        APPLE_OAUTH("Apple Oauth")
    }
}