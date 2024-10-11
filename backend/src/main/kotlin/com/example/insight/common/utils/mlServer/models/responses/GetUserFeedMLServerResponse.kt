package com.example.insight.common.utils.mlServer.models.responses

import com.fasterxml.jackson.annotation.JsonIgnoreProperties
import com.fasterxml.jackson.annotation.JsonProperty

@JsonIgnoreProperties(ignoreUnknown = true)
data class GetUserFeedMLServerResponse(
    val feedContents: List<FeedContentMLResponse>,
    val additionalInfo: HashMap<String, HashMap<String, Any?>>? = null
) {
    @JsonIgnoreProperties(ignoreUnknown = true)
    data class FeedContentMLResponse(
        @JsonProperty("content_id")
        val contentId: String
    )
}