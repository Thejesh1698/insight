package com.example.insight.features.userAuthentication.models.requests

data class UserSignUpOrLoginRequest(
    val mobileNumber: String,
    val otp: Long
)