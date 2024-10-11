package com.example.insight.features.podcasts.models.requests

import com.example.insight.common.models.entities.Article

data class InsertPodcastEpisodeRequest (
    val imageUrl: String?,
    val publishedTime: String,
    val lastUpdatedTime: String?,
    val shortDescription: String?,
    val tags: ArrayList<String> = arrayListOf(),
    val title: String,
    val reactions: HashMap<String, Long> = hashMapOf(),
    val authors: ArrayList<String> = arrayListOf(),
    val podcastEpisodeInfo: Article.PodcastEpisodeInfo,
)