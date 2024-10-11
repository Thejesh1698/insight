package com.example.insight.features.feed.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse
import com.example.insight.features.article.models.responses.ArticleInfoForUserResponse

data class UserEpisodeFeedResponse(
    val sessionId: Long,
    val feedId: Long,
    val episodes: List<ArticleInfoForUserResponse>,
    val additionalInfo: HashMap<String, HashMap<String, Any?>>?,
    val episodeIds: List<String>,
    override val message: String = ApiMessages.Common.success200
) : CommonResponse