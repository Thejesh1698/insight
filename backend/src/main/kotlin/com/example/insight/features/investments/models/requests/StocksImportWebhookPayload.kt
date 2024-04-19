package com.example.insight.features.investments.models.requests

import com.fasterxml.jackson.annotation.JsonIgnoreProperties

@JsonIgnoreProperties(ignoreUnknown = true)
data class SmallCaseStocksImportWebhookPayload (
    val lastUpdate: String,
    val snapshotDate: String,
    val notes: String?,
    val smallcaseAuthId: String,
    val broker: String,
    val transactionId: String,
    val timestamp: String,
    val checksum: String,
    val securities: List<SmallCaseSecurity>
) {

    @JsonIgnoreProperties(ignoreUnknown = true)
    data class SmallCaseSecurity(
        val holdings: SmallCaseStockValueInfo,
        val positions: SmallCaseStockPositionsInfo,
        val nseTicker: String?,
        val bseTicker: String?,
        val isin: String,
        val name: String
    )

    data class SmallCaseStockPositionsInfo(
        val nse: SmallCaseStockValueInfo,
        val bse: SmallCaseStockValueInfo,
    )

    data class SmallCaseStockValueInfo(
        val quantity: Long,
        val averagePrice: Float,
    )
}