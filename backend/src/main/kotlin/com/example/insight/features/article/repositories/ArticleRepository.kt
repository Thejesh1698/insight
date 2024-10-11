package com.example.insight.features.article.repositories

import com.example.insight.common.models.entities.Article
import com.example.insight.common.models.entities.ArticleSource
import com.example.insight.common.models.entities.ArticleTopic
import com.example.insight.common.models.entities.UserContentPreference
import com.example.insight.features.article.models.responses.ArticleCommentResponse
import com.example.insight.features.article.models.responses.ArticleInfoForUserResponse
import com.example.insight.features.article.models.responses.ArticleSourceInfoForUserResponse
import com.example.insight.features.article.models.responses.UserArticleCommentRowMapper
import com.example.insight.features.article.utils.ArticleConstants
import com.example.insight.common.models.entities.*
import com.example.insight.features.article.models.requests.*
import jakarta.annotation.PostConstruct
import org.bson.types.ObjectId
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.beans.factory.annotation.Qualifier
import org.springframework.data.mongodb.core.MongoTemplate
import org.springframework.data.mongodb.core.aggregation.Aggregation.*
import org.springframework.data.mongodb.core.aggregation.LookupOperation.newLookup
import org.springframework.data.mongodb.core.query.Criteria
import org.springframework.data.mongodb.core.query.Query
import org.springframework.data.mongodb.core.query.Update
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.jdbc.core.RowMapper
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate
import org.springframework.jdbc.support.GeneratedKeyHolder
import org.springframework.stereotype.Repository
import java.sql.Statement
import java.sql.Timestamp
import java.util.*


@Repository
class ArticleRepository {

    @Autowired
    lateinit var mongoTemplate: MongoTemplate

    @Autowired
    @Qualifier("userDatabaseJdbcTemplate")
    lateinit var jdbcTemplateForUserDb: JdbcTemplate

    lateinit var namedParameterJdbcTemplateForUserDb: NamedParameterJdbcTemplate

    @PostConstruct
    fun initNamedParameterJdbcTemplate() {
        namedParameterJdbcTemplateForUserDb = NamedParameterJdbcTemplate(jdbcTemplateForUserDb)
    }

    fun insertArticle(
        request: InsertArticleRequest
    ): ObjectId? {

        val newArticleIdObj = ObjectId()

        val article = Article(
            newArticleIdObj,
            request.url,
            request.title,
            request.shortDescription,
            request.publishedTime,
            request.lastUpdatedTime,
            request.sourceId,
            request.tags,
            request.articleImage,
            request.categoryName,
            request.authors,
            request.isPremiumArticle,
            hashMapOf()
        )

        mongoTemplate.insert(article, "articles")

        return newArticleIdObj
    }

    fun getArticleSourceById(sourceId: ObjectId): ArticleSource? {

        val sourceQuery: Query = Query().addCriteria(Criteria.where("_id").`is`(sourceId))
        return mongoTemplate.findOne(sourceQuery, ArticleSource::class.java)
    }

    fun getArticleSourceByName(sourceName: String): ArticleSource? {

        val sourceQuery: Query = Query().addCriteria(Criteria.where("name").`is`(sourceName))
        return mongoTemplate.findOne(sourceQuery, ArticleSource::class.java)
    }

    fun fetchRegisteredArticles(
        urls: List<String>
    ): List<Article> {

        val query = Query().addCriteria(Criteria.where("url").`in`(urls))
        return mongoTemplate.find(query, Article::class.java)
    }

    fun getArticle(articleId: String): Article? {

        val query = Query(Criteria.where("articleId").`is`(articleId))
        return mongoTemplate.findOne(query, Article::class.java)
    }

    fun updateArticle(
        articleId: String,
        request: UpdateArticleRequest
    ): Boolean? {

        val query = Query(Criteria.where("_id").`is`(ObjectId(articleId)))

        val update = Update()
        update.set("title", request.title)
        update.set("shortDescription", request.shortDescription)
        update.set("publishedTime", request.publishedTime)
        update.set("lastUpdatedTime", request.lastUpdatedTime)
        update.set("tags", request.tags)
        update.set("articleImageUrl", request.articleImage)
        update.set("authors", request.authors)
        update.set("isPremiumArticle", request.isPremiumArticle)
        update.set("cleanedText", request.cleanedText)

        val result = mongoTemplate.updateFirst(query, update, Article::class.java)

        return if (result.matchedCount > 0) {
            result.modifiedCount > 0
        } else {
            null // Article not found
        }
    }

    fun getAllArticleTopics(): List<ArticleTopic> {

        val query = "SELECT * " +
                "FROM " +
                "topics "

        val topicMapper: RowMapper<ArticleTopic> = RowMapper { rs, _ ->
            ArticleTopic(
                rs.getLong("topic_id"),
                rs.getString("topic_name"),
                rs.getString("category"),
                rs.getTimestamp("created_at")
            )
        }

        return jdbcTemplateForUserDb.query(query, topicMapper)
    }

    fun getArticles(articleIds: List<ObjectId>): List<ArticleInfoForUserResponse> {

        val lookupOperation = newLookup()
            .from("article_sources")
            .localField("source_id")
            .foreignField("_id")
            .`as`("sourceInfo")

        val aggregation = newAggregation(
            match(Criteria.where("_id").`in`(articleIds)),
            lookupOperation,
            unwind("sourceInfo", true),
            project()
                .andExclude("_id")
                .and("_id").`as`("articleId")
                .and("url").`as`("url")
                .and("title").`as`("title")
                .and("short_description").`as`("shortDescription")
                .and("published_time").`as`("publishedTime")
                .and("last_updated_time").`as`("lastUpdatedTime")
                .and("tags").`as`("tags")
                .and("image_url").`as`("articleImageUrl")
                .and("category").`as`("category")
                .and("authors").`as`("authors")
                .and("is_premium_article").`as`("isPremiumArticle")
                .and("reactions").`as`("reactions")
                .and("sourceInfo._id").`as`("source.sourceId")
                .and("sourceInfo.name").`as`("source.sourceName")
                .and("sourceInfo.logo_url").`as`("source.sourceLogo")
                .and("ai_generated_info").`as`("aiGeneratedInfo")
                .and("podcast_episode_info").`as`("podcast_episode_info")
                .and("comments_info").`as`("comments_info")
        )

        val results = mongoTemplate.aggregate(aggregation, "articles", ArticleInfoForUserResponse::class.java)
        return results.mappedResults
    }

    fun upsertUserArticleReaction(userId: Long, articleId: String, reactionId: Long) {

        val query = "INSERT " +
                "INTO " +
                "user_article_reactions " +
                "( " +
                "   user_id, article_id, reaction_id " +
                ") " +
                "values " +
                "(?, ?, ?) " +
                "ON CONFLICT " +
                "(user_id, article_id) " +
                "DO UPDATE SET " +
                "reaction_id = ? "

        jdbcTemplateForUserDb.update(query, userId, articleId, reactionId, reactionId)
    }

    fun deleteUserArticleReaction(userId: Long, articleId: String, reactionId: Long): Boolean {

        val query = "DELETE " +
                "FROM " +
                "user_article_reactions " +
                "WHERE " +
                "user_id = ? and article_id = ? and reaction_id = ?"

        val rowsAffected = jdbcTemplateForUserDb.update(query, userId, articleId, reactionId)

        return rowsAffected != 0
    }

    fun incrementArticleReactionCount(articleId: String, reactionId: Long): Boolean {

        val query = Query.query(Criteria.where("_id").`is`(articleId))
        val update = Update().inc("reactions.$reactionId", 1)

        val result = mongoTemplate.updateFirst(query, update, Article::class.java)

        return result.matchedCount > 0
    }

    fun decrementArticleReactionCount(articleId: String, reactionId: Long): Boolean {

        val query = Query.query(Criteria.where("_id").`is`(articleId))
        val update = Update().inc("reactions.$reactionId", -1)

        val result = mongoTemplate.updateFirst(query, update, Article::class.java)

        return result.matchedCount > 0
    }

    fun incrementArticleCommentsCount(articleId: String): Boolean {

        val query = Query.query(Criteria.where("_id").`is`(articleId))
        val update = Update().inc("comments_info.count", 1)

        val result = mongoTemplate.updateFirst(query, update, Article::class.java)

        return result.matchedCount > 0
    }

    fun decrementArticleCommentsCount(articleId: String): Boolean {

        val query = Query.query(Criteria.where("_id").`is`(articleId))
        val update = Update().inc("comments_info.count", -1)

        val result = mongoTemplate.updateFirst(query, update, Article::class.java)

        return result.matchedCount > 0
    }

    fun getUserArticleReactions(userId: Long, articleIds: List<String>): HashMap<String, Int> {

        val query = "SELECT " +
                "article_id, reaction_id " +
                "FROM " +
                "user_article_reactions " +
                "WHERE user_id = :userId AND article_id IN (:articleIds)"

        val paramMap = mapOf(
            "userId" to userId,
            "articleIds" to articleIds
        )

        val resultMap = HashMap<String, Int>()

        namedParameterJdbcTemplateForUserDb.query(
            query, paramMap
        )
        { rs, _ ->

            val articleId = rs.getString("article_id")
            val reactionId = rs.getInt("reaction_id")

            resultMap[articleId] = reactionId
        }

        return resultMap
    }

    fun upsertArticleComment(userId: Long, articleId: String, commentText: String): Pair<Long, Timestamp> {

        val query = "INSERT " +
                "INTO " +
                "article_comments " +
                "( " +
                "   user_id, article_id, comment_text " +
                ") " +
                "values " +
                "(?, ?, ?) "
        val keyHolder = GeneratedKeyHolder()

        jdbcTemplateForUserDb.update(
            { connection ->
                val ps = connection.prepareStatement(query, Statement.RETURN_GENERATED_KEYS)
                ps.setLong(1, userId)
                ps.setString(2, articleId)
                ps.setString(3, commentText)
                ps
            },
            keyHolder
        )

        val generatedKeys = keyHolder.keyList
        val commentId = generatedKeys[0]["comment_id"] as Long
        val commentCreatedAt = generatedKeys[0]["created_at"] as Timestamp
        return Pair(commentId, commentCreatedAt)
    }

    fun updateAiGeneratedInfoForArticle(articleId: String, request: AiGeneratedInfoForArticleRequest): Boolean {

        val query = Query(Criteria.where("articleId").`is`(articleId))

        val update = Update()
        val summaryModel = request.summary
        val titleModel = request.title
        val createdAt = Date()

        update.set("ai_generated_info.summary.${request.model}.value", summaryModel.value)
        update.set("ai_generated_info.summary.${request.model}.additional_info", summaryModel.additionalInfo)
        update.set("ai_generated_info.summary.${request.model}.generated_at", createdAt)

        update.set("ai_generated_info.title.${request.model}.value", titleModel.value)
        update.set("ai_generated_info.title.${request.model}.additional_info", titleModel.additionalInfo)
        update.set("ai_generated_info.title.${request.model}.generated_at", createdAt)

        if(request.isFinancialNews != null) {
            update.set("ai_generated_info.is_financial_news", request.isFinancialNews)
        }

        if(request.isRelevantForIndia != null) {
            update.set("ai_generated_info.is_relevant_for_india", request.isRelevantForIndia)
        }

        val result = mongoTemplate.updateFirst(query, update, Article::class.java)

        return if (result.matchedCount > 0) {
            result.modifiedCount > 0
        } else {
            false
        }
    }

    fun deleteArticleComment(userId: Long, articleId: String, commentId: Long): Boolean {

        val query = "DELETE " +
                "FROM " +
                "article_comments " +
                "WHERE " +
                "user_id = ? and article_id = ? and comment_id = ?"

        val rowsAffected = jdbcTemplateForUserDb.update(query, userId, articleId, commentId)

        return rowsAffected != 0
    }

    fun getArticleComments(articleId: String): List<ArticleCommentResponse> {

        val query = "SELECT " +
                "comment_id, article_id, comment_text, ac.created_at as posted_at, " +
                "us.user_id as author_id, us.user_name as author_name " +
                "FROM " +
                "article_comments as ac " +
                "inner join " +
                "users as us " +
                "using (user_id) " +
                "where article_id = ? "
        val args = arrayOf(articleId)

        return jdbcTemplateForUserDb.query(query, UserArticleCommentRowMapper(), *args)
    }

    fun getArticleSources(sourceIds: List<ObjectId>): List<ArticleSourceInfoForUserResponse> {

        val aggregation = newAggregation(
            match(Criteria.where("_id").`in`(sourceIds)),
            project()
                .andExclude("_id")
                .and("_id").`as`("sourceId")
                .and("logo_url").`as`("logoURL")
                .and("name").`as`("name")
                .and("source_type").`as`("sourceType")
                .and("podcast_info").`as`("podcastInfo")
        )

        val results = mongoTemplate.aggregate(aggregation, "article_sources", ArticleSourceInfoForUserResponse::class.java)
        return results.mappedResults
    }

    fun saveUserContentPreference(userPreference: UserContentPreference) {

        val sql = "INSERT " +
                  "INTO " +
                  "user_content_preferences"+
                  "(" +
                    "user_id, content_id, content_type, preference_type "+
                  ")" +
                  "VALUES (?, ?, ?, ?)"

        jdbcTemplateForUserDb.update(sql,
                userPreference.userId,
                userPreference.contentId,
                userPreference.contentType.name,
                userPreference.preferenceType.name
        )

    }

    fun deleteUserContentPreference(userId: Long, contentId: String, preferenceType: ArticleConstants.PreferenceType) {

        val sql = "DELETE " +
                "FROM " +
                "user_content_preferences " +
                "WHERE user_id = ? " +
                "AND content_id = ? " +
                "AND preference_type = ? "

        jdbcTemplateForUserDb.update(sql, userId, contentId, preferenceType.name)
    }

    fun getContentReportReasons(): List<ReportReason> {

        val query = "SELECT * " +
                    "FROM " +
                    "report_reasons"

        val reasonMapper: RowMapper<ReportReason> = RowMapper { rs, _ ->
            ReportReason(
                    rs.getInt("id"),
                    rs.getString("reason")
            )
        }
        return jdbcTemplateForUserDb.query(query, reasonMapper)
    }

    fun insertReportedContent(report: UserReportedContent) {

        val query = "INSERT " +
                    "INTO " +
                    "user_reported_content " +
                    "(" +
                        "user_id, content_id, content_type, reason_id, details" +
                    ")" +
                    "VALUES (?, ?, ?, ?, ?)"

        jdbcTemplateForUserDb.update(query, report.userId, report.contentId, report.contentType.name, report.reasonId, report.details)
    }

    fun countReportsInLastHour(userId: Long, intervalInSeconds: Int): Int {

        val query = "SELECT " +
                    "COUNT(*) " +
                    "FROM " +
                    "user_reported_content " +
                    "WHERE user_id = ? " +
                    "AND created_at >= NOW() - INTERVAL '$intervalInSeconds SECOND' "

        return jdbcTemplateForUserDb.queryForObject(query, Int::class.java, userId)
    }

    fun insertArticleSource(articleSource: InsertArticleWithSourceRequest,sourceLogoURL : String) : ObjectId {

        val newSourceIdObj = ObjectId()
        val source = ArticleSource(newSourceIdObj, articleSource.source,sourceLogoURL,ArticleConstants.SourceType.ARTICLE,ArticleConstants.SourceMedium.WEB_SEARCH)
        mongoTemplate.insert(source,"article_sources")
        return newSourceIdObj
    }

    fun insertArticleFromLiveSearch(
            request: InsertArticleWithSourceRequest
    ): ObjectId? {

        val newArticleIdObj = ObjectId()

        val article = Article(
                articleId =  newArticleIdObj,
                url = request.url,
                title = request.title,
                shortDescription =  request.shortDescription,
                publishedTime = request.publishedTime,
                lastUpdatedTime = request.lastUpdatedTime,
                sourceId = request.sourceId,
                tags =  request.tags,
                articleImageUrl = request.articleImage,
                category = request.categoryName,
                authors =  request.authors,
                isPremiumArticle = false,
                contentType = ArticleConstants.ContentType.ARTICLE,
                sourceMedium = ArticleConstants.SourceMedium.WEB_SEARCH,
                cleanedText = request.cleanedText,
                reactions = HashMap()
        )

        mongoTemplate.insert(article, "articles")
        return newArticleIdObj
    }

    fun getArticleIdByUrl(url: String): ObjectId? {

        val getArticleByURLQuery = Query().addCriteria(Criteria.where("url").`is`(url))
        return mongoTemplate.findOne(getArticleByURLQuery, Article::class.java)?.articleId
    }
}