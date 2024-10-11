package com.example.insight.features.userAuthentication.repositories

import com.example.insight.common.models.entities.User
import com.example.insight.common.models.entities.UserAuthToken
import com.example.insight.common.models.entities.UserAuthDetailsRowMapper
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.beans.factory.annotation.Qualifier
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Repository


@Repository
class UserAuthenticationRepository {

    @Autowired
    @Qualifier("userDatabaseJdbcTemplate")
    private lateinit var jdbcTemplate: JdbcTemplate

    fun insertAuthToken(authToken: String, userId: Long, ttl: Long) {

        val query = "INSERT " +
                "INTO " +
                "user_auth_tokens " +
                "(user_id, auth_token, ttl) " +
                "VALUES (?, ?, ?);"
        jdbcTemplate.update(query, userId, authToken, ttl)
    }

    fun getAuthenticationDetails(authToken: String): Pair<User, UserAuthToken>? {

        val query = "SELECT " +
                "* " +
                "FROM " +
                "user_auth_tokens " +
                "INNER JOIN " +
                "users " +
                "using(user_id) " +
                "where auth_token = ?"

        val userAuthTokenList = jdbcTemplate.query(query, UserAuthDetailsRowMapper(), authToken)
        return userAuthTokenList.firstOrNull()
    }

    fun deleteAuthToken(userId: Long, authToken: String): Boolean {

        val query = "DELETE " +
                "FROM " +
                "user_auth_tokens " +
                "where user_id = ? and auth_token = ?"

        val rowsAffected = jdbcTemplate.update(query, userId, authToken)
        return rowsAffected != 0
    }
}