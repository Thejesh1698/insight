package com.example.insight.features.article.models.responses

import com.fasterxml.jackson.annotation.JsonIgnore
import com.example.insight.common.models.entities.Article
import com.example.insight.common.models.entities.ArticleAiGeneratedMetaInfo
import com.example.insight.features.article.utils.ArticleConstants
import org.springframework.data.mongodb.core.mapping.Field


data class ArticleInfoForUserResponse(
    val articleId: String,
    val url: String,
    val title: String? = null,
    val shortDescription: String? = null,
    val publishedTime: String? = null,
    val lastUpdatedTime: String? = null,
    val tags: ArrayList<String>?,
    val articleImageUrl: String?,
    val category: String?,
    val authors: List<String>,
    val isPremiumArticle: Boolean?,
    val source: ArticleInformationResponse.ArticleSourceInformation? = null,
    val reactions: HashMap<Int, Long>,
    @JsonIgnore
    val aiGeneratedInfo: ArticleAiGeneratedMetaInfo? = null,

    @Field("podcast_episode_info")
    val podcastEpisodeInfo: Article.PodcastEpisodeInfo? = null,

    @Field("comments_info")
    val commentsInfo: Article.ArticleCommentsInfo? = null,
) {
    var userReaction: Int? = null
    var aiGeneratedSummary: AiGeneratedInfo? = null
    var aiGeneratedTitle: AiGeneratedInfo? = null
    var articleDateInMilliEpoch: Long? = null
    data class AiGeneratedInfo(
        val value: String,
        val infoSource: String,
        val valueType: ArticleConstants.ContentSummaryValueTypes = ArticleConstants.ContentSummaryValueTypes.STRING
    )
}