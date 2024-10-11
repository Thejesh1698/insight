package com.example.insight.features.articlesSearch.controllers

import com.example.insight.common.models.responses.SuccessResponse
import com.example.insight.features.articlesSearch.models.requests.ArticlesSearchSummarySaveRequest
import com.example.insight.features.articlesSearch.services.ArticlesSearchService
import jakarta.servlet.http.HttpServletRequest
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.validation.annotation.Validated
import org.springframework.web.bind.annotation.*

@RestController
@CrossOrigin(origins = ["http://localhost:8000"])
@RequestMapping("/cloud/articles/search")
@Validated
class ArticlesSearchCloudController {

    @Autowired
    lateinit var articlesSearchService: ArticlesSearchService

    @PutMapping("/{searchId}/summary", produces = ["application/json"])
    fun saveAiGeneratedSearchSummary(
        @PathVariable searchId: Long,
        request: HttpServletRequest,
        @RequestBody requestBody: ArticlesSearchSummarySaveRequest
    ): ResponseEntity<SuccessResponse> {

        articlesSearchService.saveAiGeneratedSearchSummary(
            searchId,
            requestBody
        )

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }
}