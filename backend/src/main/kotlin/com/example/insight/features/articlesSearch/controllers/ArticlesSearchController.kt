package com.example.insight.features.articlesSearch.controllers

import com.example.insight.common.models.entities.User
import com.example.insight.features.articlesSearch.models.requests.ArticlesSearchRequest
import com.example.insight.features.articlesSearch.models.responses.ArticlesSearchResponse
import com.example.insight.features.articlesSearch.services.ArticlesSearchService
import jakarta.servlet.http.HttpServletRequest
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.validation.annotation.Validated
import org.springframework.web.bind.annotation.*


@RestController
@CrossOrigin(origins = ["http://localhost:8000"])
@RequestMapping("/client/articles/search")
@Validated
class ArticlesSearchController {

    @Autowired
    lateinit var articlesSearchService: ArticlesSearchService

    @PostMapping(produces = ["application/json"])
    fun getArticlesSearchResults(
        request: HttpServletRequest,
        @RequestBody requestBody: ArticlesSearchRequest
    ): ResponseEntity<ArticlesSearchResponse> {

        val user = request.getAttribute("user") as User
        val searchResults = articlesSearchService.getArticlesSearchResults(
            user,
            requestBody
        )

        return ResponseEntity(
            searchResults, HttpStatus.OK
        )
    }
}