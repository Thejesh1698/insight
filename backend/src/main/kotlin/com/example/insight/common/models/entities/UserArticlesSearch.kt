package com.example.insight.common.models.entities

import org.postgresql.jdbc.PgArray
import org.springframework.jdbc.core.RowMapper
import java.sql.ResultSet
import java.sql.Timestamp


data class UserArticlesSearch(
    val searchId: Long,
    val userId: Long,
    val searchResults: List<String>,
    val mlServerResponse: String,
    val createdAt: Timestamp
)

class UserArticlesSearchRowMapper : RowMapper<UserArticlesSearch> {

    override fun mapRow(rs: ResultSet, rowNum: Int): UserArticlesSearch {

        return UserArticlesSearch(
            searchId = rs.getLong("search_id"),
            userId = rs.getLong("user_id"),
            searchResults = ((rs.getArray("search_results") as PgArray).array as Array<String>).toList(),
            mlServerResponse = rs.getString("ml_server_response"),
            createdAt = rs.getTimestamp("created_at")
        )
    }
}