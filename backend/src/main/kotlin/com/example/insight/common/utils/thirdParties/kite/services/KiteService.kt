package com.example.insight.common.utils.thirdParties.kite.services


import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.example.insight.common.utils.thirdParties.kite.models.KiteTokens
import com.example.insight.common.utils.thirdParties.kite.models.requests.KiteRefreshTokenRequest
import com.example.insight.common.utils.thirdParties.kite.models.responses.*
import com.example.insight.common.utils.thirdParties.kite.repositories.KiteRepository
import com.example.insight.common.utils.thirdParties.kite.utils.KiteConstants
import com.example.insight.common.utils.thirdParties.kite.utils.KiteConstants.KITE_CONNECT_API_DOMAIN
import com.example.insight.features.investments.models.InvestmentOptionAndKiteTradingSymbol
import com.example.insight.features.investments.utils.UserInvestmentsConstants
import org.apache.commons.codec.digest.DigestUtils.sha256Hex
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.*
import org.springframework.stereotype.Service
import org.springframework.util.LinkedMultiValueMap
import org.springframework.util.MultiValueMap
import org.springframework.web.client.RestTemplate
import java.io.File
import java.nio.file.Files
import java.nio.file.Path
import java.text.SimpleDateFormat
import java.util.*
import kotlin.collections.HashMap
import org.springframework.web.util.UriComponentsBuilder

@Service
class KiteService {

    private val objectMapper: ObjectMapper = ObjectMapper().registerModule(KotlinModule())
    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    @Autowired
    lateinit var kiteRepository: KiteRepository

    fun downloadInstrumentsFile(): File {

        val headers = HttpHeaders().apply {
            accept = Collections.singletonList(MediaType.APPLICATION_OCTET_STREAM)
        }
        val entity = HttpEntity<String>(headers)
        val endpoint = KiteConstants.ApiEndPoints.INSTRUMENTS_DOWNLOAD
        val apiUrl = "${KITE_CONNECT_API_DOMAIN}/${endpoint.value}"
        val errorResponseHandler = KiteApiErrorResponseHandler(endpoint)
        lateinit var file: File

        RestTemplate().apply {
            errorHandler = errorResponseHandler
            val response = exchange(
                apiUrl,
                HttpMethod.GET,
                entity,
                ByteArray::class.java
            )

            response.body?.let { byteArray ->
                val tempFile: Path = Files.createTempFile("kiteInstruments", ".csv")
                Files.write(tempFile, byteArray)
                return tempFile.toFile()
            } ?: run {
                throw errorResponseHandler.kiteApiInternalServerException(
                    null,
                    endpoint.value,
                    objectMapper.writeValueAsString(response),
                    "response body cannot be null in Kite server api response"
                )
            }
        }

        return file
    }

    fun processInstrumentsFile(file: File, stockExchange: UserInvestmentsConstants.StockExchanges):
            HashMap<String, KiteInstrumentsInfo> {

        val tickerMap = hashMapOf<String, KiteInstrumentsInfo>()

        Files.newBufferedReader(file.toPath()).use { reader ->
            val headerLine = reader.readLine()
            val headers = headerLine.split(",")
            val exchangeIndex = headers.indexOf("exchange")
            val tradingSymbolIndex = headers.indexOf("tradingsymbol")
            val instrumentTokenIndex = headers.indexOf("instrument_token")
            val nameIndex = headers.indexOf("name")

            reader.lineSequence().drop(1) // Skip header line
                .map { it.split(",") }
                .filter { it[exchangeIndex] == stockExchange.toString() }
                .sortedBy { it[tradingSymbolIndex] }
                .forEach { line ->
                    val tradingSymbol = line[tradingSymbolIndex]
                    processTradingSymbol(tradingSymbol)?.apply {
                        val instrumentName = if (line[nameIndex].isBlank()) {
                            this.first
                        } else {
                            line[nameIndex].replace("\"", "")
                        }
                        if (!tickerMap.containsKey(this.first)) {
                            tickerMap[this.first] = KiteInstrumentsInfo(
                                this.first,
                                this.second,
                                line[instrumentTokenIndex],
                                instrumentName
                            )
                        }
                    }
                }
        }

        return tickerMap
    }

    private fun processTradingSymbol(tradingSymbol: String): Pair<String, String>? {

        val parts = tradingSymbol.split("-")
        val (ticker, kiteTradingSymbol) = when (parts.size) {
            1 -> Pair(parts[0], parts[0]) // Only parent stock code
            2 -> Pair(parts[0], tradingSymbol) // Parent and child stock code
            else -> return null // Ignoring symbols that don't match expected patterns
        }

        return Pair(ticker, kiteTradingSymbol)
    }

    fun getHistoricPrices(
        instrumentToken: String,
        fromTimeInEpochSeconds: Long,
        toTimeInEpochSeconds: Long
    ): List<List<Any>> {

        val dateFormat = SimpleDateFormat(KiteConstants.HISTORIC_PRICES_DATE_INPUT_FORMAT)
        val fromTime = dateFormat.format(Date(fromTimeInEpochSeconds * 1000))
        val toTime = dateFormat.format(Date(toTimeInEpochSeconds * 1000))
        val kiteTokens = kiteRepository.getKiteTokens()
        val authToken = "token ${kiteTokens.apiKey}:${kiteTokens.accessToken}"

        val headers = HttpHeaders().apply {
            accept = Collections.singletonList(MediaType.APPLICATION_OCTET_STREAM)
            this.add("Authorization", authToken)
        }
        val entity = HttpEntity<String>(headers)
        val endpoint = KiteConstants.ApiEndPoints.INSTRUMENT_HISTORIC_PRICES

        val apiUrl = UriComponentsBuilder
            .fromUriString("${KITE_CONNECT_API_DOMAIN}/${endpoint.value}/${instrumentToken}/day")
            .queryParam("from", fromTime)
            .queryParam("to", toTime)
            .build()
            .toUriString()

        val errorResponseHandler = KiteApiErrorResponseHandler(endpoint)

        RestTemplate().apply {
            errorHandler = errorResponseHandler
            val response = exchange(
                apiUrl,
                HttpMethod.GET,
                entity,
                String::class.java
            )

            return response.body?.let {
                val payload = objectMapper.readValue(it, KiteHistoricPricesApiResponse::class.java)

                if(payload.status != "success") {
                    throw errorResponseHandler.kiteApiInternalServerException(
                        null,
                        endpoint.value,
                        it,
                        "error in Kite server api response"
                    )
                }
                payload.data.candles
            } ?: throw errorResponseHandler.kiteApiInternalServerException(
                null,
                endpoint.value,
                objectMapper.writeValueAsString(response),
                "response body cannot be null in Kite server api response"
            )
        }
    }

    fun getLivePricesOfInstruments(instruments: List<InvestmentOptionAndKiteTradingSymbol>):
            HashMap<String, KiteOHLCQuotesApiResponse.OHLCQuotesData> {

        val kiteTokens = kiteRepository.getKiteTokens()
        val authToken = "token ${kiteTokens.apiKey}:${kiteTokens.accessToken}"
        val headers = HttpHeaders().apply {
            accept = Collections.singletonList(MediaType.APPLICATION_OCTET_STREAM)
            this.add("Authorization", authToken)
        }
        val entity = HttpEntity<String>(headers)
        val endpoint = KiteConstants.ApiEndPoints.OHLC_QUOTE

        val apiUrl = UriComponentsBuilder.fromHttpUrl("${KITE_CONNECT_API_DOMAIN}/${endpoint.value}")
            .apply {
                instruments.forEach { instrument ->
                    queryParam("i", "${instrument.exchange}:${instrument.kiteTradingSymbol}")
                }
            }.toUriString().replace("%20", " ")

        val errorResponseHandler = KiteApiErrorResponseHandler(endpoint)

        RestTemplate().apply {
            errorHandler = errorResponseHandler
            val response = exchange(
                apiUrl,
                HttpMethod.GET,
                entity,
                String::class.java
            )

            return response.body?.let {
                val payload = objectMapper.readValue(it, KiteOHLCQuotesApiResponse::class.java)

                if (payload.status != "success") {
                    throw errorResponseHandler.kiteApiInternalServerException(
                        null,
                        endpoint.value,
                        it,
                        "error in Kite server api response"
                    )
                }
                payload.data
            } ?: throw errorResponseHandler.kiteApiInternalServerException(
                null,
                endpoint.value,
                objectMapper.writeValueAsString(response),
                "response body cannot be null in Kite server api response"
            )
        }
    }

    fun regenerateAccessToken() {

        var retryCount = 5
        while(retryCount > 0) {
            try {
                val kiteTokens: KiteTokens = kiteRepository.getKiteTokens()
                val checksum: String = sha256Hex("${kiteTokens.apiKey}${kiteTokens.refreshToken}${kiteTokens.apiSecret}")
                val kiteRefreshTokenRequest = KiteRefreshTokenRequest(kiteTokens.apiKey, kiteTokens.refreshToken, checksum)
                val response: KiteRefreshTokenData = retrieveNewTokens(
                    kiteRefreshTokenRequest
                )

                val newKiteTokens = KiteTokens(
                    accessToken = response.accessToken,
                    refreshToken = response.refreshToken,
                    apiSecret = kiteTokens.apiSecret,
                    apiKey = kiteTokens.apiKey,
                )
                kiteRepository.updateKiteTokens(newKiteTokens)
                retryCount = 0
            } catch (exception: Exception) {
                exception.printStackTrace()
                logger.error("Error while regenerating kite access token --- retryCount: $retryCount")
                retryCount--
            }
        }

    }

    fun retrieveNewTokens(
        kiteRefreshTokenRequest: KiteRefreshTokenRequest
    ): KiteRefreshTokenData {

        val headers = HttpHeaders()
        headers.contentType = MediaType.APPLICATION_FORM_URLENCODED
        val map: MultiValueMap<String, String> = LinkedMultiValueMap()
        map.add("api_key", kiteRefreshTokenRequest.apiKey)
        map.add("refresh_token", kiteRefreshTokenRequest.refreshToken)
        map.add("checksum", kiteRefreshTokenRequest.checksum)
        val entity: HttpEntity<MultiValueMap<String, String>> = HttpEntity(map, headers)

        val endpoint = KiteConstants.ApiEndPoints.REFRESH_TOKEN
        val apiUrl = "${KITE_CONNECT_API_DOMAIN}/${endpoint.value}"

        val errorResponseHandler = KiteApiErrorResponseHandler(endpoint)

        RestTemplate().apply {
            errorHandler = errorResponseHandler
            val response = exchange(
                apiUrl,
                HttpMethod.POST,
                entity,
                String::class.java
            )

            return response.body?.let {
                val payload = objectMapper.readValue(it, KiteRefreshTokenResponse::class.java)

                if (payload.status != "success" || payload.data == null) {
                    throw errorResponseHandler.kiteApiInternalServerException(
                        null,
                        endpoint.value,
                        it,
                        "error in Kite server api response"
                    )
                }
                payload.data
            } ?: throw errorResponseHandler.kiteApiInternalServerException(
                null,
                endpoint.value,
                objectMapper.writeValueAsString(response),
                "response body cannot be null in Kite server api response"
            )
        }
    }

}