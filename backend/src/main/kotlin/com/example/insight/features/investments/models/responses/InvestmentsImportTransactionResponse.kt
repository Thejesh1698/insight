package com.example.insight.features.investments.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse

data class InvestmentsImportTransactionResponse (
    val transactionId: String?,
    val sdkToken: String?,
    val areHoldingsDirectlyImported: Boolean = false,
    override val message: String = ApiMessages.Common.success200
): CommonResponse