package com.example.insight.common.utils.thirdParties.mixpanel.utils

import com.example.insight.common.utils.thirdParties.mixpanel.models.requests.MixpanelImportEventRequest
import com.example.insight.common.utils.thirdParties.mixpanel.models.requests.MixpanelSetUserPropertyRequest
import com.example.insight.common.utils.thirdParties.mixpanel.models.responses.MixpanelImportEventResponse
import com.example.insight.common.utils.thirdParties.mixpanel.properties.MixpanelProperties
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.boot.web.client.RestTemplateBuilder
import org.springframework.http.*
import org.springframework.stereotype.Service
import org.springframework.web.client.RestTemplate
import java.util.*
import kotlin.collections.ArrayList

@Service
class MixpanelApiUtils(val mixpanelProperties: MixpanelProperties) {

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    @Throws
    private fun restTemplateBuilder(): RestTemplate {
        return RestTemplateBuilder().rootUri(mixpanelProperties.domainUrl).build()
    }

    private fun getHeaders(): HttpHeaders {
        return HttpHeaders().apply {
            setBasicAuth(mixpanelProperties.userName, mixpanelProperties.password)
            contentType = MediaType.APPLICATION_JSON
            accept = Collections.singletonList(MediaType.APPLICATION_JSON)
        }
    }

    private fun getHeadersForSetUserProperties(): HttpHeaders {
        return HttpHeaders().apply {
            contentType = MediaType.APPLICATION_JSON
            accept = Collections.singletonList(MediaType.TEXT_PLAIN)
        }
    }

    private fun getUriVariables(): MutableMap<String, Any> {
        val uriVariables: MutableMap<String, Any> = HashMap()
        uriVariables["strict"] = 1
        uriVariables["project_id"] = mixpanelProperties.projectId
        return uriVariables
    }

    fun importEventsToMixpanel(data: ArrayList<MixpanelImportEventRequest> ): Boolean {

        var apiResponse: MixpanelImportEventResponse?
        val endpoint = "/import?strict={strict}&project_id={project_id}"
        val errorResponseHandler = MixpanelApiErrorResponseHandler(endpoint)
        try {
            restTemplateBuilder().apply {

                errorHandler = errorResponseHandler

                val request: HttpEntity<ArrayList<MixpanelImportEventRequest>> = HttpEntity(data, getHeaders())
                apiResponse = postForObject(endpoint, request, MixpanelImportEventResponse::class.java, getUriVariables())
                logger.info("Mixpanel event api call executed! --- data: $data | apiResponse: $apiResponse")
                if (apiResponse != null) {
                    val resp = apiResponse!!.status
                    return (resp == "OK")
                }
                return false
            }
        } catch (error: Error) {
            logger.error("Exception while calling mixpanel api for event --- data: $data | errorMessage: ${error.message}")
            return false
        }
    }

    fun setUserProperties(data: ArrayList<MixpanelSetUserPropertyRequest>): Int? {

        appendCommonProperties(data)
        var apiResponse: Int?
        val endpoint = "/engage#profile-set"
        val errorResponseHandler = MixpanelApiErrorResponseHandler(endpoint)

        try {
            restTemplateBuilder().apply {

                errorHandler = errorResponseHandler

                val request = HttpEntity(data, getHeadersForSetUserProperties())
                apiResponse = postForObject(endpoint, request, Int::class.java)
                logger.info("Mixpanel set user properties api call executed! --- data: $data | apiResponse: $apiResponse")
                if(apiResponse == 0) {
                    logger.error("Exception while calling mixpanel api for set user properties --- data: $data | apiResponse: $apiResponse")
                }
                return apiResponse
            }
        } catch (error: Error) {
            logger.error("Exception while calling mixpanel set user properties api --- data: $data | errorMessage: ${error.message}")
            return null
        }
    }

    private fun appendCommonProperties(data: ArrayList<MixpanelSetUserPropertyRequest>) {
        data.forEach {
            it.token = mixpanelProperties.projectToken
        }
    }

}