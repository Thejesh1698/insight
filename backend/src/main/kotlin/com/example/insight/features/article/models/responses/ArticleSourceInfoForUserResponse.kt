package com.example.insight.features.article.models.responses

import com.example.insight.features.article.utils.ArticleConstants
import org.springframework.data.mongodb.core.mapping.Field


data class ArticleSourceInfoForUserResponse(
    val sourceId: String,
    val name: String,
    val logoURL: String?,
    val sourceType: ArticleConstants.SourceType,
    val podcastInfo: PodcastMetaInfo? = null
) {

    data class PodcastMetaInfo(
        val description: String? = null,

        @Field("podcast_image_url")
        val podcastImageUrl: String? = null,

        @Field("podcast_author")
        val podcastAuthor: String? = null
    )
}