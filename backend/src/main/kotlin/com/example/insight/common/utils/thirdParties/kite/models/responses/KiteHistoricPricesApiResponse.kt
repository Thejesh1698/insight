package com.example.insight.common.utils.thirdParties.kite.models.responses

import com.fasterxml.jackson.annotation.JsonIgnoreProperties
import com.fasterxml.jackson.annotation.JsonProperty

@JsonIgnoreProperties(ignoreUnknown = true)
data class KiteHistoricPricesApiResponse (
    @JsonProperty("status")
    val status: String,

    @JsonProperty("data")
    val data: HistoricPricesData
) {

    data class HistoricPricesData(
        @JsonProperty("candles")
        val candles: List<List<Any>>? = emptyList()
        //candles response format: [timestamp, open, high, low, close, volume]
    )
}