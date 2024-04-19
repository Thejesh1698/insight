package com.example.insight.features.podcasts.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse

data class SavePodcastEpisodeResponse (
    val podcastEpisodeId: String,
    override val message: String = ApiMessages.Common.success200
): CommonResponse