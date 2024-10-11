package com.example.insight.common.utils.thirdParties.google.models.responses

import com.example.insight.features.userAuthentication.models.OauthCommonResponseInterface

data class GoogleOauthValidationResponse(
    override val userEmail: String,
    override val userName: String?,
    val googleUserId: String
): OauthCommonResponseInterface
