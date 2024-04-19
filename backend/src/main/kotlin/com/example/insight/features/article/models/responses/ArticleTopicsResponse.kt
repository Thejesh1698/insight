package com.example.insight.features.article.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.entities.ArticleTopic
import com.example.insight.common.models.responses.CommonResponse

data class ArticleTopicsResponse(
    val topics: List<ArticleTopic>, override val message: String = ApiMessages.Common.success200
): CommonResponse

data class CategorizedArticleTopicsResponse(
    val topicCategories: HashMap<String, ArrayList<ArticleTopic>>,
    val topicCategoriesList: List<String>,
    override val message: String = ApiMessages.Common.success200
): CommonResponse