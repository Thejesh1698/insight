package com.example.insight.features.article.controllers

import com.example.insight.common.models.entities.User
import com.example.insight.common.models.responses.CommonResponse
import com.example.insight.common.models.responses.SuccessResponse
import com.example.insight.features.article.models.requests.*
import com.example.insight.features.article.models.responses.*
import com.example.insight.features.article.services.ArticleService
import jakarta.servlet.http.HttpServletRequest
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.validation.annotation.Validated
import org.springframework.web.bind.annotation.*

@RestController
@CrossOrigin(origins = ["http://localhost:8000"])
@Validated
class ArticleController {

    @Autowired
    lateinit var articleService: ArticleService

    @PostMapping("/cloud/articles", produces = ["application/json"])
    fun insertArticle(
        @RequestBody request: InsertArticleRequest
    ): ResponseEntity<UpsertArticleResponse> {

        return ResponseEntity(
            articleService.insertArticle(
                request
            ), HttpStatus.OK
        )
    }

    @PostMapping("/cloud/articles/filter/un-scraped", produces = ["application/json"])
    fun filterUnScrapedArticles(
        @RequestBody request: FilterUnScrapedArticlesRequest
    ): ResponseEntity<FilterUnScrapedArticlesResponse> {

        val urls = articleService.filterUnScrapedArticles(request.urls)
        return ResponseEntity(
            FilterUnScrapedArticlesResponse(
                urls = urls
            ), HttpStatus.OK
        )
    }
    @GetMapping("/cloud/articles/{articleId}", produces = ["application/json"])
    fun getArticle(
        @PathVariable articleId: String,
        @RequestParam("fetchSourceInfo") fetchSourceInfo: Boolean = false,
    ): ResponseEntity<ArticleInformationResponse> {

        return ResponseEntity(
            articleService.getArticle(
                articleId,
                fetchSourceInfo
            ), HttpStatus.OK
        )
    }

    @PutMapping("/cloud/articles/{articleId}", produces = ["application/json"])
    fun updateArticle(
        @PathVariable articleId: String,
        @RequestBody request: UpdateArticleRequest
    ): ResponseEntity<SuccessResponse> {

        val (_, isArticleUpdated) = articleService.updateArticle(
            articleId,
            request
        )

        return if (isArticleUpdated) {
            ResponseEntity(
                SuccessResponse(), HttpStatus.OK
            )
        } else {
            ResponseEntity(
                SuccessResponse(), HttpStatus.NO_CONTENT
            )
        }
    }

    @GetMapping("/public/articles/topics", produces = ["application/json"])
    fun getAllArticleTopics(): ResponseEntity<ArticleTopicsResponse> {

        val allTopics = articleService.getAllArticleTopics()
        return ResponseEntity(
            ArticleTopicsResponse(allTopics), HttpStatus.OK
        )
    }

    @PostMapping("/client/articles/{articleId}/reactions", produces = ["application/json"])
    fun saveUserArticleReaction(
        @PathVariable articleId: String,
        request: HttpServletRequest,
        @RequestBody requestBody: UserArticleReactionRequest,
    ): ResponseEntity<CommonResponse> {

        val user = request.getAttribute("user") as User
        articleService.saveUserArticleReaction(
            user,
            articleId,
            requestBody,
        )

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }

    @DeleteMapping("/client/articles/{articleId}/reactions", produces = ["application/json"])
    fun deleteUserArticleReaction(
        @PathVariable articleId: String,
        request: HttpServletRequest,
        @RequestBody requestBody: UserArticleReactionRequest,
    ): ResponseEntity<CommonResponse> {

        val user = request.getAttribute("user") as User
        articleService.deleteUserArticleReaction(
            user,
            articleId,
            requestBody,
        )

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }

    @PutMapping("/cloud/articles/{articleId}/reactions/count", produces = ["application/json"])
    fun updateArticleReactionCount(
        @PathVariable articleId: String,
        @RequestBody request: UpdateArticleReactionCount
    ): ResponseEntity<SuccessResponse> {

        articleService.updateArticleReactionCount(articleId, request)

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }

    @PutMapping("/cloud/articles/{articleId}/comments/count", produces = ["application/json"])
    fun updateArticleCommentsCount(
        @PathVariable articleId: String,
        @RequestBody request: UpdateArticleCommentsCount
    ): ResponseEntity<SuccessResponse> {

        articleService.updateArticleCommentsCount(articleId, request)

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }

    @PutMapping("/cloud/articles/{articleId}/ai-generated-info", produces = ["application/json"])
    fun updateAiGeneratedInfoForArticle(
        @PathVariable articleId: String,
        @RequestBody request: AiGeneratedInfoForArticleRequest
    ): ResponseEntity<SuccessResponse> {

        val isArticleUpdated = articleService.updateAiGeneratedInfoForArticle(articleId, request)

        return if (isArticleUpdated) {
            ResponseEntity(
                SuccessResponse(), HttpStatus.OK
            )
        } else {
            ResponseEntity(
                SuccessResponse(), HttpStatus.NO_CONTENT
            )
        }
    }

    @PostMapping("/client/articles/{articleId}/comments", produces = ["application/json"])
    fun saveArticleComment(
        @PathVariable articleId: String,
        request: HttpServletRequest,
        @RequestBody requestBody: ArticleCommentRequest,
    ): ResponseEntity<SaveArticleCommentResponse> {

        val user = request.getAttribute("user") as User
        val response = articleService.saveArticleComment(
            user,
            articleId,
            requestBody,
        )

        return ResponseEntity(
            response,
            HttpStatus.OK
        )
    }

    @DeleteMapping("/client/articles/{articleId}/comments/{commentId}", produces = ["application/json"])
    fun deleteArticleComment(
        @PathVariable articleId: String,
        @PathVariable commentId: Long,
        request: HttpServletRequest
    ): ResponseEntity<CommonResponse> {

        val user = request.getAttribute("user") as User
        articleService.deleteArticleComment(
            user,
            articleId,
            commentId,
        )

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }

    @GetMapping("/client/articles/{articleId}/comments", produces = ["application/json"])
    fun getArticleComments(
        @PathVariable articleId: String,
        request: HttpServletRequest
    ): ResponseEntity<ArticleCommentsResponse> {

        val comments = articleService.getArticleComments(
            articleId
        )

        return ResponseEntity(
            ArticleCommentsResponse(comments), HttpStatus.OK
        )
    }

    @GetMapping("/client/articles/topics", produces = ["application/json"])
    fun getCategorizedArticleTopics(): ResponseEntity<CategorizedArticleTopicsResponse> {

        val response = articleService.getCategorizedArticleTopics()
        return ResponseEntity(
            response, HttpStatus.OK
        )
    }

    @PostMapping("/client/content/{contentId}/preference", produces = ["application/json"])
    fun saveUserContentPreference(
            @PathVariable contentId: String,
            request: HttpServletRequest,
            @RequestBody requestBody: UserContentPreferenceRequest,
    ) : SuccessResponse {

        val user = request.getAttribute("user") as User
        articleService.saveOrDeleteUserContentPreference(user, contentId, requestBody)

        return SuccessResponse()
    }

    @GetMapping("/client/content/report-reasons", produces = ["application/json"])
    fun getContentReportReasons(): ResponseEntity<GetReportReasonsResponse> {

        val allReasons = articleService.getContentReportReasons()
        return ResponseEntity(
                GetReportReasonsResponse(allReasons),HttpStatus.OK
        )
    }

    @PostMapping("/client/content/{contentId}/report", produces = ["application/json"])
    fun reportContent(
            @PathVariable contentId: String,
            request: HttpServletRequest,
            @RequestBody requestBody: ReportContentRequest,
    ): ResponseEntity<SuccessResponse> {

        val user = request.getAttribute("user") as User
        val response = articleService.reportContent(
                user,
                contentId,
                requestBody,
        )
        return ResponseEntity(
                response,
                HttpStatus.OK
        )
    }

    @PostMapping("/cloud/articles/register-search-articles" , produces = ["application/json"])
    fun  registerSearchArticles(@RequestBody requests : ArticleAndSourceRegisterRequest) : InsertArticleWithSourceResponse {

        return articleService.registerSearchArticles(requests)
    }
}