package com.example.insight.common.models.entities

import com.fasterxml.jackson.annotation.JsonProperty
import com.example.insight.features.article.utils.ArticleConstants
import com.example.insight.features.podcasts.utils.PodcastsConstants
import org.bson.types.ObjectId
import org.springframework.data.annotation.Id
import org.springframework.data.mongodb.core.mapping.Document
import org.springframework.data.mongodb.core.mapping.Field
import java.math.BigInteger
import java.util.Date
import kotlin.collections.ArrayList

@Document(collection = "articles")
data class Article(
    @Id
    val articleId: ObjectId,

    val url: String,
    val title: String? = null,

    @Field("short_description")
    val shortDescription: String? = null,

    @Field("published_time")
    val publishedTime: String? = null,

    @Field("last_updated_time")
    val lastUpdatedTime: String? = null,

    @Field("source_id")
    val sourceId: ObjectId,

    val tags: ArrayList<String>?,

    @Field("image_url")
    val articleImageUrl: String?,

    val category: String?,
    val authors: List<String>,

    @Field("is_premium_article")
    val isPremiumArticle: Boolean?,

    val reactions: HashMap<Int, Long>,

    @Field("podcast_episode_info")
    val podcastEpisodeInfo: PodcastEpisodeInfo? = null,

    @Field("content_type")
    val contentType: ArticleConstants.ContentType = ArticleConstants.ContentType.ARTICLE,

    @Field("source_medium")
    val sourceMedium : ArticleConstants.SourceMedium = ArticleConstants.SourceMedium.WEB_SCRAPING,

    @Field("cleaned_text")
    val cleanedText: String? = null,
) {
    data class PodcastEpisodeInfo(
        @Field("source_reference_id")
        val sourceReferenceId: String,

        @Field("source_reference_url")
        val sourceReferenceUrl: String?,

        @Field("source_audio_url")
        val sourceAudioUrl: String,

        @Field("file_size")
        val fileSize: Int?,

        @Field("source_guid")
        val sourceGuid: String?,

        @Field("episode_length")
        val episodeLength: Long?,

        @Field("episode_type")
        val episodeType: PodcastsConstants.EpisodeType?,

        @Field("rating_count")
        val ratingCount: Int?,

        @Field("rating_average")
        val ratingAverage: Float?
    )

    data class ArticleCommentsInfo(
        val count: BigInteger
    )
}

data class ArticleAiGeneratedMetaInfo(
    val summary: HashMap<String, Any?>?,
    val title: HashMap<String, Any?>?
) {
    data class AiGeneratedInfo(
        val value: String,

        @JsonProperty("additional_info")
        val additionalInfo: HashMap<String, Any?>?,

        @JsonProperty("generated_at")
        val generatedAt: Date
    )
}