package com.example.insight.common.utils.thirdParties.kite.utils


object KiteConstants {
    enum class ApiEndPoints(val value: String) {
        INSTRUMENTS_DOWNLOAD("/instruments"),
        INSTRUMENT_HISTORIC_PRICES("/instruments/historical"),
        OHLC_QUOTE("/quote/ohlc"),
        REFRESH_TOKEN("/session/refresh_token"),
    }

    const val KITE_CONNECT_API_DOMAIN = "https://api.kite.trade"
    const val HISTORIC_PRICES_DATE_INPUT_FORMAT = "yyyy-MM-dd+00:00:00"
}