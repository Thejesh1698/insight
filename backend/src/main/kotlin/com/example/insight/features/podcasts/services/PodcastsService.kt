package com.example.insight.features.podcasts.services

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.errorHandler.exceptions.NoRecordFoundException
import com.example.insight.common.models.entities.User
import com.example.insight.common.utils.getArticlePublishedTimeInEpoch
import com.example.insight.features.article.models.responses.ArticleSourceInfoForUserResponse
import com.example.insight.features.article.services.ArticleService
import com.example.insight.features.article.utils.ArticleConstants
import com.example.insight.features.podcasts.models.requests.InsertPodcastEpisodeRequest
import com.example.insight.features.podcasts.models.requests.UpdatePodcastEpisodeRequest
import com.example.insight.features.podcasts.models.responses.PodcastsInfoWithEpisodesResponse
import com.example.insight.features.podcasts.models.responses.PodcastsLatestEpisodeInfoResponse
import com.example.insight.features.podcasts.repositories.PodcastsRepository
import com.example.insight.features.podcasts.utils.PodcastsConstants.PODCAST_EPISODES_PAGE_COUNT
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service

@Service
class PodcastsService {

    @Autowired
    lateinit var podcastsRepository: PodcastsRepository

    @Autowired
    lateinit var articleService: ArticleService

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    fun getPodcastsLatestEpisodeInfo(): PodcastsLatestEpisodeInfoResponse {

        val podcastsInfo = podcastsRepository.getPodcastsLatestEpisodeInfo()
        for (podcastInfo in podcastsInfo) {
            if(podcastInfo.latestEpisodeTime == null) {
                podcastInfo.totalNumberOfEpisodes = 0
            }
        }

        return PodcastsLatestEpisodeInfoResponse(
            podcastsInfo = podcastsInfo
        )
    }

    fun insertPodcastEpisode(podcastId: String, request: InsertPodcastEpisodeRequest): String {

        return podcastsRepository.insertPodcastEpisode(podcastId, request).toHexString()
    }

    fun updatePodcastEpisode(episodeId: String, request: UpdatePodcastEpisodeRequest): Boolean {

        val isEpisodeUpdated = podcastsRepository.updatePodcastEpisode(episodeId, request)
            ?: run {
                logger.error("Episode not found --- episodeId: $episodeId | request: $request")
                throw NoRecordFoundException(message = ApiMessages.Article.notFound)
            }

        return isEpisodeUpdated
    }

    fun getPodcastInfoWithEpisodes(user: User, podcastId: String, cursor: String?): PodcastsInfoWithEpisodesResponse {

        val podcastInfo: ArticleSourceInfoForUserResponse = articleService.getArticleSourcesForUser(user.userId, arrayListOf(podcastId), ArticleConstants.SourceType.PODCAST).firstOrNull() ?: run {
            logger.error("Podcast not found --- podcastId: $podcastId | user: $user | cursor: $cursor")
            throw NoRecordFoundException(message = ApiMessages.Podcast.notFound)
        }
        val episodes = podcastsRepository.getPaginatedEpisodesOfAPodcast(podcastId, cursor, PODCAST_EPISODES_PAGE_COUNT)

        episodes.map {
            it.articleDateInMilliEpoch = getArticlePublishedTimeInEpoch(it.articleId, it.publishedTime, logger)
        }

        val totalNumberOfPages = if(cursor == null || cursor == "") {
            val totalEpisodesCount = podcastsRepository.getTotalEpisodesCountOfAPodcast(podcastId, PODCAST_EPISODES_PAGE_COUNT)
            when {
                totalEpisodesCount == 0L -> 0
                totalEpisodesCount <= PODCAST_EPISODES_PAGE_COUNT -> 1
                else -> ((totalEpisodesCount - 1) / PODCAST_EPISODES_PAGE_COUNT) + 1
            }
        } else {
            null
        }
        return PodcastsInfoWithEpisodesResponse(
            podcastInfo = podcastInfo,
            episodes = episodes,
            paginatorInfo = PodcastsInfoWithEpisodesResponse.PodcastEpisodesPaginatorInfo(
                totalNumberOfPages,
                episodes.lastOrNull()?.publishedTime
            )
        )
    }
}