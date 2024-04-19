package com.example.insight.features.userAuthentication.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse

class UserSignUpOrLoginResponse(
    val userId: Long,
    val authToken: String,
    val isNewUser: Boolean,
    val userName: String?,
    val userEmail: String?,
    val onboardingStatus: OnboardingStatus,
    override val message: String = ApiMessages.Common.success200
) : CommonResponse {
    data class OnboardingStatus(
        val isCompleted: Boolean,
        val stepsCompleted: OnboardingStepsStatus
    )
    data class OnboardingStepsStatus(
        val userName: Boolean,
        val preferences: Boolean
    )
}