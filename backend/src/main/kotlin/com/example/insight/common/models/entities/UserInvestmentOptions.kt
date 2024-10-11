package com.example.insight.common.models.entities

import org.springframework.jdbc.core.RowMapper
import java.sql.ResultSet
import java.sql.Timestamp


data class UserInvestmentOption(
    val investmentOptionId: Long,
    val name: String,
    var nseTicker: String?,
    var bseTicker: String?,
    val createdAt: Timestamp
)

class UserInvestmentOptionRowMapper : RowMapper<UserInvestmentOption> {

    override fun mapRow(rs: ResultSet, rowNum: Int): UserInvestmentOption {
        return UserInvestmentOption(
            investmentOptionId = rs.getLong("investment_option_id"),
            name = rs.getString("name"),
            nseTicker = rs.getString("nse_ticker"),
            bseTicker = rs.getString("bse_ticker"),
            createdAt = rs.getTimestamp("created_at")
        )
    }
}