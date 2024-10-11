package com.example.insight.features.investments.services


import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.example.insight.common.errorHandler.exceptions.BadRequestException
import com.example.insight.common.errorHandler.exceptions.ForbiddenRequestException
import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.models.entities.User
import com.example.insight.common.models.entities.UserInvestmentOption
import com.example.insight.common.utils.thirdParties.kite.models.responses.KiteInstrumentsInfo
import com.example.insight.common.utils.thirdParties.kite.models.responses.KiteHistoricPricesInfo
import com.example.insight.common.utils.thirdParties.kite.services.KiteService
import com.example.insight.common.utils.thirdParties.smallCase.services.SmallCaseService
import com.example.insight.features.investments.models.InvestmentHistoryInsertInputClass
import com.example.insight.features.investments.models.SmallCaseStockImportTransactionNotes
import com.example.insight.features.investments.models.responses.GetUserStockInvestmentsResponse
import com.example.insight.features.investments.models.requests.SmallCaseStocksImportWebhookPayload
import com.example.insight.features.investments.models.responses.InvestmentsImportTransactionResponse
import com.example.insight.features.investments.repositories.UserInvestmentsRepository
import com.example.insight.features.investments.utils.UserInvestmentUtils
import com.example.insight.features.investments.utils.UserInvestmentsConstants
import com.example.insight.features.investments.utils.UserInvestmentsConstants.STOCKS_FETCH_MAX_POLLING_COUNT
import com.example.insight.features.investments.utils.UserInvestmentsConstants.STOCK_HOLDINGS_IMPORT_LIMIT_PER_DAY
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.io.File
import java.time.Instant
import java.time.temporal.ChronoUnit

@Service
class UserInvestmentsService {

    @Autowired
    lateinit var smallCaseService: SmallCaseService

    @Autowired
    lateinit var userInvestmentsRepository: UserInvestmentsRepository

    @Autowired
    lateinit var kiteService: KiteService

    @Autowired
    lateinit var userInvestmentUtils: UserInvestmentUtils

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    val objectMapper: ObjectMapper = ObjectMapper().registerModule(KotlinModule())

    @Transactional("userDatabaseTransactionManager")
    fun createStocksImportTransaction(
        user: User,
        importType: UserInvestmentsConstants.ImportType,
        broker: UserInvestmentsConstants.BROKERS?
    ): InvestmentsImportTransactionResponse {

        val userSmallCaseAuthToken = when (importType) {
            UserInvestmentsConstants.ImportType.REFRESH -> {
                if (broker == null) {
                    logger.error(
                        "Broker value cannot be null --- userId: ${user.userId} | importType: $importType "
                    )
                    throw BadRequestException()
                }

                validateStocksImportRequest(user.userId, broker)
                fetchUserSmallCaseAuthTokenFromDb(user.userId, broker)
            }

            UserInvestmentsConstants.ImportType.NEW -> "guest"
        }
        val notes = SmallCaseStockImportTransactionNotes(
            userId = user.userId,
            importType = importType
        )

        if (importType == UserInvestmentsConstants.ImportType.REFRESH && broker == UserInvestmentsConstants.BROKERS.KITE) {
            val areHoldingsImported = importHoldingsDirectlyFromVendor(user, userSmallCaseAuthToken)
            return InvestmentsImportTransactionResponse(
                null,
                null,
                areHoldingsImported
            )
        }

        val (sdkToken, transactionResponse, smallCaseResponseString) = smallCaseService.createTransaction(
            user,
            userSmallCaseAuthToken,
            importType == UserInvestmentsConstants.ImportType.NEW,
            objectMapper.writeValueAsString(notes)
        )

        storeSmallCaseTransactionDetails(
            user.userId,
            transactionResponse.transactionId,
            transactionResponse.expireAt,
            smallCaseResponseString,
            broker
        )
        return InvestmentsImportTransactionResponse(
            transactionId = transactionResponse.transactionId,
            sdkToken = sdkToken
        )
    }

    private fun fetchUserSmallCaseAuthTokenFromDb(userId: Long, broker: UserInvestmentsConstants.BROKERS): String {

        return userInvestmentsRepository.getUserSmallCaseAuthToken(
            userId,
            broker
        ) ?: run {
            logger.error(
                "Existing small case auth token doesn't exist. Invalid request params! --- userId: $userId | " +
                        "broker: $broker"
            )
            throw BadRequestException()
        }
    }

    private fun storeSmallCaseTransactionDetails(
        userId: Long,
        smallCaseTransactionId: String,
        expireAtTimeStamp: String,
        smallCaseEntireResponse: String,
        broker: UserInvestmentsConstants.BROKERS?
    ) {

        val expireAtEpochMs = Instant.parse(expireAtTimeStamp).toEpochMilli()
        userInvestmentsRepository.insertSmallCaseTransactionDetails(
            userId,
            smallCaseTransactionId,
            expireAtEpochMs,
            smallCaseEntireResponse,
            broker
        )
    }

    private fun importHoldingsDirectlyFromVendor(user: User, userSmallCaseAuthToken: String): Boolean {

        //small case supports importing holdings directly for KITE.
        // implement this by yourself with edge cases considered.
        return false
    }

    private fun validateStocksImportRequest(userId: Long, broker: UserInvestmentsConstants.BROKERS) {

        val fromTime = Instant.now().truncatedTo(ChronoUnit.DAYS).toString() // Start of today, UTC
        val count = userInvestmentsRepository.getStocksImportTransactionsCount(
            userId,
            broker,
            fromTime
        )

        if (count >= STOCK_HOLDINGS_IMPORT_LIMIT_PER_DAY) {
            logger.error("Stocks holding refresh limit reached for today. --- userId: $userId | broker: $broker")
            throw BadRequestException()
        }
    }

    fun updateTransactionStatusToAuthorized(userId: Long, smallCaseTransactionId: String) {

        userInvestmentsRepository.updateTransactionStatusToAuthorized(
            smallCaseTransactionId
        )
    }

    fun getUserStockInvestments(userId: Long, pollingCount: Int, smallCaseAuthToken: String?): GetUserStockInvestmentsResponse {

        if (pollingCount > STOCKS_FETCH_MAX_POLLING_COUNT) {
            logger.error("Invalid pollingCount. --- userId: $userId | pollingCount: $pollingCount")
            throw BadRequestException()
        }

        val latestStockInvestments = userInvestmentsRepository.getUserStockInvestments(userId)

        val fromTime = Instant.now().truncatedTo(ChronoUnit.DAYS).toString() // Start of today, UTC
        val linkedBrokers = userInvestmentsRepository.getUserLinkedBrokers(userId, fromTime)
        var totalInvestmentValue = 0F
        val brokersHash = linkedBrokers.associateBy { it.name }
        val investmentHash = hashMapOf<Long, GetUserStockInvestmentsResponse.StockInvestmentDetails>()

        for (investment in latestStockInvestments) {
            totalInvestmentValue += investment.investedValue
            brokersHash[investment.broker]?.let {
                it.stockCount += 1
            }

            investmentHash[investment.investmentOptionId]?.let {

                it.shareQuantity += investment.shareQuantity
                it.investedValue += investment.investedValue
                it.averageSharePrice =
                    if (it.shareQuantity > 0) (it.shareQuantity * it.investedValue) / it.shareQuantity else 0F
            } ?: run {
                investmentHash[investment.investmentOptionId] = investment
            }
        }

        val sortedInvestments = investmentHash.values.sortedByDescending { it.investedValue }
        val anyActiveFetchTransactionOverAll = userInvestmentsRepository.hasActiveFetchTransaction(userId)
        val lastFetchedOverAll = if(linkedBrokers.isNotEmpty()) {
            linkedBrokers.maxOf { it.lastFetched }
        } else {
            null
        }

        return GetUserStockInvestmentsResponse(
            totalInvestmentValue = totalInvestmentValue,
            lastFetched = lastFetchedOverAll,
            investments = sortedInvestments,
            linkedBrokers = linkedBrokers,
            activeFetchTransactionInProgress = anyActiveFetchTransactionOverAll,
        )
    }

    @Transactional("userDatabaseTransactionManager")
    fun processStocksImportWebhook(jsonBody: String) {

        val webhookPayload = objectMapper.readValue(jsonBody, SmallCaseStocksImportWebhookPayload::class.java)
        val generatedCheckSum =
            smallCaseService.generateChecksum(webhookPayload.timestamp, webhookPayload.smallcaseAuthId)

        if (generatedCheckSum != webhookPayload.checksum) {
            logger.error(
                "Checksums didn't match in small case stocks import webhook call --- " +
                        "generatedCheckSum: $generatedCheckSum | jsonBody: $jsonBody"
            )
            throw ForbiddenRequestException()
        }

        val broker = UserInvestmentsConstants.BROKERS.fromSmallCaseEnum(webhookPayload.broker) ?: run {
            logger.error("Unrecognised broker value --- broker: ${webhookPayload.broker} | " +
                    "webhookPayload: $webhookPayload")
            throw InternalServerErrorException()
        }

        val notes = webhookPayload.notes?.let {
            objectMapper.readValue(it, SmallCaseStockImportTransactionNotes::class.java)
        } ?: run {
            logger.error("notes cannot be null in small-case's webhook payload --- webhookPayload: $webhookPayload")
            throw InternalServerErrorException()
        }

        val investments = hashMapOf<String, InvestmentHistoryInsertInputClass>()
        val stockTickers = hashSetOf<String>()

        for (security in webhookPayload.securities) {
            var totalSharesQuantity =
                security.holdings.quantity + security.positions.nse.quantity + security.positions.bse.quantity

            var totalInvestmentValue = (security.holdings.quantity * security.holdings.averagePrice) +
                    (security.positions.nse.quantity * security.positions.nse.averagePrice) +
                    (security.positions.bse.quantity * security.positions.bse.averagePrice)
            var overallAveragePrice = if (totalSharesQuantity > 0) totalInvestmentValue / totalSharesQuantity else 0F

            val (ticker, tickerSymbolWithExchange) = if(security.nseTicker != null) {
                Pair(security.nseTicker, "NSE:${security.nseTicker}")
            } else if(security.bseTicker != null) {
                Pair(security.bseTicker, "BSE:${security.bseTicker}")
            } else {
                logger.error("Either of nseTicker or bseTicker have to be not null --- " +
                        "userId: ${notes.userId} | transactionId: ${webhookPayload.transactionId} | " +
                        "webhookPayload: $webhookPayload")
                throw InternalServerErrorException()
            }

            investments[tickerSymbolWithExchange]?.let {
                totalSharesQuantity += (it.shareQuantity)
                totalInvestmentValue += (it.shareQuantity * it.averagePrice)
                overallAveragePrice = if (totalSharesQuantity > 0) totalInvestmentValue / totalSharesQuantity else 0F
            }

            investments[tickerSymbolWithExchange] = InvestmentHistoryInsertInputClass(
                totalSharesQuantity,
                overallAveragePrice
            )

            stockTickers.add(ticker)
        }

        val smallCaseTransactionRecord = userInvestmentsRepository.getSmallCaseTransactionInfo(
            webhookPayload.transactionId
        ) ?: run {
            logger.error("Can't find any smallCaseTransactionRef for given small case transaction id --- " +
                    "userId: ${notes.userId} | transactionId: ${webhookPayload.transactionId} | " +
                    "webhookPayload: $webhookPayload")
            throw InternalServerErrorException()
        }

        if(webhookPayload.securities.isNotEmpty()) {
            val investmentOptions = userInvestmentsRepository.getStockInvestmentOptionIdsByTicker(stockTickers.toList())

            for(option in investmentOptions) {
                option.nseTicker?.let {ticker ->
                    investments["NSE:${ticker}"]?.let {
                        it.investmentOptionId = option.investmentOptionId
                    }
                }

                option.bseTicker?.let {ticker ->
                    investments["BSE:${ticker}"]?.let {
                        it.investmentOptionId = option.investmentOptionId
                    }
                }
            }

            userInvestmentsRepository.deleteOldInvestmentsOfUser(notes.userId, broker)
            userInvestmentsRepository.insertInvestmentsForUser(
                notes.userId,
                smallCaseTransactionRecord.transactionRef,
                investments,
                broker
            )
        }

        userInvestmentsRepository.updateSmallCaseTransactionInfo(
            smallCaseTransactionRecord.smallcaseTransactionId,
            broker,
            jsonBody
        )

        if (notes.importType == UserInvestmentsConstants.ImportType.NEW) {
            userInvestmentsRepository.insertSmallCaseAuthToken(
                notes.userId,
                webhookPayload.smallcaseAuthId,
                broker
            )
        }
    }

    @Transactional("userDatabaseTransactionManager")
    fun updateKiteInstruments(exchange: UserInvestmentsConstants.StockExchanges) {

        lateinit var file: File
        try {
            file = kiteService.downloadInstrumentsFile()
            val instruments = kiteService.processInstrumentsFile(file, exchange)
            initialiseInvestmentOptionIds(instruments, exchange)
            userInvestmentsRepository.upsertInstruments(instruments.values.toList(), exchange)

            // TODO: take this condition as a value of param via api input
            if(exchange == UserInvestmentsConstants.StockExchanges.NSE) {
                userInvestmentsRepository.updateAllStocksStatusAsInActive()
            }

            val investmentOptionIds: List<Long> = instruments.values.map { it.investmentOptionId }
            userInvestmentsRepository.updateStocksActiveStatus(investmentOptionIds)
        } finally {
            file.delete()
        }
    }

    private fun initialiseInvestmentOptionIds(
        instruments: HashMap<String, KiteInstrumentsInfo>,
        exchange: UserInvestmentsConstants.StockExchanges
    ) {

        val tickers = instruments.keys
        val existingInvestmentOptions = userInvestmentsRepository.getStockInvestmentOptionIdsByTicker(tickers.toList())
        val existingTickersSet = existingInvestmentOptions.map {
            when(exchange) {
                UserInvestmentsConstants.StockExchanges.NSE -> it.nseTicker
                UserInvestmentsConstants.StockExchanges.BSE -> it.bseTicker
            }
        }.toSet()
        var missingTickers = tickers - existingTickersSet
        val probableSimilarInvestmentOptions = mutableListOf<UserInvestmentOption>()
        val tickersOfProbableSimilarStocks = mutableSetOf<String>()

        existingInvestmentOptions.forEach { investmentOption ->
            when(exchange) {
                UserInvestmentsConstants.StockExchanges.NSE -> {
                    if (investmentOption.bseTicker in missingTickers) {
                        probableSimilarInvestmentOptions.add(investmentOption)
                        investmentOption.bseTicker?.let {
                            tickersOfProbableSimilarStocks.add(it)
                            investmentOption.nseTicker = it
                        }
                    }
                }
                UserInvestmentsConstants.StockExchanges.BSE -> {
                    if (investmentOption.nseTicker in missingTickers) {
                        probableSimilarInvestmentOptions.add(investmentOption)
                        investmentOption.nseTicker?.let {
                            tickersOfProbableSimilarStocks.add(it)
                            investmentOption.bseTicker = it
                        }
                    }
                }
            }
        }
        when (exchange) {
            UserInvestmentsConstants.StockExchanges.NSE -> userInvestmentsRepository.updateNseTickerInfoFromProbableBSEStocks(
                probableSimilarInvestmentOptions
            )

            UserInvestmentsConstants.StockExchanges.BSE -> userInvestmentsRepository.updateBseTickerInfoFromProbableNSEStocks(
                probableSimilarInvestmentOptions
            )
        }

        missingTickers = missingTickers - tickersOfProbableSimilarStocks
        val missingInvestmentOptions = missingTickers.mapNotNull { instruments[it] }

        val insertedStockOptions = userInvestmentsRepository.insertInstrumentsAsInvestmentOptions(missingInvestmentOptions, exchange)

        for(investmentOption in existingInvestmentOptions) {
            val ticker = when (exchange) {
                UserInvestmentsConstants.StockExchanges.NSE -> investmentOption.nseTicker
                UserInvestmentsConstants.StockExchanges.BSE -> investmentOption.bseTicker
            }
            instruments[ticker]?.let {
                it.investmentOptionId = investmentOption.investmentOptionId
            } ?: run {
                logger.error("Cannot find corresponding investmentOption in instruments --- instruments: $instruments | " +
                        "existingInvestmentOptions: $existingInvestmentOptions | ticker: $ticker")
                throw InternalServerErrorException()
            }
        }

        for(investmentOption in insertedStockOptions) {
            val ticker = when (exchange) {
                UserInvestmentsConstants.StockExchanges.NSE -> investmentOption.nseTicker
                UserInvestmentsConstants.StockExchanges.BSE -> investmentOption.bseTicker
            }
            instruments[ticker]?.let {
                it.investmentOptionId = investmentOption.investmentOptionId
            } ?: run {
                logger.error("Cannot find corresponding investmentOption in instruments --- instruments: $instruments | " +
                        "existingInvestmentOptions: $existingInvestmentOptions | ticker: $ticker")
                throw InternalServerErrorException()
            }
        }
    }

    fun updateHistoricPrices(fromTimeInEpochSeconds: Long, toTimeInEpochSeconds: Long, offset: Int) {

        var count = 0;
        val startTime = System.currentTimeMillis()
        var lastTokenTriedToProcess: String? = null
        try{
            val tickerInstrumentIdsMap = userInvestmentsRepository.getAllTickerAndInstrumentTokensInfo(offset)
            for((investmentOptionId, instrumentData) in tickerInstrumentIdsMap) {
                val (instrumentToken, exchange) = instrumentData
                val historicPrices = kiteService.getHistoricPrices(instrumentToken, fromTimeInEpochSeconds, toTimeInEpochSeconds)

                //historicPrices response format: [timestamp, open, high, low, close, volume]
                val historicPriceObjects = historicPrices.map { entry ->

                    KiteHistoricPricesInfo(
                        date = entry[0].toString(),
                        openPrice = entry[1].toString().toFloat(),
                        highPrice = entry[2].toString().toFloat(),
                        lowPrice = entry[3].toString().toFloat(),
                        closePrice = entry[4].toString().toFloat(),
                        volume = entry[5].toString().toBigInteger(),
                        exchange = exchange
                    )
                }

                if(historicPriceObjects.isNotEmpty()) {
                    userInvestmentsRepository.storeStockHistoricPricesInDb(investmentOptionId, historicPriceObjects)
                }
                count += 1
                lastTokenTriedToProcess = instrumentToken
                Thread.sleep(250)
            }
        } catch (exception: Exception) {
            val endTime = System.currentTimeMillis()
            exception.printStackTrace()
            println()
            println("count in updateHistoricPrices: $count")
            println("endTime - startTime in updateHistoricPrices: ${endTime - startTime}")
            println("lastTokenTriedToProcess: $lastTokenTriedToProcess")
        }
    }

    fun updateLivePrices() {

        if(!userInvestmentUtils.isIndianTradeMarketLiveNow()) {
            return
        }
        val instrumentOptions = userInvestmentsRepository.getAllKiteTradingSymbolInfo()
        val chunkedInstrumentOptions = instrumentOptions.chunked(500)

        chunkedInstrumentOptions.forEach { chunk ->
            run {
                val livePrices = kiteService.getLivePricesOfInstruments(chunk)
                userInvestmentsRepository.storeLivePrices(chunk, livePrices)
                Thread.sleep(1000)
            }
        }
    }
}