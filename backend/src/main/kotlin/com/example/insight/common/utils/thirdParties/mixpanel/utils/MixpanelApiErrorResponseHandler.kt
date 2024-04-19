package com.example.insight.common.utils.thirdParties.mixpanel.utils

import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import org.springframework.http.client.ClientHttpResponse
import org.springframework.web.client.DefaultResponseErrorHandler
import org.springframework.web.client.HttpStatusCodeException

class MixpanelApiErrorResponseHandler(private val endpoint: String) :
    DefaultResponseErrorHandler() {

    override fun hasError(response: ClientHttpResponse): Boolean {

        return (response.statusCode.is5xxServerError) ||
                (response.statusCode.is4xxClientError)
    }

    override fun handleError(response: ClientHttpResponse) {

        try {
            super.handleError(response)
        } catch (e: HttpStatusCodeException) {
            throw mixpanelApiInternalServerException(null, endpoint, e.responseBodyAsString)
        }
    }

    fun mixpanelApiInternalServerException(
        userId: Long?,
        endpoint: String,
        response: String,
        loggingMessage: String = "Mixpanel Server Api error",
    ): Exception {

        val additionalInfo = hashMapOf(
            "endpoint" to endpoint,
            "response" to response
        )
        print("{ userId : $userId | errorMessage : $loggingMessage | additionalInfo : $additionalInfo }")
        throw InternalServerErrorException()
    }
}