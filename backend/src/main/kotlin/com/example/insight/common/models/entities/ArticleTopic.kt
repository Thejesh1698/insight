package com.example.insight.common.models.entities

import java.sql.Timestamp


data class ArticleTopic(
    val topicId: Long,
    val topicName: String,
    val category: String,
    val createdAt: Timestamp
)