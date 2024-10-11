package com.example.insight.features.investments.models

data class InvestmentOptionAndKiteTradingSymbol (
    val investmentOptionId: Long,
    val exchange: String,
    val kiteTradingSymbol: String,
)