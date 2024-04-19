package com.example.insight.common.utils.mlServer.models.responses

import com.fasterxml.jackson.annotation.JsonIgnoreProperties
import com.fasterxml.jackson.annotation.JsonProperty

@JsonIgnoreProperties(ignoreUnknown = true)
data class SearchArticlesMLServerResponse(
    val searchArticleIds: List<SearchArticleIdsFromMLResponse>,
    val additionalInfo: HashMap<String, HashMap<String, Any?>>? = null,

    @JsonProperty("user_portfolio_data")
    val userPortfolioData: Boolean? = null,

    @JsonProperty("portfolio_data")
    val portfolioData: List<HashMap<String, Any?>?>? = null
) {
    @JsonIgnoreProperties(ignoreUnknown = true)
    data class SearchArticleIdsFromMLResponse(
        @JsonProperty("article_id")
        val articleId: String
    )
}