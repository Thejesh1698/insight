package com.example.insight.common.utils.aws

object AwsConstants {
    enum class QueueUrls(val value: String) {
        ARTICLE_REACTIONS_COUNT_UPDATER("article-reactions-count-updater"),
        ARTICLE_COMMENTS_COUNT_UPDATER("article-comments-count-updater")
    }
}