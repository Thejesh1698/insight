package com.example.insight.common.utils.mlServer.services

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.example.insight.common.utils.mlServer.models.requests.GetUserFeedMLServerRequest
import com.example.insight.common.utils.mlServer.models.requests.SearchArticlesMLServerRequest
import com.example.insight.common.utils.mlServer.models.responses.GetUserFeedMLServerResponse
import com.example.insight.common.utils.mlServer.models.responses.SearchArticlesMLServerResponse
import com.example.insight.common.utils.mlServer.properties.MLServersProperties
import com.example.insight.common.utils.mlServer.utils.MLServerConstants
import org.springframework.http.HttpEntity
import org.springframework.http.HttpHeaders
import org.springframework.http.HttpMethod
import org.springframework.http.MediaType
import org.springframework.stereotype.Service
import org.springframework.web.client.RestTemplate
import java.util.*

@Service
class MLServerService(val mlServerProperties: MLServersProperties) {

    val objectMapper: ObjectMapper = ObjectMapper().registerModule(KotlinModule())

    fun getUserFeed(
        details: GetUserFeedMLServerRequest
    ): Pair<GetUserFeedMLServerResponse, String> {

        val headers = HttpHeaders().apply {
            contentType = MediaType.APPLICATION_JSON
            accept = Collections.singletonList(MediaType.APPLICATION_JSON)
        }
        val requestPayload =
            HttpEntity<Any>(
                objectMapper.writeValueAsString(details),
                headers
            )
        val endpoint = MLServerConstants.ApiEndPoints.USER_FEED
        val apiUrl = "${mlServerProperties.cambrianServer.serverBaseUrl}/${endpoint.value}"
        val errorResponseHandler = MLServerApiErrorResponseHandler(endpoint)

        RestTemplate().apply {
            errorHandler = errorResponseHandler

            val response = exchange(
                apiUrl,
                HttpMethod.POST,
                requestPayload,
                String::class.java
            )

            return response.body?.let {
                return Pair(objectMapper.readValue(it, GetUserFeedMLServerResponse::class.java), it)
            } ?: throw errorResponseHandler.mlServerApiInternalServerException(
                details.userId,
                endpoint.value,
                objectMapper.writeValueAsString(response),
                "response body cannot be null in ML server api response"
            )
        }
    }

    fun getArticlesSearchResults(
        details: SearchArticlesMLServerRequest
    ): Pair<SearchArticlesMLServerResponse, String> {

        val headers = HttpHeaders().apply {
            contentType = MediaType.APPLICATION_JSON
            accept = Collections.singletonList(MediaType.APPLICATION_JSON)
        }
        val requestPayload =
            HttpEntity<Any>(
                objectMapper.writeValueAsString(details),
                headers
            )
        val endpoint = MLServerConstants.ApiEndPoints.PORTFOLIO_SEARCH

        val apiUrl = "${mlServerProperties.hubbleServer.serverBaseUrl}/${endpoint.value}"

        val errorResponseHandler = MLServerApiErrorResponseHandler(endpoint)

        RestTemplate().apply {
            errorHandler = errorResponseHandler

            val response = exchange(
                apiUrl,
                HttpMethod.POST,
                requestPayload,
                String::class.java
            )

            return response.body?.let {
                return Pair(objectMapper.readValue(it, SearchArticlesMLServerResponse::class.java), it)
            } ?: throw errorResponseHandler.mlServerApiInternalServerException(
                details.userId,
                endpoint.value,
                objectMapper.writeValueAsString(response),
                "response body cannot be null in ML server api response"
            )
        }
    }

    fun getAdditionalInfoFromSearchArticlesMLServerResponse(response: String): HashMap<String, HashMap<String, Any?>>? {

        val searchArticlesMLServerResponse: SearchArticlesMLServerResponse =
            objectMapper.readValue(response, SearchArticlesMLServerResponse::class.java)
        return searchArticlesMLServerResponse.additionalInfo
    }
}