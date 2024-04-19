package com.example.insight.features.footPrints.models.requests

import com.example.insight.features.footPrints.utils.FootPrintsConstants

data class ArticleOpenTrackingRequest (
    val footPrints: ArrayList<ArticleOpenTrackingInfo>
) {

    data class ArticleOpenTrackingInfo(
        val activityId: Long,
        val userId: Long,
        val contentId: String,
        val sqsRequestId: String,
        val activityType: FootPrintsConstants.ARTICLE_INTERACTIONS_FEATURE_TYPES
    )
}