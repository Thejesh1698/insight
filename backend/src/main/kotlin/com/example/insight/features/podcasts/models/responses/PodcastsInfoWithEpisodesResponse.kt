package com.example.insight.features.podcasts.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse
import com.example.insight.features.article.models.responses.ArticleInfoForUserResponse
import com.example.insight.features.article.models.responses.ArticleSourceInfoForUserResponse

data class PodcastsInfoWithEpisodesResponse(
    val podcastInfo: ArticleSourceInfoForUserResponse,
    val episodes: List<ArticleInfoForUserResponse>,
    val paginatorInfo: PodcastEpisodesPaginatorInfo,
    override val message: String = ApiMessages.Common.success200
) : CommonResponse {

    data class PodcastEpisodesPaginatorInfo(
        val totalNumberOfPages: Long?,
        val cursor: String?
    )
}