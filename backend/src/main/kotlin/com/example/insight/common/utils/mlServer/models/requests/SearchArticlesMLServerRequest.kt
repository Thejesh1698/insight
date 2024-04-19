package com.example.insight.common.utils.mlServer.models.requests

import com.fasterxml.jackson.annotation.JsonProperty

data class SearchArticlesMLServerRequest(
    @JsonProperty("query_text")
    val searchQuery: String,

    val userId: Long
)