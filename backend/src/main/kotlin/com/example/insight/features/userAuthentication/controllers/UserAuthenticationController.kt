package com.example.insight.features.userAuthentication.controllers

import com.example.insight.common.models.responses.CommonResponse
import com.example.insight.common.models.responses.SuccessResponse
import com.example.insight.features.userAuthentication.models.requests.GenerateOrResendOtpRequest
import com.example.insight.features.userAuthentication.models.requests.UserOauthSignUpOrLoginRequest
import com.example.insight.features.userAuthentication.models.requests.UserSignUpOrLoginRequest
import com.example.insight.features.userAuthentication.models.responses.UserSignUpOrLoginResponse
import com.example.insight.features.userAuthentication.services.UserAuthenticationService
import jakarta.servlet.http.HttpServletRequest
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.validation.annotation.Validated
import org.springframework.web.bind.annotation.*

@RestController
@CrossOrigin(origins = ["http://localhost:8000"])
@Validated
class UserAuthenticationController {

    @Autowired
    lateinit var userAuthenticationService: UserAuthenticationService

    @PostMapping("/public/auth/generate-otp", produces = ["application/json"])
    fun generateOtp(
        @RequestBody request: GenerateOrResendOtpRequest
    ): ResponseEntity<CommonResponse> {

        val message = userAuthenticationService.generateOtp(
            request
        )

        return ResponseEntity(
            SuccessResponse(message), HttpStatus.OK
        )
    }

    @PostMapping("/public/auth/resend-otp", produces = ["application/json"])
    fun resendOtp(
        @RequestBody request: GenerateOrResendOtpRequest
    ): ResponseEntity<CommonResponse> {

        val message = userAuthenticationService.resendOtp(
            request
        )

        return ResponseEntity(
            SuccessResponse(message), HttpStatus.OK
        )
    }

    @PostMapping("/public/auth/signup-or-login", produces = ["application/json"])
    fun signUpOrLogin(
        @RequestBody request: UserSignUpOrLoginRequest
    ): ResponseEntity<UserSignUpOrLoginResponse> {

        val response = userAuthenticationService.signUpOrLogin(
            request
        )

        return ResponseEntity(
            response, HttpStatus.OK
        )
    }

    @DeleteMapping("/client/users/{userId}/auth/logout", produces = ["application/json"])
    fun logoutUser(
        request: HttpServletRequest,
        @PathVariable userId: Long,
        @RequestHeader("X-AUTH-TOKEN") authToken: String,
    ): ResponseEntity<CommonResponse> {

        userAuthenticationService.logoutUser(
            userId,
            authToken
        )

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }

    @PostMapping("/public/auth/oauth-signup-or-login", produces = ["application/json"])
    fun oauthSignUpOrLogin(
        @RequestBody request: UserOauthSignUpOrLoginRequest
    ): ResponseEntity<UserSignUpOrLoginResponse> {

        val response = userAuthenticationService.signUpOrLoginUsingOauth(
            request
        )

        return ResponseEntity(
            response, HttpStatus.OK
        )
    }
}