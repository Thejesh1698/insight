package com.example.insight.features.podcasts.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse

data class PodcastsLatestEpisodeInfoResponse(
    val podcastsInfo: List<PodcastsInfo>,
    override val message: String = ApiMessages.Common.success200
) : CommonResponse {

    data class PodcastsInfo(
        val podcastId: String,
        val sourceReferenceId: String,
        var latestEpisodeTime: String?,
        var totalNumberOfEpisodes: Int
    )
}