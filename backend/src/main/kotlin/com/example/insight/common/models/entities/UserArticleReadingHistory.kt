package com.example.insight.common.models.entities

import org.springframework.jdbc.core.RowMapper
import java.sql.ResultSet

data class UserArticleReadingHistory (
    val historyId: Long,
    val userId: Long,
    val articleId: String
)

class UserArticleReadingHistoryRowMapper(val userId: Long) : RowMapper<UserArticleReadingHistory> {

    override fun mapRow(rs: ResultSet, rowNum: Int): UserArticleReadingHistory {
        return UserArticleReadingHistory(
            historyId = rs.getLong("history_id"),
            userId = userId,
            articleId = rs.getString("article_id")
        )
    }
}