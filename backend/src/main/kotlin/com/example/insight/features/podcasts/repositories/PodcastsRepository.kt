package com.example.insight.features.podcasts.repositories

import com.example.insight.common.models.entities.Article
import com.example.insight.features.article.models.responses.ArticleInfoForUserResponse
import com.example.insight.features.article.utils.ArticleConstants
import com.example.insight.features.podcasts.models.requests.InsertPodcastEpisodeRequest
import com.example.insight.features.podcasts.models.requests.UpdatePodcastEpisodeRequest
import com.example.insight.features.podcasts.models.responses.PodcastsLatestEpisodeInfoResponse
import org.bson.types.ObjectId
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.data.domain.Sort
import org.springframework.data.mongodb.core.MongoTemplate
import org.springframework.data.mongodb.core.aggregation.*
import org.springframework.data.mongodb.core.aggregation.Aggregation.*
import org.springframework.data.mongodb.core.query.Criteria
import org.springframework.data.mongodb.core.query.Query
import org.springframework.data.mongodb.core.query.Update
import org.springframework.stereotype.Service


@Service
class PodcastsRepository {

    @Autowired
    lateinit var mongoTemplate: MongoTemplate

    fun getPodcastsLatestEpisodeInfo(): List<PodcastsLatestEpisodeInfoResponse.PodcastsInfo> {

        val aggregation = newAggregation(
            // Match only documents with source_type as "podcast"
            match(
                Criteria.where("source_type").`is`(ArticleConstants.SourceType.PODCAST)
                    .and("podcast_info.source_name").`in`("LISTEN_NOTES")
            ),

            // Lookup to fetch corresponding episodes from "articles" collection
            LookupOperation.newLookup()
                .from("articles")
                .localField("_id")
                .foreignField("source_id")
                .`as`("episodes"),

            // Unwind the episodes array
            unwind("episodes", true),

            // Group by podcast id and source_reference_id to find the latest episode date
            group("_id")
                .count().`as`("totalNumberOfEpisodes")
                .max("episodes.published_time").`as`("latestEpisodeTime")
                .first("podcast_info.source_reference_id").`as`("sourceReferenceId"),


            // Project only source_reference_id and latestEpisodeDate
            project()
                .and("_id").`as`("podcastId")
                .and("sourceReferenceId").`as`("sourceReferenceId")
                .and("latestEpisodeTime").`as`("latestEpisodeTime")
                .and("totalNumberOfEpisodes").`as`("totalNumberOfEpisodes")
        )

        // Execute aggregation and retrieve results
        val results = mongoTemplate.aggregate(
            aggregation,
            "article_sources",
            PodcastsLatestEpisodeInfoResponse.PodcastsInfo::class.java
        )
        return results.mappedResults
    }

    fun insertPodcastEpisode(
        podcastId: String,
        request: InsertPodcastEpisodeRequest
    ): ObjectId {

        val newArticleIdObj = ObjectId()

        val article = Article(
            newArticleIdObj,
            request.podcastEpisodeInfo.sourceAudioUrl,
            request.title,
            request.shortDescription,
            request.publishedTime,
            request.lastUpdatedTime,
            ObjectId(podcastId),
            request.tags,
            request.imageUrl,
            null,
            request.authors,
            false,
            hashMapOf(),
            request.podcastEpisodeInfo,
            ArticleConstants.ContentType.PODCAST_EPISODE
        )

        mongoTemplate.insert(article, "articles")

        return newArticleIdObj
    }

    fun updatePodcastEpisode(
        episodeId: String,
        request: UpdatePodcastEpisodeRequest
    ): Boolean? {

        val query = Query(Criteria.where("_id").`is`(ObjectId(episodeId)))

        val update = Update()
        update.set("url", request.episodeUrl)

        val result = mongoTemplate.updateFirst(query, update, Article::class.java)

        return if (result.matchedCount > 0) {
            result.modifiedCount > 0
        } else {
            null // Article not found
        }
    }

    fun getPaginatedEpisodesOfAPodcast(
        podcastId: String,
        cursor: String?,
        pageCount: Long
    ): List<ArticleInfoForUserResponse> {

        val podcastMatchCriteria: Criteria = Criteria.where("source_id").`is`(ObjectId(podcastId))

        val cursorMatchCriteria = if (cursor != null && cursor != "") {
            Criteria.where("published_time").lt(cursor)
        } else {
            Criteria()
        }

        val isDuplicateFromSourceCriteria = Criteria.where("podcast_episode_info.is_duplicate_from_source").ne(true)

        val operations: List<AggregationOperation> = listOf(
            MatchOperation(podcastMatchCriteria),
            MatchOperation(isDuplicateFromSourceCriteria),
            sort(Sort.by(Sort.Direction.DESC, "published_time")),
            MatchOperation(cursorMatchCriteria),
            limit(pageCount),
            project()
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
                .and("ai_generated_info").`as`("aiGeneratedInfo")
                .and("podcast_episode_info").`as`("podcast_episode_info")
        )

        val aggregation: Aggregation = newAggregation(*operations.toTypedArray()).withOptions(
            AggregationOptions.builder().allowDiskUse(true).build()
        )

        return mongoTemplate.aggregate(aggregation, "articles", ArticleInfoForUserResponse::class.java).mappedResults
    }

    fun getTotalEpisodesCountOfAPodcast(podcastId: String, pageCount: Long): Long {

        val query = Query(Criteria.where("source_id").`is`(ObjectId(podcastId)))
        return mongoTemplate.count(query, ArticleInfoForUserResponse::class.java, "articles")
    }
}