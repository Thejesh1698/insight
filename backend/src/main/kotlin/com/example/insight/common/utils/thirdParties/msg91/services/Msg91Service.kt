package com.example.insight.common.utils.thirdParties.msg91.services

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.errorHandler.ErrorTypes
import com.example.insight.common.errorHandler.exceptions.BadRequestException
import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.utils.thirdParties.msg91.models.responses.Msg91OtpResponse
import com.example.insight.common.utils.thirdParties.msg91.properties.Msg91Properties
import com.example.insight.common.utils.thirdParties.msg91.utils.Msg91Constants
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.http.*
import org.springframework.stereotype.Service
import org.springframework.web.client.RestTemplate
import org.springframework.web.util.UriComponentsBuilder
import java.util.*

@Service
class Msg91Service(val msg91Properties: Msg91Properties) {

    val objectMapper: ObjectMapper = ObjectMapper().registerModule(KotlinModule())

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    fun generateOtp(
        mobileNumber: String
    ): Msg91OtpResponse {

        val headers = HttpHeaders().apply {
            contentType = MediaType.APPLICATION_JSON
            accept = Collections.singletonList(MediaType.APPLICATION_JSON)
        }
        val requestPayload = HttpEntity<Any?>(headers)

        val endpoint = Msg91Constants.ApiEndPoints.GENERATE_OTP
        val apiUrl = "${msg91Properties.serverBaseUrl}/${endpoint.value}"

        // Set query parameters
        val queryParams = mapOf(
            "authkey" to msg91Properties.authentication.authKey,
            "template_id" to msg91Properties.templates.otpService,
            "mobile" to "91$mobileNumber",
            "otp_expiry" to Msg91Constants.otpExpiryTimeInMins,
        )
        val apiUri = UriComponentsBuilder.fromUriString(apiUrl)
            .apply { queryParams.forEach { queryParam(it.key, it.value) } }
            .build().toUri()

        val errorResponseHandler = Msg91ApiErrorResponseHandler(endpoint)

        RestTemplate().apply {
            errorHandler = errorResponseHandler

            val response = exchange(
                apiUri,
                HttpMethod.POST,
                requestPayload,
                String::class.java
            )

            return response.body?.let {
                val responseObject = objectMapper.readValue(it, Msg91OtpResponse::class.java)

                when (responseObject.type) {
                    "success" -> {
                        return responseObject
                    }

                    "error" -> {
                        logger.error("Error from msg91 --- mobileNumber: $mobileNumber | errorMessage: ${responseObject.message} | responseObject: $responseObject")
                        throw BadRequestException(
                            ErrorTypes.Http4xxErrors.Authentication.INVALID_MOBILE_NUMBER
                        )
                    }

                    else -> {
                        logger.error("Invalid response from msg91. Unrecognised responseObject.type --- mobileNumber: $mobileNumber | responseObject: $responseObject")
                        throw InternalServerErrorException(
                            message = ApiMessages.Common.vendorError,
                        )

                    }
                }
            } ?: throw errorResponseHandler.msg91ApiInternalServerException(
                null,
                endpoint.value,
                objectMapper.writeValueAsString(response),
                "response body cannot be null in MSG91 otp generation api response for mobileNumber: $mobileNumber"
            )
        }
    }

    fun verifyOtp(
        mobileNumber: String,
        otp: Long
    ): Msg91OtpResponse {

        val headers = HttpHeaders().apply {
            contentType = MediaType.APPLICATION_JSON
            accept = Collections.singletonList(MediaType.APPLICATION_JSON)
        }
        val requestPayload = HttpEntity<Any?>(headers)

        val endpoint = Msg91Constants.ApiEndPoints.VERIFY_OTP
        val apiUrl = "${msg91Properties.serverBaseUrl}/${endpoint.value}"

        // Set query parameters
        val queryParams = mapOf(
            "authkey" to msg91Properties.authentication.authKey,
            "mobile" to "91$mobileNumber",
            "otp" to otp,
        )
        val apiUri = UriComponentsBuilder.fromUriString(apiUrl)
            .apply { queryParams.forEach { queryParam(it.key, it.value) } }
            .build().toUri()

        val errorResponseHandler = Msg91ApiErrorResponseHandler(endpoint)

        RestTemplate().apply {
            errorHandler = errorResponseHandler

            val response = exchange(
                apiUri,
                HttpMethod.POST,
                requestPayload,
                String::class.java
            )

            return response.body?.let {
                val responseObject = objectMapper.readValue(it, Msg91OtpResponse::class.java)

                when (responseObject.type) {
                    "success" -> {
                        return responseObject
                    }

                    "error" -> {
                        val (formattedMessage, errorType) = Msg91Constants.verifyOTPApiErrorResponses[responseObject.message] ?: Pair(
                            ApiMessages.Common.error400, ErrorTypes.Http4xxErrors.BAD_REQUEST
                        )

                        logger.error("Error from msg91 --- mobileNumber: $mobileNumber | " +
                                "errorMessage: ${responseObject.message} | responseObject: $responseObject | otp: $otp")
                        throw BadRequestException(
                            errorType,
                            formattedMessage
                        )
                    }

                    else -> {
                        logger.error("Invalid response from msg91. Unrecognised responseObject.type --- " +
                                "mobileNumber: $mobileNumber | responseObject: $responseObject | otp: $otp")
                        throw InternalServerErrorException(
                            message = ApiMessages.Common.vendorError,
                        )

                    }
                }
            } ?: throw errorResponseHandler.msg91ApiInternalServerException(
                null,
                endpoint.value,
                objectMapper.writeValueAsString(response),
                "response body cannot be null in MSG91 otp generation api response for mobileNumber: $mobileNumber"
            )
        }
    }

    fun resendOtp(
        mobileNumber: String
    ): Msg91OtpResponse {

        val headers = HttpHeaders().apply {
            contentType = MediaType.APPLICATION_JSON
            accept = Collections.singletonList(MediaType.APPLICATION_JSON)
        }
        val requestPayload = HttpEntity<Any?>(headers)

        val endpoint = Msg91Constants.ApiEndPoints.RESEND_OTP
        val apiUrl = "${msg91Properties.serverBaseUrl}/${endpoint.value}"

        // Set query parameters
        val queryParams = mapOf(
            "authkey" to msg91Properties.authentication.authKey,
            "mobile" to "91$mobileNumber",
            "retrytype" to Msg91Constants.OtpResendTypes.TEXT.value,
        )
        val apiUri = UriComponentsBuilder.fromUriString(apiUrl)
            .apply { queryParams.forEach { queryParam(it.key, it.value) } }
            .build().toUri()

        val errorResponseHandler = Msg91ApiErrorResponseHandler(endpoint)

        RestTemplate().apply {
            errorHandler = errorResponseHandler

            val response = exchange(
                apiUri,
                HttpMethod.POST,
                requestPayload,
                String::class.java
            )

            return response.body?.let {
                val responseObject = objectMapper.readValue(it, Msg91OtpResponse::class.java)

                when (responseObject.type) {
                    "success" -> {
                        return responseObject
                    }

                    "error" -> {
                        val (formattedMessage, errorType) = Msg91Constants.otpGenerationApiErrorResponses[responseObject.message] ?: Pair(
                            ApiMessages.Common.error400, ErrorTypes.Http4xxErrors.BAD_REQUEST
                        )

                        logger.error("Error from msg91 --- mobileNumber: $mobileNumber | errorMessage: ${responseObject.message} | responseObject: $responseObject")
                        throw BadRequestException(
                            errorType,
                            formattedMessage
                        )
                    }

                    else -> {
                        logger.error("Invalid response from msg91. Unrecognised responseObject.type --- mobileNumber: $mobileNumber | responseObject: $responseObject")
                        throw InternalServerErrorException(
                            message = ApiMessages.Common.vendorError,
                        )

                    }
                }
            } ?: throw errorResponseHandler.msg91ApiInternalServerException(
                null,
                endpoint.value,
                objectMapper.writeValueAsString(response),
                "response body cannot be null in MSG91 otp generation api response for mobileNumber: $mobileNumber"
            )
        }
    }
}