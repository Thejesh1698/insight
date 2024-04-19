package com.example.insight.common.utils.thirdParties.smallCase.utils

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.utils.thirdParties.smallCase.models.responses.TransactionCreationResponse
import com.example.insight.common.utils.thirdParties.smallCase.properties.SmallCaseProperties
import com.example.insight.common.utils.thirdParties.smallCase.services.SmallCaseApiErrorResponseHandler
import com.example.insight.common.utils.thirdParties.smallCase.utils.SmallCaseConstants.GATEWAY_AUTH_TOKEN_HEADER
import com.example.insight.common.utils.thirdParties.smallCase.utils.SmallCaseConstants.GATEWAY_SECRET_HEADER
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.http.*
import org.springframework.stereotype.Service
import org.springframework.web.client.RestTemplate
import java.util.*
import kotlin.collections.HashMap

@Service
class SmallCaseApiUtils(val smallCaseProperties: SmallCaseProperties) {

    val objectMapper: ObjectMapper = ObjectMapper().registerModule(KotlinModule())
    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    fun creatTransaction(
        userId: Long,
        authToken: String,
        details: HashMap<String, Any?>
    ): Pair<TransactionCreationResponse.TransactionCreationData, String> {

        val headers = HttpHeaders().apply {
            contentType = MediaType.APPLICATION_JSON
            accept = Collections.singletonList(MediaType.APPLICATION_JSON)
            this.add(GATEWAY_AUTH_TOKEN_HEADER, authToken)
            this.add(GATEWAY_SECRET_HEADER, smallCaseProperties.apiGatewaySecret)
        }
        val requestPayload =
            HttpEntity<Any>(
                objectMapper.writeValueAsString(details),
                headers
            )

        val endpoint = SmallCaseConstants.ApiEndPoints.HOLDINGS_IMPORT_TRANSACTION
        val apiUrl = "${smallCaseProperties.serverBaseUrl}/${endpoint.value}"
        val errorResponseHandler = SmallCaseApiErrorResponseHandler(endpoint)

        RestTemplate().apply {
            errorHandler = errorResponseHandler

            val response = exchange(
                apiUrl,
                HttpMethod.POST,
                requestPayload,
                String::class.java
            )

            return response.body?.let {
                val transactionResponse = objectMapper.readValue(it, TransactionCreationResponse::class.java)

                return if(transactionResponse.data?.transactionId != null) {
                    Pair(transactionResponse.data, it)
                } else {
                    logger.error(
                        "Invalid small case api response. Transaction id cannot be null --- " +
                                "userId: $userId | transactionResponse: $transactionResponse"
                    )
                    throw InternalServerErrorException()
                }
            } ?: throw errorResponseHandler.smallCaseApiInternalServerException(
                userId,
                endpoint.value,
                objectMapper.writeValueAsString(response),
                "response body cannot be null in ML server api response"
            )
        }
    }
}