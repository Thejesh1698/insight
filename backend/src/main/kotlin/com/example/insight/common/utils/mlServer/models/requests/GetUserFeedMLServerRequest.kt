package com.example.insight.common.utils.mlServer.models.requests

import com.fasterxml.jackson.annotation.JsonProperty
import com.example.insight.features.feed.utils.FeedConstants

data class GetUserFeedMLServerRequest(
    @JsonProperty("user_id")
    val userId: Long,

    @JsonProperty("topic_ids")
    val topicIds: List<Long>,

    @JsonProperty("feed_article_count")
    val feedArticleCount: Int,

    @JsonProperty("seconds_since_last_api_call")
    val secondsSinceLastApiCall: Long?,

    @JsonProperty("current_feed_session_article_ids")
    val currentFeedSessionArticleIds: List<String>,

    val page: Int,

    @JsonProperty("content_type")
    val contentType: FeedConstants.FeedType,
)