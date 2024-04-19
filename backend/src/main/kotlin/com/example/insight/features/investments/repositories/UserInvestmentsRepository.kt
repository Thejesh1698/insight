package com.example.insight.features.investments.repositories

import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.models.entities.UserInvestmentOption
import com.example.insight.common.models.entities.UserInvestmentOptionRowMapper
import com.example.insight.common.models.entities.UserSmallcaseTransaction
import com.example.insight.common.models.entities.UserSmallcaseTransactionRowMapper
import com.example.insight.common.utils.thirdParties.kite.models.responses.KiteHistoricPricesInfo
import com.example.insight.common.utils.thirdParties.kite.models.responses.KiteInstrumentsInfo
import com.example.insight.common.utils.thirdParties.kite.models.responses.KiteOHLCQuotesApiResponse
import com.example.insight.features.investments.models.InvestmentHistoryInsertInputClass
import com.example.insight.features.investments.models.InvestmentOptionAndKiteTradingSymbol
import com.example.insight.features.investments.models.responses.GetUserStockInvestmentsResponse
import com.example.insight.features.investments.utils.UserInvestmentsConstants
import com.example.insight.features.investments.utils.UserInvestmentsConstants.STOCK_HOLDINGS_IMPORT_LIMIT_PER_DAY
import jakarta.annotation.PostConstruct
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.beans.factory.annotation.Qualifier
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate
import org.springframework.jdbc.core.namedparam.SqlParameterSource
import org.springframework.jdbc.support.GeneratedKeyHolder
import org.springframework.stereotype.Repository
import java.sql.Timestamp


@Repository
class UserInvestmentsRepository {

    @Autowired
    @Qualifier("userDatabaseJdbcTemplate")
    private lateinit var jdbcTemplate: JdbcTemplate

    lateinit var namedParameterJdbcTemplate: NamedParameterJdbcTemplate

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    @PostConstruct
    fun initNamedParameterJdbcTemplate() {
        namedParameterJdbcTemplate = NamedParameterJdbcTemplate(jdbcTemplate)
    }

    fun insertSmallCaseTransactionDetails(
        userId: Long,
        smallCaseTransactionId: String,
        expireAtEpochMs: Long,
        smallCaseEntireResponse: String,
        broker: UserInvestmentsConstants.BROKERS?,
        transactionType: UserInvestmentsConstants.SmallCaseTransactionTypes = UserInvestmentsConstants.SmallCaseTransactionTypes.HOLDINGS_IMPORT
    ) {

        val queryString = "INSERT " +
                "INTO " +
                "user_smallcase_transactions " +
                "( " +
                "   user_id, smallcase_transaction_id, transaction_type, transaction_status, expire_at, " +
                "   vendor_response, broker" +
                ") " +
                "VALUES " +
                "(?, ?, ?, ?, ?, ?::jsonb, ?); "

        jdbcTemplate.update(
            queryString,
            userId,
            smallCaseTransactionId,
            transactionType.toString(),
            UserInvestmentsConstants.SmallCaseTransactionStatus.STARTED.toString(),
            expireAtEpochMs,
            smallCaseEntireResponse,
            broker?.toString()
        )
    }

    fun getUserSmallCaseAuthToken(userId: Long, broker: UserInvestmentsConstants.BROKERS): String? {

        val paramMap = mapOf(
            "broker" to broker.toString(),
            "userId" to userId
        )
        val query = "SELECT " +
                "smallcase_auth_token " +
                "FROM " +
                "user_smallcase_broker_auth_tokens " +
                "WHERE user_id = :userId and broker = :broker; "

        return namedParameterJdbcTemplate.query(
            query, paramMap
        )
        { rs, _ ->

            rs.getString("smallcase_auth_token")
        }.firstOrNull()
    }

    fun getStocksImportTransactionsCount(
        userId: Long,
        broker: UserInvestmentsConstants.BROKERS,
        fromTime: String
    ): Int {

        val paramMap = mapOf(
            "broker" to broker.toString(),
            "userId" to userId,
            "fromTime" to fromTime,
            "transactionType" to UserInvestmentsConstants.SmallCaseTransactionTypes.HOLDINGS_IMPORT.toString()
        )
        val query = "SELECT " +
                "COUNT(*) as total_count " +
                "FROM " +
                "user_smallcase_transactions " +
                "WHERE user_id = :userId and broker = :broker and " +
                "transaction_type = :transactionType and created_at >= CAST(:fromTime AS TIMESTAMP WITH TIME ZONE); "

        return namedParameterJdbcTemplate.query(
            query, paramMap
        )
        { rs, _ ->
            rs.getInt("total_count")
        }.firstOrNull() ?: 0
    }

    fun updateTransactionStatusToAuthorized(smallCaseTransactionId: String) {

        val queryString = "UPDATE " +
                "user_smallcase_transactions " +
                "SET " +
                "transaction_status = ?, " +
                "last_updated = now() " +
                "WHERE smallcase_transaction_id = ? and transaction_status = ?; "

        jdbcTemplate.update(
            queryString,
            UserInvestmentsConstants.SmallCaseTransactionStatus.AUTHORIZED.toString(),
            smallCaseTransactionId,
            UserInvestmentsConstants.SmallCaseTransactionStatus.STARTED.toString()
        )
    }

    fun getUserStockInvestments(userId: Long): List<GetUserStockInvestmentsResponse.StockInvestmentDetails> {

        val paramMap = mapOf(
            "userId" to userId
        )
        val query = "SELECT ush.*,uio.*  " +
                "FROM " +
                "user_investments as ush " +
                "INNER JOIN " +
                "user_investment_options as uio " +
                "USING(investment_option_id) " +
                "where user_id = :userId; "

        return namedParameterJdbcTemplate.query(
            query, paramMap
        ) { rs, _ ->
            GetUserStockInvestmentsResponse.StockInvestmentDetails(
                name = rs.getString("name"),
                nseTicker = rs.getString("nse_ticker"),
                bseTicker = rs.getString("bse_ticker"),
                shareQuantity = rs.getLong("quantity"),
                averageSharePrice = rs.getFloat("average_price"),
                investedValue = rs.getLong("quantity") * rs.getFloat("average_price"),
                broker = UserInvestmentsConstants.BROKERS.valueOf(rs.getString("broker")),
                investmentOptionId = rs.getLong("investment_option_id")
            )
        }
    }

    fun getUserLinkedBrokers(
        userId: Long,
        fromTime: String
    ): List<GetUserStockInvestmentsResponse.BrokerInvestmentInfo> {

        val paramMap = mapOf(
            "userId" to userId,
            "fromTime" to fromTime
        )
        val query = "WITH broker_transactions AS ( " +
                "    SELECT " +
                "        broker, " +
                "        MAX(last_updated) FILTER (WHERE transaction_status = 'COMPLETED') AS last_fetched, " +
                "        COUNT(*) FILTER (WHERE transaction_status IN ('COMPLETED', 'AUTHORIZED') AND " +
                "        created_at > CAST(:fromTime AS TIMESTAMP WITH TIME ZONE)) AS transactions_count, " +
                "        BOOL_OR(transaction_status = 'AUTHORIZED') AS any_active_fetch_transaction " +
                "    FROM " +
                "        user_smallcase_transactions " +
                "    WHERE " +
                "            user_id = :userId " +
                "    AND " +
                "            transaction_status IN ('COMPLETED', 'AUTHORIZED')" +
                "    GROUP BY " +
                "        broker " +
                ") " +
                "SELECT " +
                "    bt.broker, " +
                "    bt.last_fetched, " +
                "    bt.transactions_count, " +
                "    bt.any_active_fetch_transaction " +
                "FROM " +
                "    broker_transactions bt " +
                "WHERE bt.broker is not null ; "

        return namedParameterJdbcTemplate.query(
            query, paramMap
        ) { rs, _ ->
            val broker = UserInvestmentsConstants.BROKERS.valueOf(rs.getString("broker"))
            val lastFetchedTimestamp = rs.getTimestamp("last_fetched")
            val lastFetchedEpochMilli = lastFetchedTimestamp.toInstant().toEpochMilli()
            val anyActiveTransaction = rs.getBoolean("any_active_fetch_transaction")

            GetUserStockInvestmentsResponse.BrokerInvestmentInfo(
                name = broker,
                stockCount = 0L,
                lastFetched = lastFetchedEpochMilli,
                iconUrl = broker.logoUrl,
                isRefreshPossible = rs.getInt("transactions_count") < STOCK_HOLDINGS_IMPORT_LIMIT_PER_DAY,
                anyActiveFetchTransaction = anyActiveTransaction,
            )
        }
    }

    fun getStockInvestmentOptionIdsByTicker(tickers: List<String>): List<UserInvestmentOption> {

        val paramMap = mapOf(
            "tickers" to tickers,
        )

        val query = "SELECT * " +
                "FROM " +
                "user_investment_options " +
                "WHERE " +
                "nse_ticker in (:tickers) or bse_ticker in (:tickers); "

        return namedParameterJdbcTemplate.query(query, paramMap, UserInvestmentOptionRowMapper())
    }

    fun insertInstrumentsAsInvestmentOptions(instruments: List<KiteInstrumentsInfo>, exchange: UserInvestmentsConstants.StockExchanges):
            List<UserInvestmentOption> {

        val sql = "INSERT INTO " +
                "user_investment_options " +
                "(name, nse_ticker, bse_ticker) " +
                "VALUES (:name, :nseTicker, :bseTicker) " +
                "ON CONFLICT " +
                "DO NOTHING " +
                "RETURNING investment_option_id, name, nse_ticker, bse_ticker, created_at; "


        val batchValues = instruments.map { instrument ->
            MapSqlParameterSource()
                .addValue("name", instrument.instrumentName)
                .addValue("nseTicker", if(exchange == UserInvestmentsConstants.StockExchanges.NSE) instrument.ticker else null)
                .addValue("bseTicker", if(exchange == UserInvestmentsConstants.StockExchanges.BSE) instrument.ticker else null)
        }

        val insertedStockOptions = mutableListOf<UserInvestmentOption>()
        for (paramSource in batchValues) {
            val keyHolder = GeneratedKeyHolder()
            namedParameterJdbcTemplate.update(sql, paramSource, keyHolder)

            val generatedKeys = keyHolder.keyList
            insertedStockOptions.add(
                UserInvestmentOption(
                    investmentOptionId = (generatedKeys[0]["investment_option_id"] as Number).toLong(),
                    name = generatedKeys[0]["name"] as String,
                    nseTicker = generatedKeys[0]["nse_ticker"] as String?,
                    bseTicker = generatedKeys[0]["bse_ticker"] as String?,
                    createdAt = generatedKeys[0]["created_at"] as Timestamp
                )
            )
        }

        return insertedStockOptions
    }

    fun insertInvestmentsForUser(
        userId: Long,
        smallCaseTransactionRef: Long,
        investments: HashMap<String, InvestmentHistoryInsertInputClass>,
        broker: UserInvestmentsConstants.BROKERS
    ) {

        val sql = "INSERT INTO " +
                "user_investments " +
                "(user_id, investment_option_id, small_case_transaction_ref, quantity, average_price, broker) " +
                "VALUES (:userId, :investmentOptionId, :smallCaseTransactionRef, :quantity, :averagePrice, :broker); "

        val batchParams: Array<SqlParameterSource> = investments.values.map { investment ->
            val shareQuantity = investment.shareQuantity
            val averagePrice = investment.averagePrice

            if(investment.investmentOptionId == null) {
                logger.error("investmentOptionId cannot be null --- userId: $userId | " +
                        "smallCaseTransactionRef: $smallCaseTransactionRef | investments: $investments")
                throw InternalServerErrorException()
            }
            MapSqlParameterSource()
                .addValue("userId", userId)
                .addValue("smallCaseTransactionRef", smallCaseTransactionRef)
                .addValue("investmentOptionId", investment.investmentOptionId)
                .addValue("quantity", shareQuantity)
                .addValue("averagePrice", averagePrice)
                .addValue("broker", broker.toString())
        }.toTypedArray()

        namedParameterJdbcTemplate.batchUpdate(sql, batchParams)
    }

    fun insertSmallCaseAuthToken(
        userId: Long,
        authToken: String,
        broker: UserInvestmentsConstants.BROKERS
    ) {

        val queryString = "INSERT " +
                "INTO " +
                "user_smallcase_broker_auth_tokens " +
                "( " +
                "   user_id, smallcase_auth_token, broker " +
                ") " +
                "VALUES " +
                "(?, ?, ?) " +
                "ON CONFLICT DO NOTHING; "

        jdbcTemplate.update(
            queryString,
            userId,
            authToken,
            broker.toString()
        )
    }

    fun getSmallCaseTransactionInfo(smallCaseTransactionId: String): UserSmallcaseTransaction? {

        val paramMap = mapOf(
            "smallCaseTransactionId" to smallCaseTransactionId
        )
        val query = "SELECT " +
                "* " +
                "FROM " +
                "user_smallcase_transactions " +
                "WHERE smallcase_transaction_id = :smallCaseTransactionId; "

        return namedParameterJdbcTemplate.query(
            query, paramMap, UserSmallcaseTransactionRowMapper()
        ).firstOrNull()
    }

    fun updateSmallCaseTransactionInfo(
        smallCaseTransactionId: String,
        broker: UserInvestmentsConstants.BROKERS,
        webhookPayload: String
    ) {

        val queryString = "UPDATE " +
                "user_smallcase_transactions " +
                "SET " +
                "broker = ?, " +
                "vendor_webhook_response = ?::jsonb, " +
                "transaction_status = ?, " +
                "last_updated = now() " +
                "WHERE " +
                "smallcase_transaction_id = ?; "

        jdbcTemplate.update(
            queryString,
            broker.toString(),
            webhookPayload,
            UserInvestmentsConstants.SmallCaseTransactionStatus.COMPLETED.toString(),
            smallCaseTransactionId
        )
    }

    fun upsertInstruments(instruments: List<KiteInstrumentsInfo>, exchange: UserInvestmentsConstants.StockExchanges) {

        val sql = "INSERT INTO " +
                "investment_option_kite_trading_symbol_mapping " +
                "(investment_option_id, exchange, kite_trading_symbol, instrument_token) " +
                "VALUES (:investmentOptionId, :exchange, :kiteTradingSymbol, :instrumentToken) " +
                "ON CONFLICT (investment_option_id, exchange) " +
                "DO UPDATE SET " +
                "kite_trading_symbol = EXCLUDED.kite_trading_symbol, " +
                "instrument_token = EXCLUDED.instrument_token, " +
                "last_updated = now(); "

        val batchParams: Array<SqlParameterSource> = instruments.map { instrument ->
            MapSqlParameterSource()
                .addValue("investmentOptionId", instrument.investmentOptionId)
                .addValue("kiteTradingSymbol", instrument.kiteTradingSymbol)
                .addValue("instrumentToken", instrument.kiteInstrumentToken)
                .addValue("exchange", exchange.toString())
        }.toTypedArray()

        namedParameterJdbcTemplate.batchUpdate(sql, batchParams)
    }

    fun hasActiveFetchTransaction(userId: Long): Boolean {

        val query = "SELECT " +
                "transaction_status='AUTHORIZED' as active_fetch_transaction " +
                "FROM " +
                "user_smallcase_transactions " +
                "WHERE user_id = :userId " +
                "ORDER BY last_updated DESC " +
                "LIMIT 1;"

        val paramMap = mapOf(
            "userId" to userId
        )

        return namedParameterJdbcTemplate.query(
            query, paramMap
        )
        { rs, _ ->
            rs.getBoolean("active_fetch_transaction")
        }.firstOrNull()?: false
    }

    fun getAllTickerAndInstrumentTokensInfo(offset: Int): HashMap<Long, Pair<String, UserInvestmentsConstants.StockExchanges>> {

        val query = "SELECT " +
                "instrument_token, investment_option_id, exchange " +
                "FROM " +
                "investment_option_kite_trading_symbol_mapping " +
                "INNER JOIN " +
                "user_investment_options " +
                "USING (investment_option_id) " +
                "WHERE active = true " +
                "ORDER BY investment_option_id " +
                "LIMIT :limit OFFSET :offset;"
        val tickerSymbolInstrumentIdsMap = hashMapOf<Long, Pair<String, UserInvestmentsConstants.StockExchanges>>()

        val paramMap = mapOf(
            "limit" to 300,
            "offset" to offset
        )

        namedParameterJdbcTemplate.query(
            query,
            paramMap
        ) { rs, _ ->
            tickerSymbolInstrumentIdsMap[rs.getLong("investment_option_id")] =
                Pair(rs.getString("instrument_token"),
                    UserInvestmentsConstants.StockExchanges.valueOf(rs.getString("exchange"))
                )
        }

        return tickerSymbolInstrumentIdsMap
    }

    fun storeStockHistoricPricesInDb(investmentOptionId: Long, prices: List<KiteHistoricPricesInfo>) {

        val sql = "INSERT INTO " +
                "investment_option_historic_price " +
                "(investment_option_id, open, high, low, close, volume, price_date, exchange) " +
                "VALUES (:investmentOptionId, :open, :high, :low, :close, :volume, :priceDate::date, :exchange) " +
                "ON CONFLICT (investment_option_id, exchange, price_date) " +
                "DO UPDATE SET " +
                "open = EXCLUDED.open, " +
                "high = EXCLUDED.high, " +
                "low = EXCLUDED.low, " +
                "close = EXCLUDED.close, " +
                "volume = EXCLUDED.volume; "


        val batchValues = prices.map {
            MapSqlParameterSource()
                .addValue("investmentOptionId", investmentOptionId)
                .addValue("open", it.openPrice)
                .addValue("high", it.highPrice)
                .addValue("low", it.lowPrice)
                .addValue("close", it.closePrice)
                .addValue("volume", it.volume)
                .addValue("priceDate", it.date)
                .addValue("exchange", it.exchange.toString())
        }.toTypedArray()

        namedParameterJdbcTemplate.batchUpdate(sql, batchValues)
    }

    fun updateNseTickerInfoFromProbableBSEStocks(investmentOptions: List<UserInvestmentOption>) {

        val queryString = "UPDATE " +
                "user_investment_options " +
                "SET " +
                "nse_ticker = :bseTicker " +
                "WHERE investment_option_id = :investmentOptionId; "

        val batchValues = investmentOptions.map {
            MapSqlParameterSource()
                .addValue("investmentOptionId", it.investmentOptionId)
                .addValue("bseTicker", it.bseTicker)
        }.toTypedArray()

        namedParameterJdbcTemplate.batchUpdate(queryString, batchValues)
    }

    fun updateBseTickerInfoFromProbableNSEStocks(investmentOptions: List<UserInvestmentOption>) {

        val queryString = "UPDATE " +
                "user_investment_options " +
                "SET " +
                "bse_ticker = :nseTicker " +
                "WHERE investment_option_id = :investmentOptionId; "

        val batchValues = investmentOptions.map {
            MapSqlParameterSource()
                .addValue("investmentOptionId", it.investmentOptionId)
                .addValue("nseTicker", it.nseTicker)
        }.toTypedArray()

        namedParameterJdbcTemplate.batchUpdate(queryString, batchValues)
    }

    fun deleteOldInvestmentsOfUser(userId: Long, broker: UserInvestmentsConstants.BROKERS) {

        val queryString = "DELETE " +
                "FROM " +
                "user_investments " +
                "WHERE " +
                "user_id = ? and broker = ?; "

        jdbcTemplate.update(
            queryString,
            userId,
            broker.toString()
        )
    }

    fun getAllKiteTradingSymbolInfo(): List<InvestmentOptionAndKiteTradingSymbol> {

        val query = "SELECT iok.investment_option_id, iok.exchange, iok.kite_trading_symbol " +
                "FROM " +
                "investment_option_kite_trading_symbol_mapping as iok " +
                "order by investment_option_id; "

        return jdbcTemplate.query(
            query
        )
        { rs, _ ->
            InvestmentOptionAndKiteTradingSymbol(
                investmentOptionId = rs.getLong("investment_option_id"),
                exchange = rs.getString("exchange"),
                kiteTradingSymbol = rs.getString("kite_trading_symbol"),
            )
        }
    }

    fun storeLivePrices(
        instruments: List<InvestmentOptionAndKiteTradingSymbol>,
        livePrices: HashMap<String, KiteOHLCQuotesApiResponse.OHLCQuotesData>
    ) {

        val sql = "INSERT INTO " +
                "investment_option_price " +
                "(investment_option_id, open, high, low, close, volume, price_time, exchange) " +
                "VALUES (:investmentOptionId, :open, :high, :low, :close, :volume, now(), :exchange) " +
                "ON CONFLICT (investment_option_id, exchange, price_time) " +
                "DO UPDATE SET " +
                "open = EXCLUDED.open, " +
                "high = EXCLUDED.high, " +
                "low = EXCLUDED.low, " +
                "close = EXCLUDED.close, " +
                "volume = EXCLUDED.volume; "
        val batchParams: ArrayList<SqlParameterSource> = arrayListOf()

        for (instrument in instruments) {
            val livePrice = livePrices["${instrument.exchange}:${instrument.kiteTradingSymbol}"]
            if(livePrice != null) {
                batchParams.add(
                    MapSqlParameterSource()
                        .addValue("investmentOptionId", instrument.investmentOptionId)
                        .addValue("open", livePrice.ohlc.open)
                        .addValue("high", livePrice.ohlc.high)
                        .addValue("low", livePrice.ohlc.low)
                        .addValue("close", livePrice.lastPrice)
                        .addValue("volume", livePrice.volume ?: 0.toBigInteger())
                        .addValue("exchange", instrument.exchange)
                )
            }
            else {
                continue
            }
        }

        if(batchParams.isNotEmpty()) {
            namedParameterJdbcTemplate.batchUpdate(sql, batchParams.toTypedArray())
        }
    }

    fun updateStocksActiveStatus(investmentOptionIds: List<Long>) {

        val queryString = "UPDATE " +
                "user_investment_options " +
                "SET " +
                "active = true " +
                "WHERE " +
                "investment_option_id in (:investmentOptionIds); "

        val paramMap = mapOf(
            "investmentOptionIds" to investmentOptionIds
        )

        namedParameterJdbcTemplate.update(queryString, paramMap)
    }

    fun updateAllStocksStatusAsInActive() {

        val queryString = "UPDATE " +
                "user_investment_options " +
                "SET active = false;"

        jdbcTemplate.update(
            queryString
        )
    }
}
