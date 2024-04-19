package com.example.insight.common.models.entities

import org.springframework.jdbc.core.RowMapper
import java.sql.ResultSet
import java.sql.Timestamp


data class User(
    val userId: Long,
    val mobileNumber: String?,
    val userName: String?,
    val userEmail: String?,
    val createdAt: Timestamp
)

class UserRowMapper : RowMapper<User> {

    override fun mapRow(rs: ResultSet, rowNum: Int): User {
        return User(
            userId = rs.getLong("user_id"),
            mobileNumber = rs.getString("user_mobile_number"),
            userName = rs.getString("user_name"),
            userEmail = rs.getString("user_email"),
            createdAt = rs.getTimestamp("created_at")
        )
    }
}