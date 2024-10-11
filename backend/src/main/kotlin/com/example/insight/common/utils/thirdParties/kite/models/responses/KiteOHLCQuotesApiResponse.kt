package com.example.insight.common.utils.thirdParties.kite.models.responses

import com.fasterxml.jackson.annotation.JsonIgnoreProperties
import com.fasterxml.jackson.annotation.JsonProperty
import java.math.BigInteger

@JsonIgnoreProperties(ignoreUnknown = true)
data class KiteOHLCQuotesApiResponse (
    @JsonProperty("status")
    val status: String,

    @JsonProperty("data")
    val data: HashMap<String, OHLCQuotesData>
) {

    @JsonIgnoreProperties(ignoreUnknown = true)

    data class OHLCQuotesData(
        @JsonProperty("volume")
        val volume: BigInteger?,

        @JsonProperty("ohlc")
        val ohlc: OHLCValues,

        @JsonProperty("last_price")
        val lastPrice: Float
    )

    @JsonIgnoreProperties(ignoreUnknown = true)

    data class OHLCValues(
        @JsonProperty("open")
        val open: Float,

        @JsonProperty("high")
        val high: Float,

        @JsonProperty("low")
        val low: Float,

        @JsonProperty("close")
        val close: Float,
    )
}