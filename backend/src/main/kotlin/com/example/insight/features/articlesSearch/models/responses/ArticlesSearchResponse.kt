package com.example.insight.features.articlesSearch.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse
import com.example.insight.features.article.models.responses.ArticleInfoForUserResponse

data class ArticlesSearchResponse(
    val searchId: Long,
    val page: Int,
    val articles: List<ArticleInfoForUserResponse>,
    val additionalInfo: HashMap<String, HashMap<String, Any?>>?,
    val totalNumberOfPages: Int,
    val totalNumberOfArticles: Int,
    val articleIds: List<String>,
    val userPortfolioData: Boolean? = null,
    val portfolioData: List<HashMap<String, Any?>?>? = null,
    override val message: String = ApiMessages.Common.success200
) : CommonResponse