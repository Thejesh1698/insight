package com.example.insight.features.articlesSearch.repositories

import com.example.insight.common.models.entities.*
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.beans.factory.annotation.Qualifier
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Repository

@Repository
class ArticlesSearchRepository {

    @Autowired
    @Qualifier("userDatabaseJdbcTemplate")
    private lateinit var jdbcTemplate: JdbcTemplate

    fun storeSearchQueryResults(userId: Long, userInputtedQuery: String, cleanedQuery: String, searchResults: List<String>, mlServerResponseString: String): Long? {

        val insertSql = "INSERT " +
                "INTO " +
                "user_articles_search " +
                "(user_id, user_inputted_query, cleaned_query, ml_server_response, search_results) " +
                "VALUES (?, ?, ?, ?::jsonb, ?) " +
                "RETURNING search_id"
        val params = arrayOf(userId, userInputtedQuery, cleanedQuery, mlServerResponseString, searchResults.toTypedArray())

        val searchIds = jdbcTemplate.query(
            insertSql,
            params
        ) { rs, _ -> rs.getLong("search_id") }

        return searchIds.firstOrNull()
    }

    fun getExistingArticlesSearchDetails(userId: Long, searchId: Long): UserArticlesSearch? {

        val query = "SELECT " +
                "* " +
                "FROM " +
                "user_articles_search " +
                "where search_id = ? and user_id = ?"

        val userAuthTokenList = jdbcTemplate.query(query, UserArticlesSearchRowMapper(), searchId, userId)
        return userAuthTokenList.firstOrNull()
    }

    fun saveAiGeneratedSearchSummary(searchId: Long, summaryInfo: String) {

        val query = "UPDATE " +
                "user_articles_search " +
                "SET " +
                "ai_generated_search_summary = ?::jsonb " +
                "WHERE search_id = ?"
        jdbcTemplate.update(
            query,
            summaryInfo,
            searchId
        )
    }
}