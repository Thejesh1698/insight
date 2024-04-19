package com.example.insight.common.models.entities

import org.postgresql.jdbc.PgArray
import org.springframework.jdbc.core.RowMapper
import java.sql.ResultSet
import java.sql.Timestamp


data class UserFeedDetails(
    val feedId: Long,
    val sessionId: Long,
    val articles: List<String>,
    val createdAt: Timestamp
)

class UserFeedDetailsRowMapper : RowMapper<UserFeedDetails> {

    override fun mapRow(rs: ResultSet, rowNum: Int): UserFeedDetails {
        return UserFeedDetails(
            feedId = rs.getLong("feed_id"),
            sessionId = rs.getLong("session_id"),
            articles = ((rs.getArray("articles") as PgArray).array as Array<String>).toList(),
            createdAt = rs.getTimestamp("created_at")
        )
    }
}
