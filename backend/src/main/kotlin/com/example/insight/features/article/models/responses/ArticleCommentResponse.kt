package com.example.insight.features.article.models.responses

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.models.responses.CommonResponse
import org.springframework.jdbc.core.RowMapper
import java.sql.ResultSet
import java.sql.Timestamp

data class ArticleCommentResponse(
    val commentId: Long,
    val articleId: String,
    val commentText: String,
    val authorInfo: ArticleCommentUserInfo,
    val postedAt: Timestamp
) {
    data class ArticleCommentUserInfo(
        val userId: Long,
        val userName: String
    )
}

data class ArticleCommentsResponse(
    val comments: List<ArticleCommentResponse>, override val message: String = ApiMessages.Common.success200
) : CommonResponse

class UserArticleCommentRowMapper : RowMapper<ArticleCommentResponse> {

    override fun mapRow(rs: ResultSet, rowNum: Int): ArticleCommentResponse {
        return ArticleCommentResponse(
            commentId = rs.getLong("comment_id"),
            articleId = rs.getString("article_id"),
            commentText = rs.getString("comment_text"),
            authorInfo = ArticleCommentResponse.ArticleCommentUserInfo(
                userId = rs.getLong("author_id"),
                userName = rs.getString("author_name")
            ),
            postedAt = rs.getTimestamp("posted_at")
        )
    }
}