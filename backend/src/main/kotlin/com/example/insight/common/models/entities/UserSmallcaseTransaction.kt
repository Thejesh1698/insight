package com.example.insight.common.models.entities

import com.example.insight.features.investments.utils.UserInvestmentsConstants
import org.springframework.jdbc.core.RowMapper
import java.sql.ResultSet
import java.sql.Timestamp

data class UserSmallcaseTransaction (
    val transactionRef: Long,
    val userId: Long,
    val smallcaseTransactionId: String,
    val transactionType: UserInvestmentsConstants.SmallCaseTransactionTypes,
    val transactionStatus: UserInvestmentsConstants.SmallCaseTransactionStatus,
    val expireAt: Long,
    val vendorResponse: String,
    val broker: UserInvestmentsConstants.BROKERS?,
    val lastUpdated: Timestamp,
    val createdAt: Timestamp
)

class UserSmallcaseTransactionRowMapper : RowMapper<UserSmallcaseTransaction> {

    override fun mapRow(rs: ResultSet, rowNum: Int): UserSmallcaseTransaction {
        return UserSmallcaseTransaction(
            transactionRef = rs.getLong("id"),
            userId = rs.getLong("user_id"),
            smallcaseTransactionId = rs.getString("smallcase_transaction_id"),
            transactionType = UserInvestmentsConstants.SmallCaseTransactionTypes.valueOf(
                rs.getString("transaction_type")
            ),
            transactionStatus = UserInvestmentsConstants.SmallCaseTransactionStatus.valueOf(
                rs.getString("transaction_status")
            ),
            expireAt = rs.getLong("expire_at"),
            vendorResponse = rs.getString("vendor_response"),
            broker = rs.getString("broker")?.let{UserInvestmentsConstants.BROKERS.valueOf(it)},
            lastUpdated = rs.getTimestamp("last_updated"),
            createdAt = rs.getTimestamp("created_at")
        )
    }
}