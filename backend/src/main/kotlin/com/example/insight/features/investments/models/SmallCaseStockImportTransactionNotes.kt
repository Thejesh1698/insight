package com.example.insight.features.investments.models

import com.example.insight.features.investments.utils.UserInvestmentsConstants

data class SmallCaseStockImportTransactionNotes (
    val userId: Long,
    val importType: UserInvestmentsConstants.ImportType
)