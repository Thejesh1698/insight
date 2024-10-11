package com.example.insight.common.models.entities

import com.example.insight.features.article.utils.ArticleConstants
import org.bson.types.ObjectId
import org.springframework.data.annotation.Id
import org.springframework.data.mongodb.core.mapping.Document
import org.springframework.data.mongodb.core.mapping.Field

@Document(collection = "article_sources")
data class ArticleSource(
    @Id
    val sourceId: ObjectId,
    val name: String,

    @Field("logo_url")
    val logoURL: String,

    @Field("source_type")
    val sourceType: ArticleConstants.SourceType,

    @Field("source_medium")
    val sourceMedium: ArticleConstants.SourceMedium,

    @Field("podcast_info")
    val podcastInfo: PodcastMetaInfo? = null
) {

    data class PodcastMetaInfo(
        @Field("source_reference_id")
        val sourceReferenceId: String,

        @Field("description")
        val description: String? = null,

        @Field("source_reference_url")
        val sourceReferenceUrl: String? = null,

        @Field("podcast_web_url")
        val podcastWebUrl: String? = null,

        @Field("podcast_image_url")
        val podcastImageUrl: String? = null,

        @Field("podcast_rss_url")
        val podcastRssUrl: String? = null,

        val language: String? = null,

        @Field("modified_date")
        val modifiedDate: String? = null,

        @Field("rating_count")
        val ratingCount: Long? = null,

        @Field("rating_average")
        val ratingAverage: Long? = null,
    )
}