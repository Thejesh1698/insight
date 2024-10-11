package com.example.insight.features.article.models.requests

data class AiGeneratedInfoForArticleRequest (
    val model: String,
    val summary: AiGeneratedInfo,
    val title: AiGeneratedInfo,
    val isFinancialNews: Boolean? = null,
    val isRelevantForIndia: Boolean? = null,
) {
    data class AiGeneratedInfo(
        val value: String,
        val additionalInfo: HashMap<String, Any?>
    )
}