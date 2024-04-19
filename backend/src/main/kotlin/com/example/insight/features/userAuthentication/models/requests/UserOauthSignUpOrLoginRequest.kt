package com.example.insight.features.userAuthentication.models.requests

import com.example.insight.features.userAuthentication.utils.UserAuthenticationConstants

data class UserOauthSignUpOrLoginRequest(
    val accessToken: String,
    val oauthType: UserAuthenticationConstants.OauthTypes,
    val userEmail: String? = null,
    val userName: String? = null
)