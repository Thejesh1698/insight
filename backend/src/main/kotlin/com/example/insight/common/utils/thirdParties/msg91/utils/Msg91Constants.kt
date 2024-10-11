package com.example.insight.common.utils.thirdParties.msg91.utils

import com.example.insight.common.errorHandler.ErrorTypes


object Msg91Constants {
    enum class ApiEndPoints(val value: String) {
        GENERATE_OTP("v5/otp"),
        VERIFY_OTP("v5/otp/verify"),
        RESEND_OTP("v5/otp/retry"),
    }

    const val otpExpiryTimeInMins = 10
    enum class OtpResendTypes(val value: String) {
        TEXT("text"),
    }

    val verifyOTPApiErrorResponses = hashMapOf<String, Pair<String, Any>>(
        "Mobile no. already verified" to Pair("Expired OTP. Please try again.", ErrorTypes.Http4xxErrors.Authentication.EXPIRED_OTP),
        "OTP expired" to Pair("Expired OTP. Please try again.", ErrorTypes.Http4xxErrors.Authentication.EXPIRED_OTP),
        "OTP empty or not numeric" to Pair("Wrong OTP. Please try again.", ErrorTypes.Http4xxErrors.Authentication.INVALID_OTP),
        "OTP not match" to Pair("Wrong OTP. Please try again.", ErrorTypes.Http4xxErrors.Authentication.INVALID_OTP),
        "Max limit reached for this otp verification" to Pair("Max tries reached. Please try again later.", ErrorTypes.Http4xxErrors.Authentication.OTP_VERIFY_TRIES_MAX_REACHED),
    )

    val otpGenerationApiErrorResponses = hashMapOf<String, Pair<String, Any>>(
        "OTP retry count maxed out" to Pair("Max retries reached. Please try again later.", ErrorTypes.Http4xxErrors.Authentication.OTP_RETRY_MAX_REACHED)
    )
}