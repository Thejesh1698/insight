package com.example.insight.common.utils.thirdParties.smallCase.utils


object SmallCaseConstants {
    enum class ApiEndPoints(val value: String) {
        HOLDINGS_IMPORT_TRANSACTION("gateway/${SMALL_CASE_GATEWAY_NAME}/transaction"),
    }

    const val SMALL_CASE_GATEWAY_NAME = "<add your small case gateway name here>"
    const val GATEWAY_AUTH_TOKEN_HEADER = "x-gateway-authtoken"
    const val GATEWAY_SECRET_HEADER = "x-gateway-secret"
}