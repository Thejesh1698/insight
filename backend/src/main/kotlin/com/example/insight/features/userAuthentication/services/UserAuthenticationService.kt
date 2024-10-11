package com.example.insight.features.userAuthentication.services

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.errorHandler.ErrorTypes
import com.example.insight.common.errorHandler.exceptions.BadRequestException
import com.example.insight.common.errorHandler.exceptions.UnauthorizedException
import com.example.insight.common.models.entities.User
import com.example.insight.common.utils.isMobileNumberValid
import com.example.insight.common.utils.thirdParties.apple.services.AppleService
import com.example.insight.common.utils.thirdParties.google.services.GoogleService
import com.example.insight.common.utils.thirdParties.msg91.services.Msg91Service
import com.example.insight.features.eventsManager.models.Event
import com.example.insight.features.eventsManager.services.EventsManagerService
import com.example.insight.features.eventsManager.utils.EventConstants
import com.example.insight.features.userAuthentication.models.requests.GenerateOrResendOtpRequest
import com.example.insight.features.userAuthentication.models.responses.UserSignUpOrLoginResponse
import com.example.insight.features.userAuthentication.repositories.UserAuthenticationRepository
import com.example.insight.features.userAuthentication.utils.UserAuthenticationConstants
import com.example.insight.features.user.services.UserService
import com.example.insight.features.userAuthentication.models.requests.UserOauthSignUpOrLoginRequest
import com.example.insight.features.userAuthentication.models.requests.UserSignUpOrLoginRequest
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.security.SecureRandom
import java.time.Instant
import java.util.*

@Service
class UserAuthenticationService {

    @Autowired
    lateinit var userAuthenticationRepository: UserAuthenticationRepository

    @Autowired
    lateinit var userService: UserService

    @Autowired
    lateinit var msg91Service: Msg91Service

    @Autowired
    lateinit var eventsManagerService: EventsManagerService

    @Autowired
    lateinit var googleService: GoogleService

    @Autowired
    lateinit var appleService: AppleService

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    fun generateOtp(request: GenerateOrResendOtpRequest): String {

        if(!isMobileNumberValid(request.mobileNumber)) {
            logger.error("Invalid Mobile number. regex check failed! --- request: $request")
            throw BadRequestException(
                ErrorTypes.Http4xxErrors.Authentication.INVALID_MOBILE_NUMBER,
                ApiMessages.Authentication.invalidMobileNumber
            )
        }

        val response = msg91Service.generateOtp(request.mobileNumber)
        logger.info("OTP generated successfully! --- request: $request | response: $response")
        return ApiMessages.Authentication.otpGenerated
    }

    fun resendOtp(request: GenerateOrResendOtpRequest): String {

        if(!isMobileNumberValid(request.mobileNumber)) {
            logger.error("Invalid Mobile number. regex check failed! --- request: $request")
            throw BadRequestException(
                ErrorTypes.Http4xxErrors.Authentication.INVALID_MOBILE_NUMBER,
                ApiMessages.Authentication.invalidMobileNumber
            )
        }
        val response = msg91Service.resendOtp(request.mobileNumber)
        logger.info("OTP resent successfully! --- request: $request | response: $response")
        return ApiMessages.Authentication.otpResent
    }

    @Transactional("userDatabaseTransactionManager")
    fun signUpOrLogin(request: UserSignUpOrLoginRequest): UserSignUpOrLoginResponse {

        if(!isMobileNumberValid(request.mobileNumber)) {
            logger.error("Invalid Mobile number. regex check failed! --- request: $request")
            throw BadRequestException(
                ErrorTypes.Http4xxErrors.Authentication.INVALID_MOBILE_NUMBER,
                ApiMessages.Authentication.invalidMobileNumber
            )
        }

        val isOtpVerified = verifyOtp(request.mobileNumber, request.otp)
        if (!isOtpVerified) {
            logger.error("Invalid OTP. otp verification failed! --- request: $request")
            throw BadRequestException(
                ErrorTypes.Http4xxErrors.Authentication.INVALID_OTP,
                ApiMessages.Authentication.invalidOTP
            )
        }

        var isNewUser = false
        val user = userService.getUserByMobileNumber(request.mobileNumber) ?: run {
            isNewUser = true
            userService.insertUser(request.mobileNumber)
        }

        val signUpType = if(isNewUser) {
            UserAuthenticationConstants.SignUpType.PHONE_NUMBER
        } else {
            null
        }
        return assignAuthToken(user, isNewUser, signUpType?.mixpanelValue)
    }

    @Transactional("userDatabaseTransactionManager")
    fun signUpOrLoginUsingOauth(request: UserOauthSignUpOrLoginRequest): UserSignUpOrLoginResponse {

        val signUpOrLoginType: UserAuthenticationConstants.SignUpType
        val response = when(request.oauthType) {
            UserAuthenticationConstants.OauthTypes.GOOGLE -> {
                signUpOrLoginType =  UserAuthenticationConstants.SignUpType.GOOGLE_OAUTH
                googleService.validateTokenAndFetchUserDetails(request.accessToken, request.userEmail)
            }
            UserAuthenticationConstants.OauthTypes.APPLE -> {
                signUpOrLoginType =  UserAuthenticationConstants.SignUpType.APPLE_OAUTH
                appleService.validateTokenAndFetchUserDetails(request.accessToken, request.userEmail)
            }
        }

        var isNewUser = false
        val user = userService.getUserByEmail(response.userEmail) ?: run {
            isNewUser = true
            userService.insertUser(response.userEmail, response.userName ?: request.userName)
        }

        val signUpType = if(isNewUser) {
            signUpOrLoginType
        } else {
            null
        }
        return assignAuthToken(user, isNewUser, signUpType?.mixpanelValue)
    }

    fun verifyOtp(mobileNumber: String, otp: Long): Boolean {

        val response = msg91Service.verifyOtp(mobileNumber, otp)
        logger.info("OTP verified successfully! --- mobileNumber: $mobileNumber | otp: $otp | response: $response")
        return true
    }

    private fun generateSecureAuthToken(length: Int): String {

        //write your own logic to return a secure random alphanumeric auth token
        return ""
    }

    private fun getTtlForAuthToken(): Long {

        return Instant.now().epochSecond + UserAuthenticationConstants.authTokenTTLDifference.seconds
    }

    fun authenticateUser(authToken: String?, userId: Long?): User {

        if (authToken == null || userId == null) {
            logger.error("Unauthorised request, authToken or userId are null --- authToken: $authToken | userId: $userId")
            throw UnauthorizedException()
        }

        val (user, authTokenDetails) = userAuthenticationRepository.getAuthenticationDetails(authToken) ?: run {
            logger.error("Unauthorised request, authToken does not exist! --- authToken: $authToken")
            throw UnauthorizedException()
        }

        if (authTokenDetails.userId != userId) {
            logger.error("Unauthorised request, auth token and userId doesn't match --- authToken: $authToken | userId: $userId")
            throw UnauthorizedException()
        } else if (authTokenDetails.ttl < Instant.now().epochSecond) {
            userAuthenticationRepository.deleteAuthToken(userId, authToken)
            logger.error("Auth token expired! --- authToken: $authToken")
            throw UnauthorizedException(
                ErrorTypes.Http4xxErrors.Authentication.EXPIRED_AUTH_TOKEN,
                ApiMessages.Authentication.expiredAuthToken
            )
        }

        return user
    }

    fun logoutUser(userId: Long, authToken: String) {

        val isAuthTokenDeleted = userAuthenticationRepository.deleteAuthToken(userId, authToken)
        if (!isAuthTokenDeleted) {
            logger.error("Auth token expired! --- authToken: $authToken")
            throw UnauthorizedException()
        }
    }

    private fun assignAuthToken(user: User, isNewUser: Boolean, signUpType: String?): UserSignUpOrLoginResponse {

        val authToken = generateSecureAuthToken(16)
        val ttl = getTtlForAuthToken()

        userAuthenticationRepository.insertAuthToken(authToken, user.userId, ttl)
        val onboardingDetails = userService.getUserOnboardingStatus(user)

        val eventProperties = hashMapOf<EventConstants.EventPropertyKeys, Any?>(
            EventConstants.EventPropertyKeys.VENDOR_KEY_DISTINCT_ID to user.userId.toString(),
            EventConstants.EventPropertyKeys.USER_ID to user.userId,
            EventConstants.EventPropertyKeys.USER_NAME to user.userName,
            EventConstants.EventPropertyKeys.USER_PHONE_NUMBER to user.mobileNumber,
            EventConstants.EventPropertyKeys.USER_EMAIL to user.userEmail,
        )

        val userProperties = hashMapOf<EventConstants.UserPropertyKeys, Any?>(
            EventConstants.UserPropertyKeys.USER_ID to user.userId,
            EventConstants.UserPropertyKeys.USER_NAME to user.userName,
            EventConstants.UserPropertyKeys.USER_PHONE_NUMBER to user.mobileNumber,
            EventConstants.UserPropertyKeys.USER_EMAIL to user.userEmail,
            EventConstants.UserPropertyKeys.SIGN_UP_TYPE to signUpType,
        )
        val event = if(isNewUser) {
            Event(
                user.userId,
                Event.EventInfo(
                    EventConstants.EventNames.USER_SIGNUP,
                    eventProperties,
                    userProperties
                )
            )
        } else {
            Event(
                user.userId,
                Event.EventInfo(
                    EventConstants.EventNames.USER_LOGIN,
                    eventProperties,
                    userProperties
                )
            )
        }
        eventsManagerService.publishEvent(event)

        return UserSignUpOrLoginResponse(
            userId = user.userId,
            authToken = authToken,
            isNewUser,
            user.userName,
            user.userEmail,
            onboardingDetails
        )
    }
}