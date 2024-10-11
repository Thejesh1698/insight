package com.example.insight.common.models.entities

import org.springframework.jdbc.core.RowMapper
import java.sql.ResultSet
import java.sql.Timestamp


data class UserAuthToken(
    val authTokenId: Long,
    val userId: Long,
    val authToken: String,
    val ttl: Long,
    val createdAt: Timestamp
)

class UserAuthDetailsRowMapper : RowMapper<Pair<User, UserAuthToken>> {

    override fun mapRow(rs: ResultSet, rowNum: Int): Pair<User, UserAuthToken> {
        val user = User(
            userId = rs.getLong("user_id"),
            mobileNumber = rs.getString("user_mobile_number"),
            userName = rs.getString("user_name"),
            userEmail = rs.getString("user_email"),
            createdAt = rs.getTimestamp("created_at")
        )

        val authTokenDetails = UserAuthToken(
            authTokenId = rs.getLong("auth_token_id"),
            userId = rs.getLong("user_id"),
            authToken = rs.getString("auth_token"),
            ttl = rs.getLong("ttl"),
            createdAt = rs.getTimestamp("created_at")
        )

        return Pair(user, authTokenDetails)
    }
}