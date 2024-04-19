package com.example.insight.features.eventsManager.services

import com.example.insight.common.utils.thirdParties.mixpanel.services.MixPanelService
import com.example.insight.features.eventsManager.models.Event
import com.example.insight.features.eventsManager.utils.EventConstants
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.scheduling.annotation.Async
import org.springframework.stereotype.Service

@Service
class EventsManagerService {

    val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    @Autowired
    private lateinit var mixPanelService: MixPanelService

    @Async
    fun publishEvent(
        event: Event
    ) {

        try {
            if(event.publishToMixpanel) {
                mixPanelService.publishEvent(
                    event
                )

                if(event.eventInfo.userProperties != null) {
                    mixPanelService.setUserProperties(
                        event
                    )
                }
            }
        } catch (exception: Exception) {
            logger.error("Error while publishing the event --- event: $event | exception: $exception")
        }
    }

    @Async
    fun setUserPropertiesInMixpanel(userId: Long, userProperties: HashMap<EventConstants.UserPropertyKeys, Any?>) {

        try {
            mixPanelService.setUserProperties(
                userId,
                userProperties
            )
        } catch (exception: Exception) {
            logger.error("Error while publishing the event --- userId: $userId | userProperties: $userProperties | " +
                    "exception: $exception")
        }
    }
}