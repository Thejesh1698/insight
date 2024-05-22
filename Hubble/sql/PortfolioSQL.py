from datetime import datetime
from typing import List, Union
import json
import os
import logging
import pandas as pd
from sql.PostgresDatabaseOperation import PostgresDatabaseOperation

logger = logging.getLogger('__name__')
level = logging.INFO
logger.setLevel(level)


class PortfolioSQL:

    @staticmethod
    def get_all_symbol_names():
        with PostgresDatabaseOperation(db='user') as cursor:
            sql = 'SELECT DISTINCT name, nseticker FROM user_investment_options WHERE nseticker IS NOT NULL'
            cursor.execute(sql)
            results = cursor.fetchall()
        return results

    @staticmethod
    def get_user_current_holdings(user_id):
        with PostgresDatabaseOperation(db='user') as cursor:
            sql = f'''
            WITH ticker_kite_mapping as 
            (SELECT *
                FROM investment_option_kite_trading_symbol_mapping
                WHERE exchange = 'NSE'
                UNION ALL
                SELECT *
                FROM investment_option_kite_trading_symbol_mapping
                WHERE exchange = 'BSE'
                AND kite_trading_symbol NOT IN (SELECT kite_trading_symbol FROM investment_option_kite_trading_symbol_mapping WHERE exchange = 'NSE')),
            kite_quotes_mapping as
                (SELECT investment_option_id, kite_trading_symbol as ticker, CONCAT(exchange, ':', kite_trading_symbol) as kite_quotes_symbol
                FROM ticker_kite_mapping)
            SELECT DISTINCT user_id, uih.investment_option_id, uio.name, ticker, kite_quotes_symbol, quantity, average_price
              FROM user_investments uih 
              LEFT JOIN user_investment_options uio
              ON uih.investment_option_id = uio.investment_option_id
              LEFT JOIN kite_quotes_mapping ntk
              ON uio.investment_option_id = ntk.investment_option_id
              WHERE user_id = {user_id} AND average_price > 0 AND quantity > 0
            '''
            cursor.execute(sql)
            results = cursor.fetchall()
        df = pd.DataFrame(results, columns=['user_id', 'investment_option_id', 'name', 'ticker', 'kite_quotes_symbol', 'quantity', 'average_price'])
        df['quantity'] = df['quantity'].astype('float')
        df['average_price'] = df['average_price'].astype('float')
        return df

    @staticmethod
    def get_all_nse_symbols():
        with PostgresDatabaseOperation(db='user') as cursor:
            sql = f'''
            WITH ticker_kite_mapping as 
            (SELECT *
                FROM investment_option_kite_trading_symbol_mapping
                WHERE exchange = 'NSE'
                UNION ALL
                SELECT *
                FROM investment_option_kite_trading_symbol_mapping
                WHERE exchange = 'BSE'
                AND kite_trading_symbol NOT IN (SELECT kite_trading_symbol FROM investment_option_kite_trading_symbol_mapping WHERE exchange = 'NSE')),
            kite_quotes_mapping as
                (SELECT investment_option_id, kite_trading_symbol as ticker, CONCAT(exchange, ':', kite_trading_symbol) as kite_quotes_symbol
                FROM ticker_kite_mapping)
            SELECT DISTINCT uio.investment_option_id, ticker, kite_quotes_symbol, uio.name 
            FROM kite_quotes_mapping ktsm 
            INNER JOIN user_investment_options uio 
            ON ktsm.investment_option_id = uio.investment_option_id
            '''
            cursor.execute(sql)
            results = cursor.fetchall()
        df = pd.DataFrame(results, columns=['investment_option_id', 'ticker', 'kite_quotes_symbol', 'name'])
        return df

    @staticmethod
    def get_instrument_token_for_nse_ticker(nse_ticker):
        with PostgresDatabaseOperation(db='user') as cursor:
            sql = f"SELECT investment_option_id FROM investment_option_kite_trading_symbol_mapping WHERE kite_trading_symbol = '{nse_ticker}' AND exchange = 'NSE'"
            cursor.execute(sql)
            results = cursor.fetchall()
        return results[0][0]

    @staticmethod
    def get_investment_option_price_history(investment_id_list, num_days=180):
        ticker_string = ", ".join(f"'{item}'" for item in investment_id_list)
        with PostgresDatabaseOperation(db='user') as cursor:
            sql = f'''SELECT investment_option_id, price_date, close FROM investment_option_historic_price
            WHERE investment_option_id IN ({ticker_string}) AND price_date > CURRENT_DATE - INTERVAL '{num_days} DAYS'
            '''
            cursor.execute(sql)
            results = cursor.fetchall()
        df = pd.DataFrame(results, columns=['investment_option_id', 'dt', 'price'])
        return df

    @staticmethod
    def get_investment_option_price_long_history(investment_id_list, num_days=180):
        investment_id_string = ", ".join(f"'{item}'" for item in investment_id_list)
        with PostgresDatabaseOperation(db='user') as cursor:
            sql = f'''
                WITH ticker_kite_mapping as 
                (SELECT *
                    FROM investment_option_kite_trading_symbol_mapping
                    WHERE exchange = 'NSE'
                    UNION ALL
                    SELECT *
                    FROM investment_option_kite_trading_symbol_mapping
                    WHERE exchange = 'BSE'
                    AND kite_trading_symbol NOT IN (SELECT kite_trading_symbol FROM investment_option_kite_trading_symbol_mapping WHERE exchange = 'NSE')),
                kite_quotes_mapping as
                    (SELECT investment_option_id, kite_trading_symbol as ticker, exchange
                    FROM ticker_kite_mapping),
                RankedPrices AS (
                SELECT
                    investment_option_id,
                    exchange,
                    DATE(price_time) dt,
                    close price,
                    ROW_NUMBER() OVER (
                        PARTITION BY investment_option_id, DATE(price_time)
                        ORDER BY price_time DESC
                    ) AS rn
                FROM
                    investment_option_price
                WHERE investment_option_id IN ({investment_id_string})
                ),
                daily_prices AS (
                SELECT
                    investment_option_id,
                    exchange,
                    dt,
                    price
                FROM
                    RankedPrices
                WHERE
                    rn = 1)

                SELECT investment_option_id, price_date dt, close price FROM investment_option_historic_price
                WHERE investment_option_id IN ({investment_id_string}) AND price_date > CURRENT_DATE - INTERVAL '{num_days} DAYS'
                UNION ALL
                (SELECT dp.investment_option_id, dt, price 
                FROM daily_prices dp 
                INNER JOIN ticker_kite_mapping tkm ON dp.investment_option_id = tkm.investment_option_id AND dp.exchange = tkm.exchange)   
                '''
            cursor.execute(sql)
            results = cursor.fetchall()
        df = pd.DataFrame(results, columns=['investment_option_id', 'dt', 'price'])
        df['dt'] = df['dt'].astype('str')
        # df['dt'] = df['dt'].astype('datetime64[ns]')
        # df['dt'] = df['dt'].apply(lambda x: x.strftime('%Y-%m-%d'))
        df['price'] = df['price'].astype('float')
        # df['price'] = round(df['price'], 4)
        return df

    @staticmethod
    def get_latest_prices_for_instrument_ids(investment_id_list):
        investment_id_string = ", ".join(f"'{item}'" for item in investment_id_list)
        with PostgresDatabaseOperation(db='user') as cursor:
            sql = f'''
                    WITH ticker_kite_mapping as 
                    (SELECT *
                        FROM investment_option_kite_trading_symbol_mapping
                        WHERE exchange = 'NSE' AND investment_option_id IN ({investment_id_string})
                        UNION ALL
                        SELECT *
                        FROM investment_option_kite_trading_symbol_mapping
                        WHERE exchange = 'BSE' AND investment_option_id IN ({investment_id_string})
                        AND kite_trading_symbol NOT IN (SELECT kite_trading_symbol FROM investment_option_kite_trading_symbol_mapping WHERE exchange = 'NSE'))
                    
                    SELECT a.investment_option_id, a.close
                    FROM investment_option_price a
                    INNER JOIN (
                        SELECT investment_option_id, exchange, MAX(price_time) AS max_date
                        FROM investment_option_price
                        WHERE investment_option_id IN ({investment_id_string})
                        GROUP BY investment_option_id, exchange
                    ) b ON a.investment_option_id = b.investment_option_id 
                    AND a.exchange = b.exchange 
                    AND a.price_time = b.max_date
                    INNER JOIN ticker_kite_mapping c 
                    ON a.investment_option_id = c.investment_option_id AND a.exchange = c.exchange
                    WHERE a.investment_option_id IN ({investment_id_string})
                    '''
            cursor.execute(sql)
            results = cursor.fetchall()
        result_dict = {}
        for res in results:
            result_dict[res[0]] = float(res[1])
        # df = pd.DataFrame(results, columns=['investment_option_id', 'price'])
        # df['price'] = df['price'].astype('float')
        return result_dict

    @staticmethod
    def get_investment_option_id_for_kite_symbol(kite_symbols):
        kite_symbols_string = ", ".join(f"'{item}'" for item in kite_symbols)
        with PostgresDatabaseOperation(db='user') as cursor:
            sql = f'''
                SELECT CONCAT(exchange, ':', kite_trading_symbol), investment_option_id  FROM investment_option_kite_trading_symbol_mapping WHERE CONCAT(exchange, ':', kite_trading_symbol) IN ({kite_symbols_string})
                '''
            cursor.execute(sql)
            results = cursor.fetchall()
        return {x[0]: x[1] for x in results}
