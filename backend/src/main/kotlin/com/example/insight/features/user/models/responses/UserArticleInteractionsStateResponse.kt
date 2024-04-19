package com.example.insight.features.user.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse

data class UserArticleInteractionsStateResponse (
    val states: HashMap<String, ArticleInteractionsState>,
    override val message: String = ApiMessages.Common.success200
): CommonResponse {

    data class ArticleInteractionsState(
            val bookmarkId: Long?,
            val isNotInterested: Boolean?,
            val showMoreLikeThis: Boolean?
    )

}