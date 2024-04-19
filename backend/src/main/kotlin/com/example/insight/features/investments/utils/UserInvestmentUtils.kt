package com.example.insight.features.investments.utils

import com.example.insight.features.investments.utils.UserInvestmentsConstants.INDIAN_TRADE_MARKET_CLOSE_IST
import com.example.insight.features.investments.utils.UserInvestmentsConstants.INDIAN_TRADE_MARKET_HOLIDAYS_LIST
import com.example.insight.features.investments.utils.UserInvestmentsConstants.INDIAN_TRADE_MARKET_OPEN_IST
import org.springframework.stereotype.Service
import java.time.DayOfWeek
import java.time.ZoneId
import java.time.ZonedDateTime

@Service
class UserInvestmentUtils {

    fun isIndianTradeMarketLiveNow(): Boolean {
        val nowIST = ZonedDateTime.now(ZoneId.of("Asia/Kolkata"))
        val todayIST = nowIST.toLocalDate()
        val currentTimeIST = nowIST.toLocalTime()
        val dayOfWeek = nowIST.dayOfWeek

        if (dayOfWeek == DayOfWeek.SATURDAY || dayOfWeek == DayOfWeek.SUNDAY) {
            return false
        }

        if (INDIAN_TRADE_MARKET_HOLIDAYS_LIST.contains(todayIST)) {
            return false
        }

        if (currentTimeIST.isBefore(INDIAN_TRADE_MARKET_OPEN_IST) || currentTimeIST.isAfter(
                INDIAN_TRADE_MARKET_CLOSE_IST
            )
        ) {
            return false
        }

        return true
    }
}