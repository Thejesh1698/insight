package com.example.insight.features.user.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.entities.Reaction
import com.example.insight.common.models.responses.CommonResponse

data class UserAppSummaryResponse (
    val reactions: AppSummaryReactionsResponse,
    val feedConfig: AppFeedConfig,
    override val message: String = ApiMessages.Common.success200
): CommonResponse {

    data  class AppSummaryReactionsResponse(
        val articleReactions: List<Reaction>
    )

    data  class AppFeedConfig(
        val podcastFeedOffset: Int,
        val podcastEpisodeFeedOffset: Int
    )
}