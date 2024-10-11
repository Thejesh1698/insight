package com.example.insight.features.feed.repositories

import com.example.insight.common.models.entities.UserFeedDetails
import com.example.insight.common.models.entities.UserFeedDetailsRowMapper
import com.example.insight.features.feed.utils.FeedConstants
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.beans.factory.annotation.Qualifier
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Repository


@Repository
class FeedRepository {

    @Autowired
    @Qualifier("userDatabaseJdbcTemplate")
    private lateinit var jdbcTemplate: JdbcTemplate

    fun insertFeedSession(userId: Long, feedType: FeedConstants.FeedType): Long? {

        val insertSql = "INSERT " +
                "INTO " +
                "feed_sessions " +
                "(user_id, feed_type) " +
                "VALUES (?, ?) " +
                "RETURNING session_id"
        val params = arrayOf(userId, feedType.toString())

        return jdbcTemplate.queryForObject(insertSql, params) { rs, _ ->
            rs.getLong("session_id")
        }
    }

    fun insertFeedDetails(sessionId: Long, articleIds: List<String>, serverResponse: String): Long? {

        val insertSql = "INSERT " +
                "INTO " +
                "feed_details " +
                "(session_id, ml_server_response, articles) " +
                "VALUES (?, ?::jsonb, ?) " +
                "RETURNING feed_id"
        val params = arrayOf(sessionId, serverResponse, articleIds.toTypedArray())

        val feedIds = jdbcTemplate.query(
            insertSql,
            params
        ) { rs, _ -> rs.getLong("feed_id") }

        return feedIds.firstOrNull()
    }

    fun getExistingFeedSessionDetails(userId: Long, sessionId: Long): List<UserFeedDetails> {

        val sql = "SELECT " +
                "fd.* " +
                "FROM " +
                "feed_sessions as fs " +
                "INNER JOIN " +
                "feed_details as fd " +
                "USING(session_id) " +
                "WHERE user_id = ? and session_id = ? " +
                "ORDER BY fd.created_at DESC"
        val args = arrayOf(userId, sessionId)

        return jdbcTemplate.query(sql, UserFeedDetailsRowMapper(), *args)
    }

    fun getLastFeedSessionDetails(userId: Long, feedType: FeedConstants.FeedType): UserFeedDetails? {

        val sql = "SELECT " +
                "fd.* " +
                "FROM " +
                "feed_sessions as fs " +
                "INNER JOIN " +
                "feed_details as fd " +
                "USING(session_id) " +
                "WHERE user_id = ? and feed_type = ? " +
                "ORDER BY fd.created_at DESC LIMIT 1"
        val args = arrayOf(userId, feedType.toString())

        return jdbcTemplate.query(sql, UserFeedDetailsRowMapper(), *args).firstOrNull()
    }
}