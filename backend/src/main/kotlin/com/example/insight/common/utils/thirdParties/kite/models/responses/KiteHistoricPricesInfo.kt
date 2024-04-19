package com.example.insight.common.utils.thirdParties.kite.models.responses

import com.example.insight.features.investments.utils.UserInvestmentsConstants
import java.math.BigInteger

data class KiteHistoricPricesInfo(
    val date: String,
    val openPrice: Float,
    val highPrice: Float,
    val lowPrice: Float,
    val closePrice: Float,
    val volume: BigInteger,
    val exchange: UserInvestmentsConstants.StockExchanges
)