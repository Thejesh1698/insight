package com.example.insight.common.utils.thirdParties.smallCase.models.responses

data class TransactionCreationResponse(
    val success: Boolean,
    val errors: ArrayList<String>?,
    val errorType: String? = null,
    val data: TransactionCreationData?
) {
    data class TransactionCreationData(
        val transactionId: String,
        val expireAt: String
    )
}