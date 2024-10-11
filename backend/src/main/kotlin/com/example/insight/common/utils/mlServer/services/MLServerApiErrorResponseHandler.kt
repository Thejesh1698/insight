package com.example.insight.common.utils.mlServer.services

import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.utils.mlServer.utils.MLServerConstants
import org.springframework.http.client.ClientHttpResponse
import org.springframework.web.client.DefaultResponseErrorHandler
import org.springframework.web.client.HttpStatusCodeException

class MLServerApiErrorResponseHandler(private val endpoint: MLServerConstants.ApiEndPoints) :
    DefaultResponseErrorHandler() {

    override fun hasError(response: ClientHttpResponse): Boolean {

        return (response.statusCode.is5xxServerError) ||
                (response.statusCode.is4xxClientError)
    }

    override fun handleError(response: ClientHttpResponse) {

        try {
            super.handleError(response)
        } catch (e: HttpStatusCodeException) {
            throw mlServerApiInternalServerException(null, endpoint.value, e.responseBodyAsString)
        }
    }

    fun mlServerApiInternalServerException(
        userId: Long?,
        endpoint: String,
        response: String,
        loggingMessage: String = "ML Server Api error"
    ): Exception {

        val additionalInfo = hashMapOf(
            "endpoint" to endpoint,
            "response" to response
        )
        print("{ userId : $userId | errorMessage : $loggingMessage | additionalInfo : $additionalInfo }")
        throw InternalServerErrorException()
    }
}