package com.example.insight.features.investments.controllers

import com.example.insight.common.models.responses.CommonResponse
import com.example.insight.common.models.responses.SuccessResponse
import com.example.insight.features.investments.services.UserInvestmentsService
import jakarta.servlet.http.HttpServletRequest
import org.apache.commons.io.IOUtils
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.validation.annotation.Validated
import org.springframework.web.bind.annotation.*
import java.io.BufferedReader
import java.io.InputStreamReader

@RestController
@CrossOrigin(origins = ["http://localhost:8000"])
@Validated
@RequestMapping("/public/investments")
class UserInvestmentsPublicController {

    @Autowired
    lateinit var userInvestmentsService: UserInvestmentsService

    @PostMapping("/stocks/import-webhook", consumes = ["application/json"], produces = ["application/json"])
    fun stocksImportWebhook(
        request: HttpServletRequest
    ): ResponseEntity<CommonResponse> {

        val jsonBody = IOUtils.toString(BufferedReader(InputStreamReader(request.inputStream)))
        try {
            userInvestmentsService.processStocksImportWebhook(jsonBody)
        } catch (exception: Exception) {
            exception.printStackTrace()
            println(jsonBody)
        }

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }
}