package com.example.insight.common.utils.thirdParties.smallCase.services

import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.utils.thirdParties.smallCase.utils.SmallCaseConstants
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.http.client.ClientHttpResponse
import org.springframework.web.client.DefaultResponseErrorHandler
import org.springframework.web.client.HttpStatusCodeException

class SmallCaseApiErrorResponseHandler(private val endpoint: SmallCaseConstants.ApiEndPoints) :
    DefaultResponseErrorHandler() {

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    override fun hasError(response: ClientHttpResponse): Boolean {

        return (response.statusCode.is5xxServerError) ||
                (response.statusCode.is4xxClientError)
    }

    override fun handleError(response: ClientHttpResponse) {

        try {
            super.handleError(response)
        } catch (e: HttpStatusCodeException) {
            var responseBody: String? = e.responseBodyAsString
            if(responseBody.isNullOrBlank()) {
                responseBody = e.message
            }
            throw smallCaseApiInternalServerException(null, endpoint.value, responseBody)
        }
    }

    fun smallCaseApiInternalServerException(
        userId: Long?,
        endpoint: String,
        response: String?,
        loggingMessage: String = "Small Case Server Api error",
    ): Exception {

        val additionalInfo = hashMapOf(
            "endpoint" to endpoint,
            "response" to response
        )
        logger.error("{ userId : $userId | errorMessage : $loggingMessage | additionalInfo : $additionalInfo }")
        throw InternalServerErrorException()
    }
}