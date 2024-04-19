package com.example.insight.features.eventsManager.utils

import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component
import org.springframework.web.context.request.RequestAttributes
import org.springframework.web.context.request.RequestContextHolder

@Component
class EventsRequestContextHelper {

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    fun getPlatformType(): String {

        return getHeaderValueFromRequestContext(
            EventConstants.EventsRequestContextProperties.HeaderNames.PLATFORM_TYPE.toString(),
            "NA"
        )
    }

    fun setPlatformType(source: String) {

        return setHeaderValueInRequestContext(
            EventConstants.EventsRequestContextProperties.HeaderNames.PLATFORM_TYPE.toString(),
            source
        )
    }

    fun getAppVersion(): String {

        return getHeaderValueFromRequestContext(
            EventConstants.EventsRequestContextProperties.HeaderNames.APP_VERSION.toString(),
            "NA"
        )
    }

    fun setAppVersion(appVersionName: String) {

        return setHeaderValueInRequestContext(
            EventConstants.EventsRequestContextProperties.HeaderNames.APP_VERSION.toString(),
            appVersionName
        )
    }

    fun getAppBuildNumber(): String {

        return getHeaderValueFromRequestContext(
            EventConstants.EventsRequestContextProperties.HeaderNames.APP_BUILD_NUMBER.toString(),
            "NA"
        )
    }

    fun setAppBuildNumber(appBuildNumber: String) {

        return setHeaderValueInRequestContext(
            EventConstants.EventsRequestContextProperties.HeaderNames.APP_BUILD_NUMBER.toString(),
            appBuildNumber
        )
    }

    fun getDeviceBrand(): String {

        return getHeaderValueFromRequestContext(
            EventConstants.EventsRequestContextProperties.HeaderNames.DEVICE_BRAND.toString(),
            "NA"
        )
    }

    fun setDeviceBrand(brand: String) {

        return setHeaderValueInRequestContext(
            EventConstants.EventsRequestContextProperties.HeaderNames.DEVICE_BRAND.toString(),
            brand
        )
    }

    fun getDeviceManufacturer(): String {

        return getHeaderValueFromRequestContext(
            EventConstants.EventsRequestContextProperties.HeaderNames.DEVICE_MANUFACTURER.toString(),
            "NA"
        )
    }

    fun setDeviceManufacturer(manufacturer: String) {

        return setHeaderValueInRequestContext(
            EventConstants.EventsRequestContextProperties.HeaderNames.DEVICE_MANUFACTURER.toString(),
            manufacturer
        )
    }

    fun setHeaderValueInRequestContext(headerName: String, value: String) {

        try {
            RequestContextHolder
                .getRequestAttributes()
                ?.setAttribute(headerName, value, RequestAttributes.SCOPE_SESSION)
        } catch (exception: Exception) {
            logger.error(
                "Unable to set header value in request content --- " +
                        "exception: $exception | header: $headerName | value: $value"
            )
        }
    }

    fun getHeaderValueFromRequestContext(headerName: String, defaultValue: String): String {

        return try {
            RequestContextHolder
                .currentRequestAttributes()
                .getAttribute(headerName, RequestAttributes.SCOPE_SESSION)
                .toString()
        } catch (exception: Exception) {
            logger.error(
                "Unable to set header value from request content --- " +
                        "exception: $exception | header: $headerName | defaultValue: $defaultValue"
            )
            return defaultValue
        }
    }

}