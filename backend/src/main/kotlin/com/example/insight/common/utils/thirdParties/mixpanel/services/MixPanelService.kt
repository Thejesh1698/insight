package com.example.insight.common.utils.thirdParties.mixpanel.services

import com.example.insight.common.errorHandler.exceptions.BadRequestException
import com.example.insight.common.utils.getCurrentTimeStampOfIndianTimeZone
import com.example.insight.common.utils.thirdParties.mixpanel.models.requests.MixpanelImportEventRequest
import com.example.insight.common.utils.thirdParties.mixpanel.models.requests.MixpanelSetUserPropertyRequest
import com.example.insight.common.utils.thirdParties.mixpanel.utils.MixpanelApiUtils
import com.example.insight.features.eventsManager.utils.EventsRequestContextHelper
import com.example.insight.features.eventsManager.models.Event
import com.example.insight.features.eventsManager.utils.EventConstants
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service
import java.util.*
import kotlin.collections.HashMap

@Service
class MixPanelService {

    @Autowired
    private lateinit var mixpanelApiUtils: MixpanelApiUtils

    @Autowired
    private lateinit var eventsRequestContextHelper: EventsRequestContextHelper

    val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    fun publishEvent(
        event: Event
    ) {

        if(event.eventInfo.name.mixpanelName.isNullOrBlank()) {
            logger.error("Mixpanel event name cannot be null! --- event: $event")
            throw BadRequestException(notifyUser = false)
        }

        val eventProperties = HashMap<String, Any?>(
            event.eventInfo.eventProperties
                .filter { !(it.value == null || it.value == "null") }
                .map { it.key.mixpanelKey to it.value }
                .toMap()
        )
        appendCommonProperties(eventProperties)

        val mixpanelImportEventRequest = MixpanelImportEventRequest(event.eventInfo.name.mixpanelName, eventProperties)
        val data = arrayListOf(mixpanelImportEventRequest)
        mixpanelApiUtils.importEventsToMixpanel(data)
    }

    private fun appendCommonProperties(properties: HashMap<String, Any?>) {

        EventConstants.EventPropertyKeys.VENDOR_KEY_INSERT_ID.mixpanelKey?.let {
            properties[it] = UUID.randomUUID().toString()
        }

        EventConstants.EventPropertyKeys.VENDOR_KEY_TIME.mixpanelKey?.let {
            properties[it] = getCurrentTimeStampOfIndianTimeZone()
        }

        EventConstants.EventPropertyKeys.PLATFORM_TYPE.mixpanelKey?.let {
            properties[it] = eventsRequestContextHelper.getPlatformType()
        }

        val appProperties: MutableMap<String, String> = HashMap()
        EventConstants.EventPropertyKeys.APP_VERSION.mixpanelKey?.let {
            appProperties[it] = eventsRequestContextHelper.getAppVersion()
        }
        EventConstants.EventPropertyKeys.APP_BUILD_NUMBER.mixpanelKey?.let {
            appProperties[it] = eventsRequestContextHelper.getAppBuildNumber()
        }
        EventConstants.EventPropertyKeys.DEVICE_BRAND.mixpanelKey?.let {
            appProperties[it] = eventsRequestContextHelper.getDeviceBrand()
        }
        EventConstants.EventPropertyKeys.DEVICE_MANUFACTURER.mixpanelKey?.let {
            appProperties[it] = eventsRequestContextHelper.getDeviceManufacturer()
        }
        properties.putAll(appProperties)
    }

    fun setUserProperties(event: Event) {

        val userProperties = event.eventInfo.userProperties?.let { properties ->
            HashMap<String, Any?>(
                properties.filter { !(it.value == null || it.value == "null") }
                .map { it.key.value to it.value }
                .toMap()
            )
        } ?: HashMap()
        val data = MixpanelSetUserPropertyRequest(
            distinctId = event.userId.toString(),
            properties = userProperties
        )
        val userProfileArray = arrayListOf(data)
        mixpanelApiUtils.setUserProperties(userProfileArray)
    }

    fun setUserProperties(userId: Long, userProperties: HashMap<EventConstants.UserPropertyKeys, Any?>) {

        val userPropertiesCleaned = HashMap<String, Any?>(
            userProperties.filter { !(it.value == null || it.value == "null") }
                .map { it.key.value to it.value }
                .toMap()
        )
        val data = MixpanelSetUserPropertyRequest(
            distinctId = userId.toString(),
            properties = userPropertiesCleaned
        )
        val userProfileArray = arrayListOf(data)
        mixpanelApiUtils.setUserProperties(userProfileArray)
    }
}