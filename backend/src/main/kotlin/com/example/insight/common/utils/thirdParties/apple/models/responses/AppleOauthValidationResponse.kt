package com.example.insight.common.utils.thirdParties.apple.models.responses

import com.example.insight.features.userAuthentication.models.OauthCommonResponseInterface

data class AppleOauthValidationResponse(
    override val userEmail: String,
    override val userName: String?
): OauthCommonResponseInterface
