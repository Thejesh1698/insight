package com.example.insight.features.footPrints.models.requests

import com.example.insight.features.footPrints.utils.FootPrintsConstants

data class ArticleVisibilityTrackingRequest (
    val footPrints: ArrayList<ArticleVisibilityTrackingInfo>
) {

    data class ArticleVisibilityTrackingInfo(
        val activityId: Long,
        val userId: Long,
        val contentId: String,
        val contentPosition: HashMap<String, Int>,
        val sqsRequestId: String,
        val activityType: FootPrintsConstants.ARTICLE_INTERACTIONS_FEATURE_TYPES
    )
}