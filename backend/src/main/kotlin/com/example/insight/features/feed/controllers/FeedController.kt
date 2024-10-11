package com.example.insight.features.feed.controllers

import com.example.insight.common.models.entities.User
import com.example.insight.features.feed.models.responses.UserEpisodeFeedResponse
import com.example.insight.features.feed.models.responses.UserFeedResponse
import com.example.insight.features.feed.models.responses.UserPodcastFeedResponse
import com.example.insight.features.feed.services.FeedService
import jakarta.servlet.http.HttpServletRequest
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.validation.annotation.Validated
import org.springframework.web.bind.annotation.*

@RestController
@CrossOrigin(origins = ["http://localhost:8000"])
@RequestMapping("/client/users/{userId}/feed")
@Validated
class FeedController {

    @Autowired
    lateinit var feedService: FeedService

    @GetMapping(produces = ["application/json"])
    fun getUserFeed(
        @RequestParam sessionId: Long? = null,
        @RequestParam page: Int,
        request: HttpServletRequest, @PathVariable userId: Long,
    ): ResponseEntity<UserFeedResponse> {

        val user = request.getAttribute("user") as User
        val feed = feedService.getUserFeed(
            user,
            page,
            sessionId
        )

        return ResponseEntity(
            feed, HttpStatus.OK
        )
    }

    @GetMapping("/podcasts", produces = ["application/json"])
    fun getUserPodcastFeed(
        @RequestParam sessionId: Long? = null,
        @RequestParam page: Int,
        request: HttpServletRequest, @PathVariable userId: Long,
    ): ResponseEntity<UserPodcastFeedResponse> {

        val user = request.getAttribute("user") as User
        val feed = feedService.getUserPodcastFeed(
            user,
            sessionId, page
        )

        return ResponseEntity(
            feed, HttpStatus.OK
        )
    }

    @GetMapping("/podcast-episodes", produces = ["application/json"])
    fun getUserPodcastEpisodeFeed(
        @RequestParam sessionId: Long? = null,
        @RequestParam page: Int,
        request: HttpServletRequest, @PathVariable userId: Long,
    ): ResponseEntity<UserEpisodeFeedResponse> {

        val user = request.getAttribute("user") as User
        val feed = feedService.getUserPodcastEpisodeFeed(
            user,
            sessionId, page
        )

        return ResponseEntity(
            feed, HttpStatus.OK
        )
    }
}