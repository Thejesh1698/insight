package com.example.insight.features.footPrints.repositories

import com.example.insight.features.footPrints.utils.FootPrintsConstants
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.beans.factory.annotation.Qualifier
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Repository


@Repository
class FootPrintsRepository {

    @Autowired
    @Qualifier("mlDatabaseJdbcTemplate")
    private lateinit var jdbcTemplate: JdbcTemplate

    fun insertArticleVisibilityTracking(
        userId: Long,
        activityId: Long,
        contentId: String,
        contentPosition: String,
        activityType: FootPrintsConstants.ARTICLE_INTERACTIONS_FEATURE_TYPES
    ) {

        val query = "INSERT " +
                "INTO " +
                "user_article_interactions " +
                "(user_id, activity_id, article_id, content_position, activity_type, is_summary_read) " +
                "VALUES (?, ?, ?, ?::jsonb, ?, FALSE) " +
                "ON CONFLICT (user_id, activity_type, activity_id, article_id) " +
                "DO NOTHING "
        jdbcTemplate.update(
            query,
            userId,
            activityId,
            contentId,
            contentPosition,
            activityType.toString()
        )
    }

    fun updateArticleOpenTracking(
        userId: Long,
        activityId: Long,
        contentId: String,
        activityType: FootPrintsConstants.ARTICLE_INTERACTIONS_FEATURE_TYPES
    ) {

        val query = "UPDATE " +
                "user_article_interactions " +
                "SET " +
                "is_article_opened = true " +
                "WHERE user_id = ? and activity_id = ? and article_id = ? and activity_type = ?"
        jdbcTemplate.update(
            query,
            userId,
            activityId,
            contentId,
            activityType.toString()
        )
    }

    fun updateArticleSummaryReadTracking(
        userId: Long,
        activityId: Long,
        contentId: String,
        activityType: FootPrintsConstants.ARTICLE_INTERACTIONS_FEATURE_TYPES
    ) {

        val query = "UPDATE " +
                "user_article_interactions " +
                "SET " +
                "is_summary_read = true " +
                "WHERE user_id = ? and activity_id = ? and article_id = ? and activity_type = ?"
        jdbcTemplate.update(
            query,
            userId,
            activityId,
            contentId,
            activityType.toString()
        )
    }
}