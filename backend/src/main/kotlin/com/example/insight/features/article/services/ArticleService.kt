package com.example.insight.features.article.services

import com.fasterxml.jackson.databind.ObjectMapper
import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.errorHandler.exceptions.NoRecordFoundException
import com.example.insight.common.errorHandler.exceptions.BadRequestException
import com.example.insight.common.models.entities.*
import com.example.insight.common.models.responses.SuccessResponse
import com.example.insight.common.utils.aws.AwsConstants
import com.example.insight.common.utils.aws.queues.AmazonSqsManager
import com.example.insight.common.utils.aws.queues.models.SQSSendSingleMessageTemplate
import com.example.insight.common.utils.getArticlePublishedTimeInEpoch
import com.example.insight.features.article.models.requests.*
import com.example.insight.features.article.models.responses.*
import com.example.insight.features.article.repositories.ArticleRepository
import com.example.insight.features.article.utils.ArticleConstants
import com.example.insight.features.article.utils.ArticleConstants.AI_GENERATED_INFO_MODEL
import com.example.insight.features.article.utils.ArticleConstants.REPORT_REASON_MAX_CHARACTER_LIMIT
import com.example.insight.features.article.utils.ArticleConstants.MAX_REPORTS_LIMIT
import com.example.insight.features.article.utils.ArticleConstants.MODELS_WITH_HTML_SUMMARY_FORMAT
import com.example.insight.features.article.utils.ArticleConstants.MODELS_WITH_STRING_SUMMARY_FORMAT
import com.example.insight.features.article.utils.ArticleConstants.REPORT_INTERVAL_IN_SECONDS
import org.bson.types.ObjectId
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.dao.DuplicateKeyException
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.*
import kotlin.collections.ArrayList
import kotlin.collections.HashMap
import com.example.insight.features.article.models.requests.ArticleAndSourceRegisterRequest as ArticleAndSourceRequest

@Service
class ArticleService {

    @Autowired
    lateinit var articleRepository: ArticleRepository

    @Autowired
    private lateinit var amazonSqsManager: AmazonSqsManager

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)
    private val objectMapper = ObjectMapper()

    fun getArticle(articleId: String, fetchSourceInfo: Boolean): ArticleInformationResponse {

        val article = articleRepository.getArticle(articleId) ?: run {
            logger.error("Article not found --- articleId: $articleId")
            throw NoRecordFoundException(message = ApiMessages.Article.notFound)
        }
        val articleSourceInfo = if (fetchSourceInfo) {
            articleRepository.getArticleSourceById(article.sourceId) ?: run {
                logger.error("Article source not found --- articleId: $articleId")
                throw NoRecordFoundException(message = ApiMessages.ArticleSource.notFound)
            }
        } else {
            null
        }

        return ArticleInformationResponse(
            articleId = article.articleId.toHexString(),
            url = article.url,
            title = article.title,
            shortDescription = article.shortDescription,
            publishedTime = article.publishedTime,
            lastUpdatedTime = article.lastUpdatedTime,
            tags = article.tags,
            articleImageUrl = article.articleImageUrl,
            category = article.category,
            authors = article.authors,
            isPremiumArticle = article.isPremiumArticle,
            source = articleSourceInfo?.let {
                ArticleInformationResponse.ArticleSourceInformation(
                    sourceId = it.sourceId.toHexString(),
                    sourceName = it.name,
                    sourceLogo = it.logoURL,
                )
            }
        )
    }

    fun insertArticle(
        request: InsertArticleRequest
    ): UpsertArticleResponse {

        val articleSource = articleRepository.getArticleSourceByName(request.source)
            ?: run {
                logger.error("Article source not found --- request: $request")
                throw InternalServerErrorException(message = ApiMessages.ArticleSource.notFound)
            }
        request.sourceId = articleSource.sourceId
        val articleId = articleRepository.insertArticle(request)
            ?: run {
                logger.error("Unable to insert article into DB --- request: $request")
                throw InternalServerErrorException(message = ApiMessages.Article.insertError)
            }

        return UpsertArticleResponse(
            articleId.toHexString()
        )
    }

    fun updateArticle(
        articleId: String,
        request: UpdateArticleRequest
    ): Pair<UpsertArticleResponse, Boolean> {

        val isArticleUpdated = articleRepository.updateArticle(articleId, request)
            ?: run {
                logger.error("Article not found --- articleId: $articleId | request: $request")
                throw NoRecordFoundException(message = ApiMessages.Article.notFound)
            }

        return Pair(
            UpsertArticleResponse(
                articleId
            ), isArticleUpdated
        )
    }

    fun filterUnScrapedArticles(urls: List<String>): List<String> {

        if (urls.isEmpty()) {
            return arrayListOf()
        }

        val scrapedArticles = articleRepository.fetchRegisteredArticles(urls)
        val scrapedArticleUrls = scrapedArticles.map { it.url }
        return urls.filterNot { scrapedArticleUrls.contains(it) }
    }

    fun getAllArticleTopics(): List<ArticleTopic> {

        return articleRepository.getAllArticleTopics()
    }

    fun getArticlesForUser(userId: Long, articleIds: List<String>): List<ArticleInfoForUserResponse> {

        val convertedArticleIds = articleIds.map { ObjectId(it) }
        val articles = articleRepository.getArticles(convertedArticleIds)
        val userArticleReactions = articleRepository.getUserArticleReactions(userId, articleIds)

        // Sort the articles based on the order of articleIds, set user reactions and Ai generated info
        val sortedArticles = articleIds.mapNotNull { articleId ->
            val article = articles.find { it.articleId == articleId }
            article?.apply {
                userReaction = userArticleReactions[articleId]

                extractAiGeneratedInfo(userId, this)
                articleDateInMilliEpoch = getArticlePublishedTimeInEpoch(articleId, publishedTime, logger)
            }
        }

        return sortedArticles
    }

    @Transactional("userDatabaseTransactionManager")
    fun saveUserArticleReaction(user: User, articleId: String, request: UserArticleReactionRequest) {

        articleRepository.upsertUserArticleReaction(user.userId, articleId, request.reactionId)

        val sqsMessage = objectMapper.writeValueAsString(
            ArticleReactionCountUpdateMessage(
                userId = user.userId,
                reactionId = request.reactionId,
                articleId = articleId,
                action = "INCREMENT"
            )
        )
        amazonSqsManager.sendMessage(
            SQSSendSingleMessageTemplate(
                message = sqsMessage,
                queueName = AwsConstants.QueueUrls.ARTICLE_REACTIONS_COUNT_UPDATER.value
            )
        )
    }

    @Transactional("userDatabaseTransactionManager")
    fun deleteUserArticleReaction(user: User, articleId: String, request: UserArticleReactionRequest) {

        val isReactionDeleted = articleRepository.deleteUserArticleReaction(user.userId, articleId, request.reactionId)
        if (!isReactionDeleted) {
            logger.error("Invalid request, given reactionId can't be found for this userId --- userId: ${user.userId} | articleId: $articleId | request: $request")
            throw BadRequestException()
        }

        val sqsMessage = objectMapper.writeValueAsString(
            ArticleReactionCountUpdateMessage(
                userId = user.userId,
                reactionId = request.reactionId,
                articleId = articleId,
                action = "DECREMENT"
            )
        )
        amazonSqsManager.sendMessage(
            SQSSendSingleMessageTemplate(
                message = sqsMessage,
                queueName = AwsConstants.QueueUrls.ARTICLE_REACTIONS_COUNT_UPDATER.value
            )
        )
    }

    fun updateArticleReactionCount(articleId: String, request: UpdateArticleReactionCount) {

        val isCountUpdated = when (request.action) {
            "INCREMENT" -> {
                articleRepository.incrementArticleReactionCount(
                    articleId,
                    request.reactionId
                )
            }

            "DECREMENT" -> {
                articleRepository.decrementArticleReactionCount(
                    articleId,
                    request.reactionId
                )
            }

            else -> {
                logger.error("Invalid request action in updateArticleReactionCount api --- article: $articleId | request: $request")
                throw BadRequestException()
            }
        }

        if (!isCountUpdated) {
            logger.error("Invalid request, possibly articleId doesn't exist --- article: $articleId | request: $request")
            throw BadRequestException()
        }

        logger.info("article reaction count updated --- articleId: $articleId | request: $request")
    }

    fun updateAiGeneratedInfoForArticle(articleId: String, request: AiGeneratedInfoForArticleRequest): Boolean {

        return articleRepository.updateAiGeneratedInfoForArticle(
            articleId, request
        )
    }

    fun getArticleSourcesForUser(
        userId: Long,
        sourceIds: List<String>,
        sourceType: ArticleConstants.SourceType
    ): List<ArticleSourceInfoForUserResponse> {

        val convertedSourceIds = sourceIds.map { ObjectId(it) }
        val sources = articleRepository.getArticleSources(convertedSourceIds)

        // Sort the article sources based on the order of sourceIds, set published time in milli epoch seconds
        val sortedSources = sourceIds.mapNotNull { sourceId ->
            sources.find { it.sourceId == sourceId }
        }

        return sortedSources
    }

    private fun extractAiGeneratedInfo(userId: Long, article: ArticleInfoForUserResponse) {

        article.apply {
            aiGeneratedSummary = aiGeneratedInfo?.summary?.let { summary ->

                findDesiredOrLatestAiGeneratedInfo(userId, article, summary)?.let {
                    val (modelName, summaryInfo) = it
                    var summaryValue = summaryInfo["value"] as String
                    val valueType = when (modelName) {
                        in MODELS_WITH_HTML_SUMMARY_FORMAT -> {
                            ArticleConstants.ContentSummaryValueTypes.HTML
                        }

                        in MODELS_WITH_STRING_SUMMARY_FORMAT -> {
                            summaryValue = objectMapper.writeValueAsString(
                                arrayListOf(
                                    hashMapOf(
                                        "emoji" to null,
                                        "label" to null,
                                        "point" to summaryValue
                                    )
                                )
                            )
                            ArticleConstants.ContentSummaryValueTypes.JSON
                        }

                        else -> {
                            ArticleConstants.ContentSummaryValueTypes.JSON
                        }
                    }

                    ArticleInfoForUserResponse.AiGeneratedInfo(
                        summaryValue,
                        modelName,
                        valueType
                    )
                }
            } ?: shortDescription?.let {
                val formattedValue = objectMapper.writeValueAsString(
                    arrayListOf(
                        hashMapOf(
                            "emoji" to null,
                            "label" to null,
                            "point" to it
                        )
                    )
                )
                ArticleInfoForUserResponse.AiGeneratedInfo(
                    formattedValue,
                    "shortDescription",
                    ArticleConstants.ContentSummaryValueTypes.JSON
                )
            }

            aiGeneratedTitle = aiGeneratedInfo?.title?.let {

                findDesiredOrLatestAiGeneratedInfo(userId, article, it)?.let {
                    val (modelName, titleInfo) = it
                    ArticleInfoForUserResponse.AiGeneratedInfo(
                        titleInfo["value"] as String,
                        modelName
                    )
                }
            }
        }
    }

    private fun findDesiredOrLatestAiGeneratedInfo(
        userId: Long,
        article: ArticleInfoForUserResponse,
        data: Map<String, Any?>
    ): Pair<String, Map<*, *>>? {

        val generatedInfoBySpecificModel = data[AI_GENERATED_INFO_MODEL]

        return if (generatedInfoBySpecificModel != null) {
            Pair(AI_GENERATED_INFO_MODEL, generatedInfoBySpecificModel as Map<*, *>)
        } else {
            var latestNode: Map<*, *>? = null
            lateinit var latestNodeModelName: String
            var latestTimestamp = Date(0)

            for ((modelName, currentNode) in data) {
                if (currentNode is Map<*, *> && currentNode["generated_at"] != null) {
                    val timestamp = currentNode["generated_at"] as Date

                    if (timestamp.after(latestTimestamp)) {
                        latestTimestamp = timestamp
                        latestNode = currentNode
                        latestNodeModelName = modelName
                    }
                }
            }

            latestNode?.let {
                Pair(latestNodeModelName, latestNode)
            } ?: let {
                logger.warn("Unable to find AiGeneratedInfo for an article --- userId: $userId | article: $article")
                null
            }
        }
    }

    @Transactional("userDatabaseTransactionManager")
    fun saveArticleComment(user: User, articleId: String, request: ArticleCommentRequest): SaveArticleCommentResponse {

        if (request.comment.length > 140 || request.comment.isBlank()) {
            logger.error(
                "Invalid request, given comment is either blank or exceeds character limit --- " +
                        "userId: ${user.userId} | articleId: $articleId | request: $request"
            )
            throw BadRequestException()
        }

        val (commentId, commentPostedAt) = articleRepository.upsertArticleComment(
            user.userId,
            articleId,
            request.comment
        )

        val sqsMessage = objectMapper.writeValueAsString(
            ArticleCommentsCountUpdateMessage(
                userId = user.userId,
                articleId = articleId,
                action = "INCREMENT",
                commentPostedAt = commentPostedAt,
                commentId = commentId
            )
        )
        amazonSqsManager.sendMessage(
            SQSSendSingleMessageTemplate(
                message = sqsMessage,
                queueName = AwsConstants.QueueUrls.ARTICLE_COMMENTS_COUNT_UPDATER.value
            )
        )

        return SaveArticleCommentResponse(
            commentDetails = ArticleCommentResponse(
                commentId = commentId,
                commentText = request.comment,
                articleId = articleId,
                postedAt = commentPostedAt,
                authorInfo = ArticleCommentResponse.ArticleCommentUserInfo(
                    userId = user.userId,
                    userName = user.userName ?: run {
                        logger.error("Internal server exception. user name can't be empty --- user: $user | articleId: $articleId | request: $request")
                        throw InternalServerErrorException()
                    }
                )
            ),
        )
    }

    @Transactional("userDatabaseTransactionManager")
    fun deleteArticleComment(user: User, articleId: String, commentId: Long) {

        val isCommentDeleted = articleRepository.deleteArticleComment(user.userId, articleId, commentId)
        if (!isCommentDeleted) {
            logger.error("Invalid request, given commentId can't be found for this userId --- userId: ${user.userId} | articleId: $articleId | commentId: $commentId")
            throw BadRequestException()
        }

        val sqsMessage = objectMapper.writeValueAsString(
            ArticleCommentsCountUpdateMessage(
                userId = user.userId,
                articleId = articleId,
                action = "DECREMENT",
                commentPostedAt = null,
                commentId = commentId
            )
        )
        amazonSqsManager.sendMessage(
            SQSSendSingleMessageTemplate(
                message = sqsMessage,
                queueName = AwsConstants.QueueUrls.ARTICLE_COMMENTS_COUNT_UPDATER.value
            )
        )
    }

    fun updateArticleCommentsCount(articleId: String, request: UpdateArticleCommentsCount) {

        val isCountUpdated = when (request.action) {
            "INCREMENT" -> {
                articleRepository.incrementArticleCommentsCount(
                    articleId
                )
            }

            "DECREMENT" -> {
                articleRepository.decrementArticleCommentsCount(
                    articleId
                )
            }

            else -> {
                logger.error("Invalid request action in updateArticleCommentsCount api --- article: $articleId | request: $request")
                throw BadRequestException()
            }
        }

        if (!isCountUpdated) {
            logger.error("Invalid request, possibly articleId doesn't exist --- article: $articleId | request: $request")
            throw BadRequestException()
        }

        logger.info("article comments count updated --- articleId: $articleId | request: $request")
    }

    fun getArticleComments(articleId: String): List<ArticleCommentResponse> {

        return articleRepository.getArticleComments(articleId)
    }

    fun getCategorizedArticleTopics(): CategorizedArticleTopicsResponse {

        val allTopics = articleRepository.getAllArticleTopics()
        val categorizedTopics = HashMap<String, ArrayList<ArticleTopic>>()
        val categoriesList = sortedSetOf<String>()

        for (topic in allTopics) {
            val category = topic.category
            categoriesList.add(category)

            if (categorizedTopics.containsKey(category)) {
                categorizedTopics[category]?.add(topic)
            } else {
                val newTopicList = ArrayList<ArticleTopic>()
                newTopicList.add(topic)
                categorizedTopics[category] = newTopicList
            }
        }

        return CategorizedArticleTopicsResponse(
            categorizedTopics,
            categoriesList.toList()
        )
    }

    @Transactional("userDatabaseTransactionManager")
    fun saveOrDeleteUserContentPreference(user: User, contentId: String, request: UserContentPreferenceRequest) {

        val userPreference = UserContentPreference(
            userId = user.userId,
            contentId = contentId,
            contentType = request.contentType,
            preferenceType = request.preferenceType
        )
        if (request.value) {
            articleRepository.saveUserContentPreference(userPreference)
        } else {
            articleRepository.deleteUserContentPreference(user.userId, contentId, request.preferenceType)
        }
    }

    fun getContentReportReasons(): List<ReportReason> {

        return articleRepository.getContentReportReasons()
    }

    @Transactional("userDatabaseTransactionManager")
    fun reportContent(user: User, contentId: String, request: ReportContentRequest): SuccessResponse {

//      Removes HTML tags from the 'details' string if present, ensuring null safety.
        val details = request.details?.replace(Regex("<[^>]*>"), "")
        if (details != null && details.length > REPORT_REASON_MAX_CHARACTER_LIMIT) {
            logger.error("Invalid request, Maximum Character limit for details reached. userId: ${user.userId} | contentId: $contentId | Request: $request")
            throw BadRequestException()
        }

        val reportCount = articleRepository.countReportsInLastHour(user.userId, REPORT_INTERVAL_IN_SECONDS)
        if (reportCount >= MAX_REPORTS_LIMIT) {
            logger.error("Invalid request, Maximum report limit reached. userId: ${user.userId} | contentId: $contentId | Request: $request")
            throw BadRequestException()
        }

        val report = UserReportedContent(
            userId = user.userId,
            contentId = contentId,
            contentType = request.contentType,
            reasonId = request.reasonId,
            details = details
        )
        articleRepository.insertReportedContent(report)
        return SuccessResponse()
    }

    fun registerSearchArticles(requests: ArticleAndSourceRequest) : InsertArticleWithSourceResponse {

        val articleIds = requests.articles.map { req ->

            if (req.title.isNullOrBlank()) {
                logger.error(" Title is Blank --- URL ${req.url}")
                throw BadRequestException()
            }

            if(req.cleanedText.isNullOrBlank() || req.cleanedText.length < ArticleConstants.ARTICLE_CLEAN_TEXT_LENGTH) {
                logger.error("Article Clean Text is Blank or Insufficient --- URL ${req.url}")
                throw BadRequestException()
            }

            val articleSourceId = articleRepository.getArticleSourceByName(req.source)?.sourceId

            req.sourceId = articleSourceId ?: articleRepository.insertArticleSource(req,req.sourceLogoURL ?: ArticleConstants.SOURCE_DEFAULT_LOGO_URL)
            try {
                articleRepository.insertArticleFromLiveSearch(req)
            } catch (e: DuplicateKeyException) {
                articleRepository.getArticleIdByUrl(req.url) ?: run {
                    logger.error("Failed to retrieve article ID --- URL: ${req.url}")
                    throw BadRequestException()
                }
            }.toString()
        }

        return InsertArticleWithSourceResponse(articleIds)
    }
}