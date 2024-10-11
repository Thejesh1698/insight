package com.example.insight.features.podcasts.controllers

import com.example.insight.common.models.responses.SuccessResponse
import com.example.insight.features.podcasts.models.requests.InsertPodcastEpisodeRequest
import com.example.insight.features.podcasts.models.requests.UpdatePodcastEpisodeRequest
import com.example.insight.features.podcasts.models.responses.PodcastsLatestEpisodeInfoResponse
import com.example.insight.features.podcasts.models.responses.SavePodcastEpisodeResponse
import com.example.insight.features.podcasts.services.PodcastsService
import jakarta.servlet.http.HttpServletRequest
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.validation.annotation.Validated
import org.springframework.web.bind.annotation.*

@RestController
@CrossOrigin(origins = ["http://localhost:8000"])
@RequestMapping("/cloud/podcasts")
@Validated
class PodcastsCloudController {

    @Autowired
    lateinit var podcastsService: PodcastsService

    @GetMapping("/latest-episode-info", produces = ["application/json"])
    fun getPodcastsLatestEpisodeInfo(
        request: HttpServletRequest,
    ): ResponseEntity<PodcastsLatestEpisodeInfoResponse> {

        val response = podcastsService.getPodcastsLatestEpisodeInfo()
        return ResponseEntity(
            response, HttpStatus.OK
        )
    }

    @PostMapping("/{podcastId}/episodes", produces = ["application/json"])
    fun insertPodcastEpisode(
        request: HttpServletRequest,
        @PathVariable podcastId: String,
        @RequestBody requestBody: InsertPodcastEpisodeRequest
    ): ResponseEntity<SavePodcastEpisodeResponse> {

        val episodeId = podcastsService.insertPodcastEpisode(podcastId, requestBody)
        return ResponseEntity(
            SavePodcastEpisodeResponse(episodeId), HttpStatus.OK
        )
    }

    @PutMapping("/{podcastId}/episodes/{episodeId}", produces = ["application/json"])
    fun updatePodcastEpisode(
        request: HttpServletRequest,
        @PathVariable podcastId: String,
        @RequestBody requestBody: UpdatePodcastEpisodeRequest, @PathVariable episodeId: String
    ): ResponseEntity<SuccessResponse> {

        val isEpisodeUpdated = podcastsService.updatePodcastEpisode(
            episodeId,
            requestBody
        )

        return if (isEpisodeUpdated) {
            ResponseEntity(
                SuccessResponse(), HttpStatus.OK
            )
        } else {
            ResponseEntity(
                SuccessResponse(), HttpStatus.NO_CONTENT
            )
        }
    }
}