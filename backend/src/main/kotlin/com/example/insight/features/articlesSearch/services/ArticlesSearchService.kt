package com.example.insight.features.articlesSearch.services

import com.fasterxml.jackson.databind.ObjectMapper
import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.errorHandler.ErrorTypes
import com.example.insight.common.errorHandler.exceptions.BadRequestException
import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.models.entities.User
import com.example.insight.common.models.entities.UserArticlesSearch
import com.example.insight.common.utils.mlServer.models.requests.SearchArticlesMLServerRequest
import com.example.insight.common.utils.mlServer.services.MLServerService
import com.example.insight.features.article.services.ArticleService
import com.example.insight.features.articlesSearch.models.requests.ArticlesSearchRequest
import com.example.insight.features.articlesSearch.models.requests.ArticlesSearchSummarySaveRequest
import com.example.insight.features.articlesSearch.models.responses.ArticlesSearchResponse
import com.example.insight.features.articlesSearch.repositories.ArticlesSearchRepository
import com.example.insight.features.articlesSearch.utils.ArticlesSearchConstants
import com.example.insight.features.articlesSearch.utils.ArticlesSearchConstants.ARTICLES_PER_PAGE
import com.example.insight.features.articlesSearch.utils.ArticlesSearchConstants.INVALID_CHARS_FOR_SEARCH_QUERY
import com.example.insight.features.articlesSearch.utils.ArticlesSearchConstants.MAX_ARTICLES_PER_QUERY
import com.example.insight.features.articlesSearch.utils.ArticlesSearchConstants.MAX_SEARCH_QUERY_LENGTH
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.util.*

@Service
class ArticlesSearchService {

    @Autowired
    lateinit var articlesSearchRepository: ArticlesSearchRepository

    @Autowired
    lateinit var mlServerService: MLServerService

    @Autowired
    lateinit var articleService: ArticleService

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    private val objectMapper = ObjectMapper()

    @Transactional("userDatabaseTransactionManager")
    fun getArticlesSearchResults(
        user: User,
        request: ArticlesSearchRequest
    ): ArticlesSearchResponse {

        val searchRequestUUID = UUID.randomUUID()

        //Time logger
        var startTime = System.currentTimeMillis()
        logger.info("Search request execution started --- userId: ${user.userId} | request: $request | searchRequestUUID: $searchRequestUUID")
        val existingSearchResults = validateArticlesSearchApiInput(user.userId, request)

        if (existingSearchResults != null) {
            return fetchResultsFromExistingResults(existingSearchResults, request, user, searchRequestUUID)
        }

        val cleanedSearchQuery = validateAndCleanSearchQuery(user.userId, request.searchQuery)

        val (mlServerResponse, mlServerResponseString) = mlServerService.getArticlesSearchResults(
            SearchArticlesMLServerRequest(
                cleanedSearchQuery,
                user.userId
            )
        )

        //Time logger
        var endTime = System.currentTimeMillis()
        logger.info("Search request results received from ML --- userId: ${user.userId} in ${endTime - startTime} milli seconds | request: $request | searchRequestUUID: $searchRequestUUID")
        startTime = System.currentTimeMillis()

        val articleIds = mlServerResponse.searchArticleIds.map { it.articleId }

        val searchId = articlesSearchRepository.storeSearchQueryResults(
            user.userId,
            request.searchQuery,
            cleanedSearchQuery,
            articleIds,
            mlServerResponseString
        ) ?: run {
            logger.error("Unable to create search Id --- userId: ${user.userId} | request: $request | searchRequestUUID: $searchRequestUUID")
            throw InternalServerErrorException()
        }

        val articles = if(articleIds.isNotEmpty()) {
            articleService.getArticlesForUser(user.userId, articleIds)
        } else {
            arrayListOf()
        }

        //Time logger
        endTime = System.currentTimeMillis()
        logger.info("Search request results meta data received from mongoDB --- userId: ${user.userId} in ${endTime - startTime} milli seconds | request: $request | searchRequestUUID: $searchRequestUUID")
        startTime = System.currentTimeMillis()

        val startIndex = ((request.page - 1) * ARTICLES_PER_PAGE).coerceAtLeast(0)
        val endIndex = (startIndex + ARTICLES_PER_PAGE).coerceAtMost(articleIds.size)
        val totalNumberOfPages = when {
            articleIds.isEmpty() -> 0
            articleIds.size <= ARTICLES_PER_PAGE -> 1
            else -> ((articleIds.size - 1) / ARTICLES_PER_PAGE) + 1
        }

        //Time logger
        endTime = System.currentTimeMillis()
        logger.info("Search request execution ended --- userId: ${user.userId} in ${endTime - startTime} milli seconds | request: $request | searchRequestUUID: $searchRequestUUID")

        val croppedArticles = articles.subList(startIndex, endIndex)

        return ArticlesSearchResponse(
            searchId,
            1,
            croppedArticles,
            mlServerResponse.additionalInfo,
            totalNumberOfPages,
            articles.size,
            croppedArticles.map{ it.articleId },
            mlServerResponse.userPortfolioData,
            mlServerResponse.portfolioData
        )
    }

    fun saveAiGeneratedSearchSummary(searchId: Long, requestBody: ArticlesSearchSummarySaveRequest) {

        val summaryInfoString = objectMapper.writeValueAsString(
            requestBody.summaryInfo
        )
        articlesSearchRepository.saveAiGeneratedSearchSummary(searchId, summaryInfoString)
    }

    private fun fetchResultsFromExistingResults(
        existingDetails: UserArticlesSearch,
        request: ArticlesSearchRequest,
        user: User,
        searchRequestUUID: UUID
    ): ArticlesSearchResponse {

        val articleIds = existingDetails.searchResults
        val articles = articleService.getArticlesForUser(user.userId, articleIds)
        val sortedArticlesByPublishedTime = articles.sortedByDescending { it.publishedTime }

        var sortedArticles = when (request.sortBy) {
            ArticlesSearchConstants.ArticlesSearchSortBy.RELEVANCE -> articles
            ArticlesSearchConstants.ArticlesSearchSortBy.PUBLISHED_TIME -> sortedArticlesByPublishedTime
        }

        val startIndex = ((request.page - 1) * ARTICLES_PER_PAGE).coerceAtLeast(0)
        val endIndex = (startIndex + ARTICLES_PER_PAGE).coerceAtMost(articleIds.size)

        sortedArticles = sortedArticles.subList(startIndex, endIndex)
        val additionalInfo =
            mlServerService.getAdditionalInfoFromSearchArticlesMLServerResponse(existingDetails.mlServerResponse)

        val totalNumberOfPages = when {
            articleIds.isEmpty() -> 0
            articleIds.size <= ARTICLES_PER_PAGE -> 1
            else -> ((articleIds.size - 1) / ARTICLES_PER_PAGE) + 1
        }

        //Time logger
        logger.info("Search request execution ended for userId: ${user.userId} | searchRequestUUID: $searchRequestUUID")

        return ArticlesSearchResponse(
            existingDetails.searchId,
            request.page,
            sortedArticles,
            additionalInfo,
            totalNumberOfPages,
            articleIds.size,
            sortedArticles.map { it.articleId },
        )
    }

    private fun validateArticlesSearchApiInput(
        userId: Long,
        request: ArticlesSearchRequest
    ): UserArticlesSearch? {

        if (
            request.page != 1 && request.searchId == null ||
            (request.page * ARTICLES_PER_PAGE) > MAX_ARTICLES_PER_QUERY ||
            request.page == 0 ||
            (request.searchId == null && request.sortBy == ArticlesSearchConstants.ArticlesSearchSortBy.PUBLISHED_TIME) ||
            request.searchQuery.length > MAX_SEARCH_QUERY_LENGTH
            ) {
            logger.error("Invalid request payload! --- userId: $userId | request: $request")
            throw BadRequestException()
        } else if (request.searchId != null) {

            val existingSearchResults =
                articlesSearchRepository.getExistingArticlesSearchDetails(userId, request.searchId)
            return existingSearchResults ?: run {
                logger.error("Invalid search request. search session doesn't exist! --- userId: $userId | request: $request")
                throw BadRequestException()
            }
        }

        return null
    }

    private fun validateAndCleanSearchQuery(userId: Long, searchQuery: String): String {

        var cleanedSearchQuery = searchQuery

        if (searchQuery.length > 140) {

            logger.error("Invalid search query! Found more than 140 chars --- userId: $userId | searchQuery: $searchQuery")
            throw BadRequestException(
                ErrorTypes.Http4xxErrors.ArticleSearch.INVALID_SEARCH_QUERY,
                ApiMessages.ArticleSearch.INVALID_SEARCH_QUERY,
            )
        }

        if (detectScripts(cleanedSearchQuery)) {

            logger.error("Invalid search query! Found a script in the query --- userId: $userId | searchQuery: $searchQuery")
            throw BadRequestException(
                ErrorTypes.Http4xxErrors.ArticleSearch.INVALID_SEARCH_QUERY,
                ApiMessages.ArticleSearch.INVALID_SEARCH_QUERY,
            )
        }

        // Remove characters which are not part of alphabets, numbers, or space
        cleanedSearchQuery = cleanedSearchQuery.replace(INVALID_CHARS_FOR_SEARCH_QUERY, " ")

        /**
         * To remove extra continuous white spaces in the query string.
         * For example: "Hello      World" to "Hello World"
         */
        cleanedSearchQuery = cleanedSearchQuery.replace(Regex("\\s+"), " ")

        // Remove newline and tab characters
        cleanedSearchQuery = cleanedSearchQuery.replace("\n", "").replace("\t", "")

        if (cleanedSearchQuery.isBlank()) {
            logger.error("Invalid search query! Found search query to be empty post cleaning --- userId: $userId | searchQuery: $searchQuery")
            throw BadRequestException(
                ErrorTypes.Http4xxErrors.ArticleSearch.INVALID_SEARCH_QUERY,
                ApiMessages.ArticleSearch.INVALID_SEARCH_QUERY,
            )
        }

        return cleanedSearchQuery.trim().lowercase()
    }

    private fun detectScripts(query: String): Boolean {

        //TODO: check if any library can take this up
        // Define a pattern to detect common script-like sequences
        val scriptPattern = Regex("""<script>|javascript:|sql:|eval\(|alert\(""", RegexOption.IGNORE_CASE)
        return scriptPattern.containsMatchIn(query)
    }
}