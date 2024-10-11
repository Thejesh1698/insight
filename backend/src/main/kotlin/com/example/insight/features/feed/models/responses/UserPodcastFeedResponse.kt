package com.example.insight.features.feed.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse
import com.example.insight.features.article.models.responses.ArticleSourceInfoForUserResponse

data class UserPodcastFeedResponse(
    val sessionId: Long,
    val feedId: Long,
    val podcasts: List<ArticleSourceInfoForUserResponse>,
    val additionalInfo: HashMap<String, HashMap<String, Any?>>?,
    val podcastIds: List<String>,
    override val message: String = ApiMessages.Common.success200
) : CommonResponse