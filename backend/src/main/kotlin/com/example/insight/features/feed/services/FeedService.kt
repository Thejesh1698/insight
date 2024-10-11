package com.example.insight.features.feed.services

import com.example.insight.common.errorHandler.exceptions.BadRequestException
import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.models.entities.User
import com.example.insight.common.models.entities.UserFeedDetails
import com.example.insight.common.utils.mlServer.models.requests.GetUserFeedMLServerRequest
import com.example.insight.common.utils.mlServer.services.MLServerService
import com.example.insight.common.utils.secondsSinceGivenTimestamp
import com.example.insight.features.article.services.ArticleService
import com.example.insight.features.article.utils.ArticleConstants
import com.example.insight.features.feed.models.responses.UserEpisodeFeedResponse
import com.example.insight.features.feed.models.responses.UserFeedResponse
import com.example.insight.features.feed.models.responses.UserPodcastFeedResponse
import com.example.insight.features.feed.repositories.FeedRepository
import com.example.insight.features.feed.utils.FeedConstants
import com.example.insight.features.user.services.UserService
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional

@Service
class FeedService {

    @Autowired
    lateinit var feedRepository: FeedRepository

    @Autowired
    lateinit var articleService: ArticleService

    @Autowired
    lateinit var userService: UserService

    @Autowired
    lateinit var mlServerService: MLServerService

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    @Transactional("userDatabaseTransactionManager")
    fun getUserFeed(user: User, page: Int, sessionIdParam: Long?): UserFeedResponse {

        val existingFeedDetails = validateFeedRequest(user, page, sessionIdParam, FeedConstants.FeedType.ARTICLE)
        val sessionId = sessionIdParam ?: feedRepository.insertFeedSession(user.userId, FeedConstants.FeedType.ARTICLE) ?: run {
            logger.error("Failed to insert feed session --- user: $user | page: $page | feedType: ${FeedConstants.FeedType.ARTICLE}")
            throw InternalServerErrorException()
        }
        val userInterestedTopics = userService.getUserInterestedTopics(user)

        if (userInterestedTopics.isEmpty()) {
            logger.error("Invalid api request. user didn't submit the preferences yet! --- user: $user")
            throw BadRequestException()
        }

        val userInterestedTopicIds: List<Long> = userInterestedTopics.map { it.topicId }
        val (secondsSinceLastApiCall, currentFeedSessionArticleIds) = if (existingFeedDetails.isEmpty()) {
            val seconds = getSecondsSinceLastSession(user, FeedConstants.FeedType.ARTICLE)
            Pair(seconds, listOf())
        } else {
            computeFeedSessionDetails(existingFeedDetails)
        }

        val (mlServerResponse, mlServerResponseString) = mlServerService.getUserFeed(
            GetUserFeedMLServerRequest(
                user.userId,
                userInterestedTopicIds,
                FeedConstants.NUMBER_OF_ARTICLES_IN_FEED,
                secondsSinceLastApiCall,
                currentFeedSessionArticleIds,
                page,
                FeedConstants.FeedType.ARTICLE
            )
        )
        logger.info("ML response for user article feed api --- user: $user | page: $page | sessionId: $sessionIdParam " +
                "| mlServerResponseString: $mlServerResponseString")

        val articleIds = mlServerResponse.feedContents.map { it.contentId }

        val feedId = feedRepository.insertFeedDetails(sessionId, articleIds, mlServerResponseString) ?: run {
            logger.error("Failed to insert feed details --- user: $user | page: $page | sessionId: $sessionIdParam")
            throw InternalServerErrorException()
        }

        val articles = if(articleIds.isNotEmpty()) {
            articleService.getArticlesForUser(user.userId, articleIds)
        } else {
            arrayListOf()
        }

        return UserFeedResponse(
            sessionId = sessionId,
            feedId = feedId,
            articles = articles,
            additionalInfo = mlServerResponse.additionalInfo,
            articleIds = articleIds
        )
    }

    @Transactional("userDatabaseTransactionManager")
    fun getUserPodcastFeed(user: User, sessionIdParam: Long?, page: Int): UserPodcastFeedResponse {

        val existingFeedDetails = validateFeedRequest(user, page, sessionIdParam, FeedConstants.FeedType.PODCAST)
        val sessionId = sessionIdParam ?: feedRepository.insertFeedSession(user.userId, FeedConstants.FeedType.PODCAST) ?: run {
            logger.error("Failed to insert feed session --- user: $user | page: $page | feedType: ${FeedConstants.FeedType.PODCAST}")
            throw InternalServerErrorException()
        }
        val userInterestedTopics = userService.getUserInterestedTopics(user)

        if (userInterestedTopics.isEmpty()) {
            logger.error("Invalid api request. user didn't submit the preferences yet! --- user: $user")
            throw BadRequestException()
        }

        val userInterestedTopicIds: List<Long> = userInterestedTopics.map { it.topicId }
        val (secondsSinceLastApiCall, currentFeedSessionArticleIds) = if (existingFeedDetails.isEmpty()) {
            val seconds = getSecondsSinceLastSession(user, FeedConstants.FeedType.PODCAST)
            Pair(seconds, listOf())
        } else {
            computeFeedSessionDetails(existingFeedDetails)
        }

        val (mlServerResponse, mlServerResponseString) = mlServerService.getUserFeed(
            GetUserFeedMLServerRequest(
                user.userId,
                userInterestedTopicIds,
                FeedConstants.NUMBER_OF_ARTICLES_IN_FEED,
                secondsSinceLastApiCall,
                currentFeedSessionArticleIds,
                page,
                FeedConstants.FeedType.PODCAST
            )
        )
        logger.info("ML response for user article feed api --- user: $user | page: $page | sessionId: $sessionIdParam " +
                "| mlServerResponseString: $mlServerResponseString")


        val podcastIds = mlServerResponse.feedContents.map { it.contentId }

        val feedId = feedRepository.insertFeedDetails(sessionId, podcastIds, mlServerResponseString) ?: run {
            logger.error("Failed to insert feed details --- user: $user | page: $page | sessionId: $sessionIdParam")
            throw InternalServerErrorException()
        }

        val podcasts = if(podcastIds.isNotEmpty()) {
            articleService.getArticleSourcesForUser(user.userId, podcastIds, ArticleConstants.SourceType.PODCAST)
        } else {
            arrayListOf()
        }

        return UserPodcastFeedResponse(
            sessionId = sessionId,
            feedId = feedId,
            podcasts = podcasts,
            additionalInfo = mlServerResponse.additionalInfo,
            podcastIds = podcastIds
        )
    }

    @Transactional("userDatabaseTransactionManager")
    fun getUserPodcastEpisodeFeed(user: User, sessionIdParam: Long?, page: Int): UserEpisodeFeedResponse {

        val existingFeedDetails = validateFeedRequest(user, page, sessionIdParam, FeedConstants.FeedType.PODCAST_EPISODE)
        val sessionId = sessionIdParam ?: feedRepository.insertFeedSession(user.userId, FeedConstants.FeedType.PODCAST_EPISODE) ?: run {
            logger.error("Failed to insert feed session --- user: $user | page: $page | feedType: ${FeedConstants.FeedType.PODCAST_EPISODE}")
            throw InternalServerErrorException()
        }
        val userInterestedTopics = userService.getUserInterestedTopics(user)

        if (userInterestedTopics.isEmpty()) {
            logger.error("Invalid api request. user didn't submit the preferences yet! --- user: $user")
            throw BadRequestException()
        }

        val userInterestedTopicIds: List<Long> = userInterestedTopics.map { it.topicId }
        val (secondsSinceLastApiCall, currentFeedSessionArticleIds) = if (existingFeedDetails.isEmpty()) {
            val seconds = getSecondsSinceLastSession(user, FeedConstants.FeedType.PODCAST_EPISODE)
            Pair(seconds, listOf())
        } else {
            computeFeedSessionDetails(existingFeedDetails)
        }

        val (mlServerResponse, mlServerResponseString) = mlServerService.getUserFeed(
            GetUserFeedMLServerRequest(
                user.userId,
                userInterestedTopicIds,
                FeedConstants.NUMBER_OF_ARTICLES_IN_FEED,
                secondsSinceLastApiCall,
                currentFeedSessionArticleIds,
                page,
                FeedConstants.FeedType.PODCAST_EPISODE
            )
        )
        logger.info("ML response for user article feed api --- user: $user | page: $page | sessionId: $sessionIdParam " +
                "| mlServerResponseString: $mlServerResponseString")

        val episodeIds = mlServerResponse.feedContents.map { it.contentId }

        val feedId = feedRepository.insertFeedDetails(sessionId, episodeIds, mlServerResponseString) ?: run {
            logger.error("Failed to insert feed details --- user: $user | page: $page | sessionId: $sessionIdParam")
            throw InternalServerErrorException()
        }

        val episodes = if(episodeIds.isNotEmpty()) {
            articleService.getArticlesForUser(user.userId, episodeIds)
        } else {
            arrayListOf()
        }

        return UserEpisodeFeedResponse(
            sessionId = sessionId,
            feedId = feedId,
            episodes = episodes,
            additionalInfo = mlServerResponse.additionalInfo,
            episodeIds =  episodeIds
        )
    }

    private fun validateFeedRequest(user: User, page: Int, sessionId: Long?, feedType: FeedConstants.FeedType): List<UserFeedDetails> {

        if (page != 0 && sessionId == null || page == 0 && sessionId != null) {
            logger.error("Invalid request payload! --- user: $user | page: $page | sessionId: $sessionId | feedType: $feedType")
            throw BadRequestException()
        } else if (sessionId != null) {
            val feeds = feedRepository.getExistingFeedSessionDetails(user.userId, sessionId)
            if (feeds.isEmpty() || page != feeds.size) {
                logger.error("Invalid feed request. page number doesn't sync with db values! --- user: $user | page: $page | sessionId: $sessionId")
                throw BadRequestException()
            }
            return feeds
        }
        return listOf()
    }

    private fun computeFeedSessionDetails(existingFeedDetails: List<UserFeedDetails>): Pair<Long, List<String>> {

        val secondsSinceLastFeedCall = secondsSinceGivenTimestamp(existingFeedDetails.first().createdAt)
        val articleIds: List<String> = existingFeedDetails.flatMap { it.articles }
        return Pair(secondsSinceLastFeedCall, articleIds)
    }

    private fun getSecondsSinceLastSession(user: User, feedType: FeedConstants.FeedType): Long? {

        val lastFeedSessionDetails = feedRepository.getLastFeedSessionDetails(user.userId, feedType)
        return lastFeedSessionDetails?.let {
            secondsSinceGivenTimestamp(lastFeedSessionDetails.createdAt)
        }
    }
}