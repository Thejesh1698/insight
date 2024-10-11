package com.example.insight.features.investments.utils

import java.time.LocalDate
import java.time.LocalTime


object UserInvestmentsConstants {
    enum class ImportType {
        NEW, REFRESH
    }
    enum class BROKERS(val smallCaseEnum: String, val logoUrl: String) {
        FIVE_PAISA("fivepaisa", "add-your-custom-logo-url-here"),
        ANGEL_BROKING("angelbroking", "add-your-custom-logo-url-here"),
        DHAN("dhan", "add-your-custom-logo-url-here"),
        FISDOM("fisdom", "add-your-custom-logo-url-here"),
        GROWW("groww", "add-your-custom-logo-url-here"),
        IIFL("iifl", "add-your-custom-logo-url-here"),
        MOTILAL("motilal", "add-your-custom-logo-url-here"),
        TRUSTLINE("trustline", "add-your-custom-logo-url-here"),
        UPSTOX("upstox", "add-your-custom-logo-url-here"),
        KITE("kite", "add-your-custom-logo-url-here");

        companion object {
            fun fromSmallCaseEnum(smallCaseEnum: String): BROKERS? {
                return values().find { it.smallCaseEnum == smallCaseEnum }
            }
        }
    }

    const val STOCK_HOLDINGS_IMPORT_LIMIT_PER_DAY = 1
    const val STOCKS_FETCH_MAX_POLLING_COUNT = 5

    enum class SmallCaseTransactionTypes {
        HOLDINGS_IMPORT
    }

    enum class SmallCaseTransactionStatus {
        STARTED, AUTHORIZED, COMPLETED
    }

    enum class StockExchanges {
        NSE, BSE
    }

    /**
     * The list is in IST format
     */
    val INDIAN_TRADE_MARKET_HOLIDAYS_LIST = listOf(
        LocalDate.of(2024, 1, 22),
        LocalDate.of(2024, 1, 26),
        LocalDate.of(2024, 3, 8),
        LocalDate.of(2024, 3, 25),
        LocalDate.of(2024, 3, 29),
        LocalDate.of(2024, 4, 11),
        LocalDate.of(2024, 4, 17),
        LocalDate.of(2024, 5, 1),
        LocalDate.of(2024, 5, 20),
        LocalDate.of(2024, 6, 17),
        LocalDate.of(2024, 7, 17),
        LocalDate.of(2024, 8, 15),
        LocalDate.of(2024, 10, 2),
        LocalDate.of(2024, 11, 1),
        LocalDate.of(2024, 11, 15),
        LocalDate.of(2024, 12, 25)
    )

    val INDIAN_TRADE_MARKET_OPEN_IST: LocalTime = LocalTime.of(9, 15)
    val INDIAN_TRADE_MARKET_CLOSE_IST: LocalTime = LocalTime.of(15, 30)
}