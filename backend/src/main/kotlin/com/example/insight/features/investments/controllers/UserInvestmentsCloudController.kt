package com.example.insight.features.investments.controllers

import com.example.insight.common.models.responses.CommonResponse
import com.example.insight.common.models.responses.SuccessResponse
import com.example.insight.common.utils.thirdParties.kite.services.KiteService
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
@RequestMapping("/cloud/investments")
class UserInvestmentsCloudController {

    @Autowired
    lateinit var userInvestmentsService: UserInvestmentsService

    @Autowired
    lateinit var kiteService: KiteService

    @PostMapping("/kite/instruments", consumes = ["application/json"], produces = ["application/json"])
    fun updateKiteInstruments(
        request: HttpServletRequest,
        @RequestParam exchange: UserInvestmentsConstants.StockExchanges
    ): ResponseEntity<CommonResponse> {

        userInvestmentsService.updateKiteInstruments(exchange)

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }

    @PostMapping("/options/historic-prices", consumes = ["application/json"], produces = ["application/json"])
    fun updateHistoricPrices(
        request: HttpServletRequest,
        @RequestParam("fromTimeInEpochSeconds") fromTimeInEpochSeconds: Long,
        @RequestParam("toTimeInEpochSeconds") toTimeInEpochSeconds: Long,
        @RequestParam offset: Int
    ): ResponseEntity<CommonResponse> {

        userInvestmentsService.updateHistoricPrices(fromTimeInEpochSeconds, toTimeInEpochSeconds, offset)

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }

    @PostMapping("/options/live-prices", consumes = ["application/json"], produces = ["application/json"])
    fun updateLivePrices(
        request: HttpServletRequest,
    ): ResponseEntity<CommonResponse> {

        userInvestmentsService.updateLivePrices()

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }

    @PostMapping("/kite/regenerate-access-token", consumes = ["application/json"], produces = ["application/json"])
    fun regenerateAccessToken(
        request: HttpServletRequest,
    ): ResponseEntity<CommonResponse> {

        kiteService.regenerateAccessToken()

        return ResponseEntity(
            SuccessResponse(), HttpStatus.OK
        )
    }
}