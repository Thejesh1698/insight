package com.example.insight.features.user.repositories

import com.example.insight.common.models.entities.*
import jakarta.annotation.PostConstruct
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.beans.factory.annotation.Qualifier
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.jdbc.core.RowMapper
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate
import org.springframework.jdbc.support.GeneratedKeyHolder
import org.springframework.stereotype.Repository
import org.springframework.transaction.annotation.Transactional
import java.sql.Statement
import java.sql.Timestamp


@Repository
class UserRepository {

    @Autowired
    @Qualifier("userDatabaseJdbcTemplate")
    private lateinit var jdbcTemplate: JdbcTemplate

    lateinit var namedParameterJdbcTemplate: NamedParameterJdbcTemplate

    @PostConstruct
    fun initNamedParameterJdbcTemplate() {
        namedParameterJdbcTemplate = NamedParameterJdbcTemplate(jdbcTemplate)
    }

    fun getUserInterestedTopics(userId: Long): List<ArticleTopic> {

        val getUserInterestsQuery = "SELECT * " +
                "FROM " +
                "topics " +
                "INNER JOIN " +
                "user_topic_interests " +
                "using(topic_id)" +
                "WHERE user_id = ?"

        val topicMapper: RowMapper<ArticleTopic> = RowMapper { rs, _ ->
            ArticleTopic(
                rs.getLong("topic_id"),
                rs.getString("topic_name"),
                rs.getString("category"),
                rs.getTimestamp("created_at")
            )
        }

        return jdbcTemplate.query(getUserInterestsQuery, arrayOf(userId), topicMapper)
    }

    @Transactional("userDatabaseTransactionManager")
    fun upsertUserInterestedTopics(userId: Long, topicIds: List<Long>) {

        val deleteInterestsQuery = "DELETE " +
                "FROM " +
                "user_topic_interests " +
                "WHERE user_id = ?"
        jdbcTemplate.update(deleteInterestsQuery, userId)


        val userTopicsMappingQuery = "INSERT " +
                "INTO " +
                "user_topic_interests " +
                "(user_id, topic_id, created_at) " +
                "VALUES " +
                "(?, ?, now())"

        val batchArgs = topicIds.map { arrayOf(userId, it) }

        jdbcTemplate.batchUpdate(userTopicsMappingQuery, batchArgs)
    }

    fun insertUser(mobileNumber: String): User {

        val sql = "INSERT " +
                "INTO " +
                "users " +
                "(user_mobile_number) " +
                "VALUES " +
                "(?)"
        val keyHolder = GeneratedKeyHolder()

        jdbcTemplate.update(
            { connection ->
                val ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)
                ps.setString(1, mobileNumber)
                ps
            },
            keyHolder
        )

        val generatedKeys = keyHolder.keyList
        return User(
            generatedKeys[0]["user_id"] as Long,
            mobileNumber,
            null,
            null,
            generatedKeys[0]["created_at"] as Timestamp
        )
    }

    fun insertUser(userEmail: String, userName: String?): User {

        val sql = "INSERT " +
                "INTO " +
                "users " +
                "(user_email, user_name) " +
                "VALUES " +
                "(?, ?)"
        val keyHolder = GeneratedKeyHolder()

        jdbcTemplate.update(
            { connection ->
                val ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)
                ps.setString(1, userEmail)
                ps.setString(2, userName)
                ps
            },
            keyHolder
        )

        val generatedKeys = keyHolder.keyList
        return User(
            generatedKeys[0]["user_id"] as Long,
            null,
            userName,
            userEmail,
            generatedKeys[0]["created_at"] as Timestamp
        )
    }

    fun getUserByMobileNumber(mobileNumber: String): User? {

        val sql = "SELECT " +
                "* " +
                "FROM " +
                "users " +
                "WHERE user_mobile_number = ?"
        val args = arrayOf(mobileNumber)

        val userList = jdbcTemplate.query(sql, UserRowMapper(), *args)
        return userList.firstOrNull()
    }

    fun getUserByEmail(email: String): User? {

        val sql = "SELECT " +
                "* " +
                "FROM " +
                "users " +
                "WHERE user_email = ?"
        val args = arrayOf(email)

        val userList = jdbcTemplate.query(sql, UserRowMapper(), *args)
        return userList.firstOrNull()
    }

    fun getArticleReactions(): List<Reaction> {

        val sql = "SELECT " +
                "* " +
                "FROM " +
                "reactions "

        return jdbcTemplate.query(sql, ReactionRowMapper())
    }

    fun updateUserDetails(userId: Long, userName: String): Boolean {

        val query = "UPDATE " +
                "users " +
                "SET " +
                "user_name = ? " +
                "WHERE " +
                "user_id = ? "

        val rowsAffected = jdbcTemplate.update(query, userName, userId)

        return rowsAffected != 0
    }

    fun saveArticleBookmark(userId: Long, articleId: String): Long? {

        val query = "INSERT INTO " +
                "user_article_bookmarks " +
                "(user_id, article_id) " +
                "VALUES " +
                "(?, ?) " +
                "ON CONFLICT " +
                "DO NOTHING "

        val keyHolder = GeneratedKeyHolder()

        jdbcTemplate.update({ connection ->
            val ps = connection.prepareStatement(query, Statement.RETURN_GENERATED_KEYS)
            ps.setLong(1, userId)
            ps.setString(2, articleId)
            ps
        }, keyHolder)

        return keyHolder.keys?.get("bookmark_id") as? Long
    }

    fun deleteArticleBookmark(userId: Long, bookmarkId: Long): Boolean {

        val query = "DELETE FROM " +
                "user_article_bookmarks " +
                "where user_id = ? and bookmark_id = ?"

        val rowsAffected = jdbcTemplate.update(query, userId, bookmarkId)

        return rowsAffected != 0
    }

    fun addArticleToReadingHistory(userId: Long, articleId: String): Long? {

        val query = "INSERT INTO " +
                "user_article_reading_history " +
                "(user_id, article_id) " +
                "VALUES " +
                "(?, ?) " +
                "RETURNING history_id "

        val keyHolder = GeneratedKeyHolder()

        jdbcTemplate.update({ connection ->
            val ps = connection.prepareStatement(query, Statement.RETURN_GENERATED_KEYS)
            ps.setLong(1, userId)
            ps.setString(2, articleId)
            ps
        }, keyHolder)

        return keyHolder.keys?.get("history_id") as? Long
    }

    fun deleteArticleFromReadingHistory(userId: Long, historyId: Long): Boolean {

        val query = "DELETE FROM " +
                "user_article_reading_history " +
                "where user_id = ? and history_id = ?"

        val rowsAffected = jdbcTemplate.update(query, userId, historyId)

        return rowsAffected != 0
    }

    fun getUserArticleBookmarks(userId: Long, cursor: Long?, limit: Int): List<UserArticleBookmark> {

        val cursorCondition = if (cursor != null) "AND bookmark_id < :cursor" else ""
        val paramMap = mapOf(
            "userId" to userId,
            "cursor" to cursor,
            "limit" to limit
        )

        val query = "SELECT " +
                "bookmark_id, article_id " +
                "FROM " +
                "user_article_bookmarks " +
                "WHERE user_id = :userId $cursorCondition " +
                "ORDER BY bookmark_id DESC LIMIT :limit"

        return namedParameterJdbcTemplate.query(query, paramMap, UserArticleBookmarkRowMapper(userId))
    }

    fun getUserArticleReadingHistory(userId: Long, cursor: Long?, limit: Int): List<UserArticleReadingHistory> {

        val cursorCondition = if (cursor != null) "AND history_id < :cursor" else ""
        val paramMap = mapOf(
            "userId" to userId,
            "cursor" to cursor,
            "limit" to limit
        )

        val query = "SELECT " +
                "history_id, article_id " +
                "FROM " +
                "user_article_reading_history " +
                "WHERE user_id = :userId $cursorCondition " +
                "ORDER BY history_id DESC LIMIT :limit"

        return namedParameterJdbcTemplate.query(query, paramMap, UserArticleReadingHistoryRowMapper(userId))
    }

    fun getBookmarkIdsForArticles(userId: Long, articleIds: List<String>): HashMap<String, Long> {

        val paramMap = mapOf(
            "articleIds" to articleIds,
            "userId" to userId
        )
        val bookmarks = hashMapOf<String, Long>()

        val query = "SELECT " +
                "bookmark_id, article_id " +
                "FROM " +
                "user_article_bookmarks " +
                "WHERE user_id = :userId and article_id IN (:articleIds)"

        namedParameterJdbcTemplate.query(
            query, paramMap
        )
        { rs, _ ->

            bookmarks[rs.getString("article_id")] = rs.getLong("bookmark_id")
        }

        return bookmarks
    }

    fun getUserOnboardingStatus(userId: Long): Boolean? {

        val query = "SELECT " +
                "COUNT(*) > 0 as preferences_submitted " +
                "FROM " +
                "user_topic_interests " +
                "WHERE user_id = :userId"

        val paramMap = mapOf(
            "userId" to userId
        )

        return namedParameterJdbcTemplate.queryForObject(
            query, paramMap
        )
        { rs, _ ->
            rs.getBoolean("preferences_submitted")
        }
    }

    fun getUserContentPreferences(userId: Long, contentIds: List<String>) : List<Pair<String, String>>{

        val paramMap = mapOf(
                "contentIds" to contentIds,
                "userId" to userId
        )
        val query = "SELECT " +
                "content_id, preference_type " +
                "FROM " +
                "user_content_preferences " +
                "WHERE user_id = :userId and content_id IN (:contentIds)"

        return namedParameterJdbcTemplate.query(
                query, paramMap
        )
        { rs, _ ->

            Pair(rs.getString("content_id"), rs.getString("preference_type"))
        }
    }
}