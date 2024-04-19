package com.example.insight.features.podcasts.controllers

import com.example.insight.common.models.entities.User
import com.example.insight.features.podcasts.models.responses.PodcastsInfoWithEpisodesResponse
import com.example.insight.features.podcasts.services.PodcastsService
import jakarta.servlet.http.HttpServletRequest
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.validation.annotation.Validated
import org.springframework.web.bind.annotation.*

@RestController
@CrossOrigin(origins = ["http://localhost:8000"])
@RequestMapping("/client/podcasts/{podcastId}")
@Validated
class PodcastsClientController {

    @Autowired
    lateinit var podcastsService: PodcastsService

    @GetMapping(produces = ["application/json"])
    fun getPodcastInfoWithEpisodes(
        request: HttpServletRequest,
        cursor: String?, @PathVariable podcastId: String,
    ): ResponseEntity<PodcastsInfoWithEpisodesResponse> {

        val user = request.getAttribute("user") as User
        val response = podcastsService.getPodcastInfoWithEpisodes(user, podcastId, cursor)
        return ResponseEntity(
            response, HttpStatus.OK
        )
    }
}