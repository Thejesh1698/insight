package com.example.insight.features.footPrints.services

import com.fasterxml.jackson.databind.ObjectMapper
import com.example.insight.features.footPrints.models.requests.ArticleOpenTrackingRequest
import com.example.insight.features.footPrints.models.requests.ArticleSummaryReadTrackingRequest
import com.example.insight.features.footPrints.models.requests.ArticleVisibilityTrackingRequest
import com.example.insight.features.footPrints.repositories.FootPrintsRepository
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service

@Service
class FootPrintsService {

    @Autowired
    lateinit var footPrintsRepository: FootPrintsRepository

    private val objectMapper = ObjectMapper()

    fun articleVisibilityTracking(request: ArticleVisibilityTrackingRequest): ArrayList<HashMap<String, Any?>> {

        val errorRequests = arrayListOf<HashMap<String, Any?>>()
        for (footPrint in request.footPrints) {
            try {
                val userId = footPrint.userId
                val activityId = footPrint.activityId
                val contentId = footPrint.contentId
                val contentPosition = objectMapper.writeValueAsString(
                    footPrint.contentPosition
                )
                val activityType = footPrint.activityType

                footPrintsRepository.insertArticleVisibilityTracking(userId, activityId, contentId, contentPosition, activityType)
            } catch (exception: Exception) {
                errorRequests.add(
                    hashMapOf(
                        "sqsRequestId" to footPrint.sqsRequestId,
                        "exception" to exception.message
                    )
                )
            }
        }

        return errorRequests
    }

    fun articleOpenTracking(request: ArticleOpenTrackingRequest): ArrayList<HashMap<String, Any?>> {

        val errorRequests = arrayListOf<HashMap<String, Any?>>()
        for (footPrint in request.footPrints) {
            try {
                val userId = footPrint.userId
                val activityId = footPrint.activityId
                val contentId = footPrint.contentId
                val activityType = footPrint.activityType

                footPrintsRepository.updateArticleOpenTracking(userId, activityId, contentId, activityType)
            } catch (exception: Exception) {
                errorRequests.add(
                    hashMapOf(
                        "sqsRequestId" to footPrint.sqsRequestId,
                        "exception" to exception.message
                    )
                )
            }
        }

        return errorRequests
    }

    fun articleSummaryReadTracking(request: ArticleSummaryReadTrackingRequest): ArrayList<HashMap<String, Any?>> {

        val errorRequests = arrayListOf<HashMap<String, Any?>>()
        for (footPrint in request.footPrints) {
            try {
                val userId = footPrint.userId
                val activityId = footPrint.activityId
                val contentId = footPrint.contentId
                val activityType = footPrint.activityType

                footPrintsRepository.updateArticleSummaryReadTracking(userId, activityId, contentId, activityType)
            } catch (exception: Exception) {
                errorRequests.add(
                    hashMapOf(
                        "sqsRequestId" to footPrint.sqsRequestId,
                        "exception" to exception.message
                    )
                )
            }
        }

        return errorRequests
    }
}