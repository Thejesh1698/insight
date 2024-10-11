package com.example.insight.features.investments.controllers

import com.example.insight.common.models.entities.User
import com.example.insight.common.models.responses.SuccessResponse
import com.example.insight.features.investments.models.requests.UpdateTransactionStatusRequest
import com.example.insight.features.investments.models.responses.GetUserStockInvestmentsResponse
import com.example.insight.features.investments.models.responses.InvestmentsImportTransactionResponse
import com.example.insight.features.investments.services.UserInvestmentsService
import com.example.insight.features.investments.utils.UserInvestmentsConstants
import jakarta.servlet.http.HttpServletRequest
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.validation.annotation.Validated
import org.springframework.web.bind.annotation.*

@RestController
@CrossOrigin(origins = ["http://localhost:8000"])
@Validated
@RequestMapping("/client/users/{userId}/investments")
class UserInvestmentsController {

    @Autowired
    lateinit var userInvestmentsService: UserInvestmentsService

    @PostMapping("/stocks/import", produces = ["application/json"])
    fun createStocksImportTransaction(
        request: HttpServletRequest,
        @PathVariable userId: String,
        @RequestParam("importType") importType: UserInvestmentsConstants.ImportType,
        @RequestParam("broker") broker: UserInvestmentsConstants.BROKERS? = null,
    ): ResponseEntity<InvestmentsImportTransactionResponse> {

        val user = request.getAttribute("user") as User
        val response = userInvestmentsService.createStocksImportTransaction(user, importType, broker)
        return ResponseEntity(
            response, HttpStatus.OK
        )
    }

    @PutMapping("/stocks/import/authorized", produces = ["application/json"])
    fun updateTransactionStatusToAuthorized(
        request: HttpServletRequest,
        @PathVariable userId: String,
        @RequestBody payload: UpdateTransactionStatusRequest
    ): ResponseEntity<SuccessResponse> {

        val user = request.getAttribute("user") as User
        userInvestmentsService.updateTransactionStatusToAuthorized(user.userId,payload.smallCaseTransactionId)
        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }

    @GetMapping("/stocks", produces = ["application/json"])
    fun getUserStockInvestments(
        request: HttpServletRequest,
        @PathVariable userId: String,
        @RequestParam smallCaseAuthToken: String? = null,
        @RequestParam("pollingCount") pollingCount: Int,
    ): ResponseEntity<GetUserStockInvestmentsResponse> {

        val user = request.getAttribute("user") as User
        val response = userInvestmentsService.getUserStockInvestments(user.userId, pollingCount, smallCaseAuthToken)
        return ResponseEntity(
            response, HttpStatus.OK
        )
    }
}