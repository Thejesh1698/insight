package com.example.insight.features.investments.models

data class InvestmentHistoryInsertInputClass (
    val shareQuantity: Long,
    val averagePrice: Float,
) {
    var investmentOptionId: Long? = null
}