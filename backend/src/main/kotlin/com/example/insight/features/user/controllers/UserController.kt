package com.example.insight.features.user.controllers

import com.example.insight.common.models.entities.User
import com.example.insight.common.models.responses.CommonResponse
import com.example.insight.common.models.responses.SuccessResponse
import com.example.insight.features.user.models.requests.UpdateUserDetailsRequest
import com.example.insight.features.user.models.requests.UserInterestedTopicsRequest
import com.example.insight.features.user.models.responses.*
import com.example.insight.features.user.services.UserService
import jakarta.servlet.http.HttpServletRequest
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.validation.annotation.Validated
import org.springframework.web.bind.annotation.*

@RestController
@CrossOrigin(origins = ["http://localhost:8000"])
@RequestMapping("/client/users")
@Validated
class UserController {

    @Autowired
    lateinit var userService: UserService

    @PutMapping("/{userId}", produces = ["application/json"])
    fun updateUserDetails(
        @RequestBody requestBody: UpdateUserDetailsRequest,
        request: HttpServletRequest, @PathVariable userId: Long,
    ): ResponseEntity<CommonResponse> {

        val user = request.getAttribute("user") as User
        val areDetailsUpdated = userService.updateUserDetails(
            user,
            requestBody
        )

        return ResponseEntity(
            SuccessResponse(), if (areDetailsUpdated) {
                HttpStatus.OK
            } else {
                HttpStatus.NO_CONTENT
            }
        )
    }

    @GetMapping("/{userId}/interests/topics", produces = ["application/json"])
    fun getUserInterestedTopics(
        request: HttpServletRequest, @PathVariable userId: Long,
    ): ResponseEntity<CommonResponse> {

        val user = request.getAttribute("user") as User
        val interestedTopics = userService.getUserInterestedTopics(
            user
        )

        return ResponseEntity(
            UserInterestedTopicsResponse(interestedTopics), HttpStatus.OK
        )
    }

    @PostMapping("/{userId}/interests/topics", produces = ["application/json"])
    fun upsertUserInterestedTopics(
        @RequestBody requestBody: UserInterestedTopicsRequest,
        request: HttpServletRequest, @PathVariable userId: Long,
    ): ResponseEntity<CommonResponse> {

        val user = request.getAttribute("user") as User
        userService.upsertUserInterestedTopics(
            user,
            requestBody
        )

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }

    @GetMapping("/{userId}/app-summary", produces = ["application/json"])
    fun getUserAppSummary(
        request: HttpServletRequest, @PathVariable userId: Long,
    ): ResponseEntity<UserAppSummaryResponse> {

        val user = request.getAttribute("user") as User
        val summary = userService.getUserAppSummary(
            user
        )

        return ResponseEntity(
            summary, HttpStatus.OK
        )
    }

    @PostMapping("/{userId}/article-bookmarks", produces = ["application/json"])
    fun saveArticleBookmark(
        request: HttpServletRequest, @PathVariable userId: Long,
        @RequestParam("articleId") articleId:String
    ): ResponseEntity<SaveArticleBookmarkResponse> {

        val user = request.getAttribute("user") as User
        val bookmarkId = userService.saveArticleBookmark(
            user.userId,
            articleId
        )

        return ResponseEntity(
            SaveArticleBookmarkResponse(bookmarkId), HttpStatus.OK
        )
    }

    @DeleteMapping("/{userId}/article-bookmarks/{bookmarkId}", produces = ["application/json"])
    fun deleteArticleBookmark(
        request: HttpServletRequest, @PathVariable userId: Long,
        @PathVariable bookmarkId:Long
    ): ResponseEntity<CommonResponse> {

        val user = request.getAttribute("user") as User
        userService.deleteArticleBookmark(
            user.userId,
            bookmarkId
        )

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }

    @PostMapping("/{userId}/article-reading-history", produces = ["application/json"])
    fun addArticleToReadingHistory(
        request: HttpServletRequest, @PathVariable userId: Long,
        @RequestParam("articleId") articleId:String
    ): ResponseEntity<AddArticleToReadingHistoryResponse> {

        val user = request.getAttribute("user") as User
        val historyId = userService.addArticleToReadingHistory(
            user.userId,
            articleId
        )

        return ResponseEntity(
            AddArticleToReadingHistoryResponse(historyId), HttpStatus.OK
        )
    }

    @DeleteMapping("/{userId}/article-reading-history/{historyId}", produces = ["application/json"])
    fun deleteArticleFromReadingHistory(
        request: HttpServletRequest, @PathVariable userId: Long,
        @PathVariable historyId:Long
    ): ResponseEntity<CommonResponse> {

        val user = request.getAttribute("user") as User
        userService.deleteArticleFromReadingHistory(
            user.userId,
            historyId
        )

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }

    @GetMapping("/{userId}/article-bookmarks", produces = ["application/json"])
    fun getUserArticleBookmarks(
        request: HttpServletRequest, @PathVariable userId: Long,
        @RequestParam("cursor") cursor: Long?
    ): ResponseEntity<UserArticleBookmarksResponse> {

        val user = request.getAttribute("user") as User
        val bookmarks = userService.getUserArticleBookmarks(
            user, cursor
        )

        return ResponseEntity(
            bookmarks, HttpStatus.OK
        )
    }

    @GetMapping("/{userId}/article-reading-history", produces = ["application/json"])
    fun getUserArticleReadingHistory(
        request: HttpServletRequest, @PathVariable userId: Long,
        @RequestParam("cursor") cursor: Long?
    ): ResponseEntity<UserArticleReadingHistoryResponse> {

        val user = request.getAttribute("user") as User
        val history = userService.getUserArticleReadingHistory(
            user, cursor
        )

        return ResponseEntity(
            history, HttpStatus.OK
        )
    }

    @GetMapping("/{userId}/article-interactions-state", produces = ["application/json"])
    fun getUserArticleInteractionsState(
        request: HttpServletRequest, @PathVariable userId: Long,
        @RequestParam("articleIds") articleIds: List<String>
    ): ResponseEntity<UserArticleInteractionsStateResponse> {

        val states = userService.getUserArticleInteractionsState(
            userId,
            articleIds
        )

        return ResponseEntity(
            UserArticleInteractionsStateResponse(
                states
            ), HttpStatus.OK
        )
    }
}