package com.example.insight.features.eventsManager.models

import com.example.insight.features.eventsManager.utils.EventConstants

data class Event (
    val userId: Long,
    val eventInfo: EventInfo,
    val publishToMixpanel: Boolean = true
) {

    data class EventInfo(
        val name: EventConstants.EventNames,
        val eventProperties: HashMap<EventConstants.EventPropertyKeys, Any?>,
        val userProperties: HashMap<EventConstants.UserPropertyKeys, Any?>? = null,
    )
}