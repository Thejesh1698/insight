package com.example.insight.features.user.services

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.errorHandler.ErrorTypes
import com.example.insight.common.errorHandler.exceptions.BadRequestException
import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.models.entities.User
import com.example.insight.common.models.entities.ArticleTopic
import com.example.insight.common.utils.isValidUserName
import com.example.insight.features.article.services.ArticleService
import com.example.insight.features.article.utils.ArticleConstants
import com.example.insight.features.eventsManager.services.EventsManagerService
import com.example.insight.features.eventsManager.utils.EventConstants
import com.example.insight.features.podcasts.utils.PodcastsConstants.PODCAST_FEED_OFFSET_MULTIPLE
import com.example.insight.features.podcasts.utils.PodcastsConstants.PODCAST_EPISODE_FEED_OFFSET_MULTIPLE
import com.example.insight.features.user.models.requests.UpdateUserDetailsRequest
import com.example.insight.features.user.models.requests.UserInterestedTopicsRequest
import com.example.insight.features.user.models.responses.*
import com.example.insight.features.user.repositories.UserRepository
import com.example.insight.features.user.utils.UserConstants
import com.example.insight.features.userAuthentication.models.responses.UserSignUpOrLoginResponse
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service

@Service
class UserService {

    @Autowired
    lateinit var userRepository: UserRepository

    @Autowired
    lateinit var articleService: ArticleService

    @Autowired
    lateinit var eventsManagerService: EventsManagerService

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    fun insertUser(mobileNumber: String): User {

        return userRepository.insertUser(mobileNumber)
    }

    fun insertUser(email:String, userName: String?): User {

        return userRepository.insertUser(email, userName)
    }

    fun getUserByMobileNumber(mobileNumber: String): User? {

        return userRepository.getUserByMobileNumber(mobileNumber)
    }

    fun getUserByEmail(email: String): User? {

        return userRepository.getUserByEmail(email)
    }

    fun getUserInterestedTopics(user: User): List<ArticleTopic> {

        return userRepository.getUserInterestedTopics(user.userId)
    }

    fun upsertUserInterestedTopics(user: User, request: UserInterestedTopicsRequest) {

        if (request.topics.size < 3) {
            logger.error("Bad Request. Interested topics length should be minimum 3! --- request: $request | user: $user")
            throw BadRequestException()
        }
        val topicsSet = request.topics.toSet()

        if (topicsSet.size < request.topics.size) {
            logger.error("Bad request. Got duplicate options in UserInterestedTopicsRequest! --- request: $request | user: $user")
            throw BadRequestException()
        }
        userRepository.upsertUserInterestedTopics(user.userId, request.topics)
    }

    fun getUserAppSummary(user: User): UserAppSummaryResponse {

        val articleReactions = userRepository.getArticleReactions()
        return UserAppSummaryResponse(
            reactions = UserAppSummaryResponse.AppSummaryReactionsResponse(
                articleReactions = articleReactions
            ),
            feedConfig = UserAppSummaryResponse.AppFeedConfig(
                podcastFeedOffset = PODCAST_FEED_OFFSET_MULTIPLE,
                podcastEpisodeFeedOffset = PODCAST_EPISODE_FEED_OFFSET_MULTIPLE
            )
        )
    }

    fun updateUserDetails(user: User, request: UpdateUserDetailsRequest): Boolean {

        if (!isValidUserName(request.userName)) {
            logger.error("Bad Request. Invalid user name! --- user: $user | request: $request")
            throw BadRequestException(
                ErrorTypes.Http4xxErrors.User.INVALID_USER_NAME,
                ApiMessages.User.INVALID_USER_NAME
            )
        }

        // Trim extra spaces between words and remove spaces at the ends
        var formattedUserName = request.userName.replace("\\s+".toRegex(), " ").trim()
        formattedUserName = formattedUserName.split(" ").joinToString(" ") { it.replaceFirstChar { it.titlecase()[0] } }

        val areDetailsUpdated = userRepository.updateUserDetails(user.userId, formattedUserName)

        if(areDetailsUpdated) {
            val userProperties = hashMapOf<EventConstants.UserPropertyKeys, Any?>(
                EventConstants.UserPropertyKeys.USER_ID to user.userId,
                EventConstants.UserPropertyKeys.USER_NAME to request.userName
            )
            eventsManagerService.setUserPropertiesInMixpanel(user.userId, userProperties)
        }
        return areDetailsUpdated
    }

    fun saveArticleBookmark(userId: Long, articleId: String): Long {

        val bookmarkId = userRepository.saveArticleBookmark(userId, articleId)

        if (bookmarkId == null) {
            logger.error("Internal server error. Duplicate article bookmark request! --- userId: $userId | articleId: $articleId")
            throw InternalServerErrorException()
        }
        return bookmarkId
    }

    fun deleteArticleBookmark(userId: Long, bookmarkId: Long) {

        val isArticleBookmarkDeleted = userRepository.deleteArticleBookmark(userId, bookmarkId)

        if (!isArticleBookmarkDeleted) {
            logger.error("Bad request. Bookmark Id doesn't exist for the user! --- userId: $userId | bookmarkId: $bookmarkId")
            throw BadRequestException()
        }
    }

    fun getUserArticleBookmarks(user: User, cursor: Long?): UserArticleBookmarksResponse {

        val pageSize = UserConstants.Bookmarks.ARTICLES_PER_PAGE
        val bookmarks = userRepository.getUserArticleBookmarks(user.userId, cursor, pageSize)
        val articleIdBookmarkIdMap = hashMapOf<String, Long>()
        val articleIds = bookmarks.map {
            articleIdBookmarkIdMap[it.articleId] = it.bookmarkId
            it.articleId
        }
        if (articleIds.isEmpty()) {
            return UserArticleBookmarksResponse(
                bookmarks = arrayListOf(),
                cursor
            )
        }

        val nextCursor = bookmarks.last().bookmarkId
        val articlesWithMetaInfo = articleService.getArticlesForUser(user.userId, articleIds)
        val bookmarkedArticles = articlesWithMetaInfo.map {
            UserArticleBookmarkInfo(
                bookmarkId = articleIdBookmarkIdMap[it.articleId] ?: run {
                    logger.error(
                        "Internal server error. bookmarkId not found in articleIdBookmarkIdMap --- " +
                                "user: $user | cursor: $cursor | articleIdBookmarkIdMap: $articleIdBookmarkIdMap | articlesWithMetaInfo: $articlesWithMetaInfo"
                    )
                    throw InternalServerErrorException()
                },
                articleInfo = it
            )
        }
        return UserArticleBookmarksResponse(
            bookmarkedArticles,
            nextCursor
        )
    }

    fun addArticleToReadingHistory(userId: Long, articleId: String): Long {

        val historyId = userRepository.addArticleToReadingHistory(userId, articleId)

        if (historyId == null) {
            logger.error(
                "Internal server error. Unable to save article reading history, historyId is null! --- " +
                        "userId: $userId | articleId: $articleId | historyId: null"
            )
            throw InternalServerErrorException()
        }
        return historyId
    }

    fun deleteArticleFromReadingHistory(userId: Long, historyId: Long) {

        val isArticleDeletedFromHistory = userRepository.deleteArticleFromReadingHistory(userId, historyId)

        if (!isArticleDeletedFromHistory) {
            logger.error("Bad request. HistoryId Id doesn't exist for the user! --- userId: $userId | historyId: $historyId")
            throw BadRequestException()
        }
    }

    fun getUserArticleReadingHistory(user: User, cursor: Long?): UserArticleReadingHistoryResponse {

        val pageSize = UserConstants.ReadingHistory.ARTICLES_PER_PAGE
        val history = userRepository.getUserArticleReadingHistory(user.userId, cursor, pageSize)
        val articleIdHistoryIdMap = hashMapOf<String, Long>()
        val articleIds = history.map {
            articleIdHistoryIdMap[it.articleId] = it.historyId
            it.articleId
        }
        if (articleIds.isEmpty()) {
            return UserArticleReadingHistoryResponse(
                readingHistory = arrayListOf(),
                cursor
            )
        }

        val nextCursor = history.last().historyId
        val articlesWithMetaInfo = articleService.getArticlesForUser(user.userId, articleIds)
        val articlesInHistory = articlesWithMetaInfo.map {
            UserArticleReadingHistoryInfo(
                historyId = articleIdHistoryIdMap[it.articleId] ?: run {
                    logger.error(
                        "Internal server error. historyId not found in articleIdHistoryIdMap --- " +
                                "user: $user | cursor: $cursor | articleIdHistoryIdMap: $articleIdHistoryIdMap | articlesWithMetaInfo: $articlesWithMetaInfo"
                    )
                    throw InternalServerErrorException()
                },
                articleInfo = it
            )
        }
        return UserArticleReadingHistoryResponse(
            articlesInHistory,
            nextCursor
        )
    }

    fun getUserArticleInteractionsState(userId: Long, articleIds: List<String>): HashMap<String, UserArticleInteractionsStateResponse.ArticleInteractionsState> {

        val interactionsState = hashMapOf<String, UserArticleInteractionsStateResponse.ArticleInteractionsState>()
        val bookmarkIds = userRepository.getBookmarkIdsForArticles(userId, articleIds)
        val contentPreferences= userRepository.getUserContentPreferences(userId, articleIds)

        val notInterestedMap = hashMapOf<String, Boolean>()
        val showMoreMap = hashMapOf<String, Boolean>()

        contentPreferences.forEach { (contentId, preferenceType) ->
            when (preferenceType) {
                ArticleConstants.PreferenceType.NOT_INTERESTED.name -> notInterestedMap[contentId] = true
                ArticleConstants.PreferenceType.SHOW_MORE_LIKE_THIS.name -> showMoreMap[contentId] = true
            }
        }

        articleIds.map {
            interactionsState[it] = UserArticleInteractionsStateResponse.ArticleInteractionsState(
                    bookmarkId = bookmarkIds[it],
                    isNotInterested = notInterestedMap[it],
                    showMoreLikeThis = showMoreMap[it]
            )
        }
        return interactionsState
    }

    fun getUserOnboardingStatus(user: User): UserSignUpOrLoginResponse.OnboardingStatus {

        val arePreferencesGiven = userRepository.getUserOnboardingStatus(user.userId) ?: run {
            logger.error("Internal server exception. getUserOnboardingStatus gave null --- userId: ${user.userId}")
            throw InternalServerErrorException()
        }
        val isUserNameGiven = user.userName != null

        return UserSignUpOrLoginResponse.OnboardingStatus(
            isUserNameGiven && arePreferencesGiven,
            stepsCompleted = UserSignUpOrLoginResponse.OnboardingStepsStatus(
                isUserNameGiven,
                arePreferencesGiven
            )
        )
    }
}