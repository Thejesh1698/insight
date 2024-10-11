package com.example.insight.features.footPrints.models.requests

import com.example.insight.features.footPrints.utils.FootPrintsConstants

data class ArticleSummaryReadTrackingRequest (
    val footPrints: ArrayList<ArticleSummaryReadTrackingInfo>
) {

    data class ArticleSummaryReadTrackingInfo(
        val activityId: Long,
        val userId: Long,
        val contentId: String,
        val sqsRequestId: String,
        val activityType: FootPrintsConstants.ARTICLE_INTERACTIONS_FEATURE_TYPES
    )
}