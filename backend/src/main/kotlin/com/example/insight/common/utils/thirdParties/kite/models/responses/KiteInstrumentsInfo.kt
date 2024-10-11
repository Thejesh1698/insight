package com.example.insight.common.utils.thirdParties.kite.models.responses

import kotlin.properties.Delegates

data class KiteInstrumentsInfo(
    val ticker: String,
    val kiteTradingSymbol: String,
    val kiteInstrumentToken: String,
    val instrumentName: String,
) {
    var investmentOptionId by Delegates.notNull<Long>()
}