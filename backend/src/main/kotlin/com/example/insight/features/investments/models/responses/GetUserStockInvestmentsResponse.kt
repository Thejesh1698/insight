package com.example.insight.features.investments.models.responses

import com.fasterxml.jackson.annotation.JsonIgnore
import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse
import com.example.insight.features.investments.utils.UserInvestmentsConstants

data class GetUserStockInvestmentsResponse (
    val totalInvestmentValue: Float,
    val lastFetched: Long?,
    val investments: List<StockInvestmentDetails>,
    val linkedBrokers: List<BrokerInvestmentInfo>,
    val activeFetchTransactionInProgress: Boolean, //-> true for max of 5 pollings with 3 sec delayed
    override val message: String = ApiMessages.Common.success200
): CommonResponse {

    data class BrokerInvestmentInfo(
        val name: UserInvestmentsConstants.BROKERS,
        var stockCount: Long,
        val lastFetched: Long,
        val iconUrl: String,
        val isRefreshPossible: Boolean,
        val anyActiveFetchTransaction: Boolean
    )

    data class StockInvestmentDetails(
        val name: String,
        val nseTicker : String?,
        val bseTicker : String?,
        var shareQuantity : Long,
        var averageSharePrice : Float,
        var investedValue : Float,
        @JsonIgnore
        val broker: UserInvestmentsConstants.BROKERS,
        @JsonIgnore
        val investmentOptionId: Long
    )
}