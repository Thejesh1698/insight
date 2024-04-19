package com.example.insight.common.configurations.interceptors

import com.example.insight.features.eventsManager.utils.EventConstants
import com.example.insight.features.eventsManager.utils.EventsRequestContextHelper
import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Component
import org.springframework.web.servlet.HandlerInterceptor
import java.lang.Exception

@Component
class EventTrackingInterceptor : HandlerInterceptor {

    val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    @Autowired
    private lateinit var eventsRequestContextHelper: EventsRequestContextHelper

    override fun preHandle(request: HttpServletRequest, response: HttpServletResponse, handler: Any): Boolean {

        getAndSetPlatformTypeHeader(request)
        getAndSetAppHeaders(request)
        return true
    }

    private fun getAndSetPlatformTypeHeader(request: HttpServletRequest) {

        try {
            request.getHeader(EventConstants.EventsRequestContextProperties.HeaderNames.PLATFORM_TYPE.toString())?.let {
                eventsRequestContextHelper.setPlatformType(it)
            }
        } catch (error: Exception) {
            logger.error("${error.message}")
        }
    }

    private fun getAndSetAppHeaders(request: HttpServletRequest) {

        try {
            request.getHeader(EventConstants.EventsRequestContextProperties.HeaderNames.APP_VERSION.toString())?.let {
                eventsRequestContextHelper.setAppVersion(it)
            }
            request.getHeader(EventConstants.EventsRequestContextProperties.HeaderNames.APP_BUILD_NUMBER.toString())
                ?.let {
                    eventsRequestContextHelper.setAppBuildNumber(it)
                }
            request.getHeader(EventConstants.EventsRequestContextProperties.HeaderNames.DEVICE_BRAND.toString())?.let {
                eventsRequestContextHelper.setDeviceBrand(it)
            }
            request.getHeader(EventConstants.EventsRequestContextProperties.HeaderNames.DEVICE_MANUFACTURER.toString())
                ?.let {
                    eventsRequestContextHelper.setDeviceManufacturer(it)
                }
        } catch (error: Exception) {
            logger.error("${error.message}")
        }
    }
}