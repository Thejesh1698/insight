package com.example.insight.features.footPrints.controllers

import com.example.insight.features.footPrints.models.requests.ArticleOpenTrackingRequest
import com.example.insight.features.footPrints.models.requests.ArticleSummaryReadTrackingRequest
import com.example.insight.features.footPrints.models.requests.ArticleVisibilityTrackingRequest
import com.example.insight.features.footPrints.models.responses.ArticleOpenTrackingResponse
import com.example.insight.features.footPrints.models.responses.ArticleSummaryReadTrackingResponse
import com.example.insight.features.footPrints.models.responses.ArticleVisibilityTrackingResponse
import com.example.insight.features.footPrints.services.FootPrintsService
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.validation.annotation.Validated
import org.springframework.web.bind.annotation.*

@RestController
@CrossOrigin(origins = ["http://localhost:8000"])
@RequestMapping("/cloud/foot-prints")
@Validated
class FootPrintsController {

    @Autowired
    lateinit var footPrintsService: FootPrintsService

    @PostMapping("/article-visibility-tracking", produces = ["application/json"])
    fun articleVisibilityTracking(
        @RequestBody request: ArticleVisibilityTrackingRequest
    ): ResponseEntity<ArticleVisibilityTrackingResponse> {

        val errorRequests = footPrintsService.articleVisibilityTracking(
            request
        )

        return ResponseEntity(
            ArticleVisibilityTrackingResponse(errorRequests), HttpStatus.OK
        )
    }

    @PostMapping("/article-open-tracking", produces = ["application/json"])
    fun articleOpenTracking(
        @RequestBody request: ArticleOpenTrackingRequest
    ): ResponseEntity<ArticleOpenTrackingResponse> {

        val errorRequests = footPrintsService.articleOpenTracking(
            request
        )

        return ResponseEntity(
            ArticleOpenTrackingResponse(errorRequests), HttpStatus.OK
        )
    }

    @PostMapping("/article-summary-read-tracking", produces = ["application/json"])
    fun articleSummaryReadTracking(
        @RequestBody request: ArticleSummaryReadTrackingRequest
    ): ResponseEntity<ArticleSummaryReadTrackingResponse> {

        val errorRequests = footPrintsService.articleSummaryReadTracking(
            request
        )

        return ResponseEntity(
            ArticleSummaryReadTrackingResponse(errorRequests), HttpStatus.OK
        )
    }
}