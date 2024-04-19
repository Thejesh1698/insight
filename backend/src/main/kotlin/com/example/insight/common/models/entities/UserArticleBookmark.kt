package com.example.insight.common.models.entities

import org.springframework.jdbc.core.RowMapper
import java.sql.ResultSet

data class UserArticleBookmark (
    val bookmarkId: Long,
    val userId: Long,
    val articleId: String
)

class UserArticleBookmarkRowMapper(val userId: Long) : RowMapper<UserArticleBookmark> {

    override fun mapRow(rs: ResultSet, rowNum: Int): UserArticleBookmark {
        return UserArticleBookmark(
            bookmarkId = rs.getLong("bookmark_id"),
            userId = userId,
            articleId = rs.getString("article_id")
        )
    }
}