package com.example.insight.common.utils.thirdParties.msg91.services

import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.utils.thirdParties.msg91.utils.Msg91Constants
import org.springframework.http.client.ClientHttpResponse
import org.springframework.web.client.DefaultResponseErrorHandler
import org.springframework.web.client.HttpStatusCodeException

class Msg91ApiErrorResponseHandler(private val endpoint: Msg91Constants.ApiEndPoints) :
    DefaultResponseErrorHandler() {

    override fun hasError(response: ClientHttpResponse): Boolean {

        return (response.statusCode.is5xxServerError) ||
                (response.statusCode.is4xxClientError)
    }

    override fun handleError(response: ClientHttpResponse) {

        try {
            super.handleError(response)
        } catch (e: HttpStatusCodeException) {
            throw msg91ApiInternalServerException(null, endpoint.value, e.responseBodyAsString)
        }
    }

    fun msg91ApiInternalServerException(
        userId: Long?,
        endpoint: String,
        response: String,
        loggingMessage: String = "Msg91 Server Api error",
    ): Exception {

        val additionalInfo = hashMapOf(
            "endpoint" to endpoint,
            "response" to response
        )
        print("{ userId : $userId | errorMessage : $loggingMessage | additionalInfo : $additionalInfo }")
        throw InternalServerErrorException()
    }
}