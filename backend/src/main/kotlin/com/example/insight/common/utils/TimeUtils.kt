package com.example.insight.common.utils

import java.sql.Timestamp
import java.time.Duration
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.*
import org.slf4j.Logger


fun secondsSinceGivenTimestamp(timestamp: Timestamp): Long {

    val localDateTime: LocalDateTime = timestamp.toLocalDateTime()
    val utcZone = ZoneId.of("UTC")
    val zonedDateTime = ZonedDateTime.of(localDateTime, utcZone)

    val currentUtcTime = ZonedDateTime.now(ZoneId.of("UTC"))
    val duration: Duration = Duration.between(zonedDateTime, currentUtcTime)

    return duration.seconds
}

fun getArticlePublishedTimeInEpoch(articleId: String, publishedTime: String?, logger: Logger): Long? {

    return try {
        val formatter = DateTimeFormatter.ofPattern("[yyyy-MM-dd'T'HH:mm:ss[XXX][X]][yyyy-MM-dd]", Locale.ENGLISH)
        val zonedDateTime = ZonedDateTime.parse(publishedTime, formatter)
        zonedDateTime.toEpochSecond()
    } catch (e: Exception) {
        logger.error("Unable to convert articlePublisedTime to epoch seconds --- articleId: $articleId | publishedTime: $publishedTime")
        null
    }
}

fun getCurrentTimeStampOfIndianTimeZone(): Long {
    return ZonedDateTime.now(ZoneId.of("Asia/Kolkata"))
        .toInstant()
        .toEpochMilli()
}