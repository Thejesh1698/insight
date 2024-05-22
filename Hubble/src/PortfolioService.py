import base64
import json
import os
from datetime import datetime, timedelta
import boto3
import numpy as np

from sql.PortfolioSQL import PortfolioSQL
from sql.PostgresDatabaseOperation import PostgresDatabaseOperation
from fuzzywuzzy import process, fuzz
import pandas as pd
import requests
from enum import Enum
import logging

logger = logging.getLogger('__name__')
level = logging.INFO
logger.setLevel(level)


class PortfolioAggLevel(Enum):
    OVERALL = 'overall'
    COMPANY = 'company'


class PortfolioAggMetric(Enum):
    INVESTED_VALUE = 'invested_value'
    CURRENT_VALUE = 'current_value'
    PROFIT = 'profit'
    PROFIT_PERCENT = 'profit_percent'


class GrowthAggMetric(Enum):
    GROWTH = 'growth'
    GROWTH_OVER_INDEX = 'growth_over_index'


class PortfolioService:

    def __init__(self):
        pass

    @staticmethod
    def filter_portfolio_by_name(company_name, portfolio_df):
        def get_names_to_symbol_mapping():
            d = portfolio_df[['name', 'ticker']].set_index('name').to_dict('index')
            return {k1: v1['ticker'] for k1, v1 in d.items()}

        portfolio_df = portfolio_df.drop_duplicates('name')
        names = list(portfolio_df['name'])
        symbols = list(portfolio_df['ticker'])
        mapping = get_names_to_symbol_mapping()

        name_matches = process.extract(company_name, names)
        symbol_matches = process.extract(company_name, symbols)
        best_matched_symbols = {}

        for name, score in name_matches:
            best_matched_symbols[mapping[name]] = score
        for symbol, score in symbol_matches:
            best_matched_symbols[symbol] = max(score, best_matched_symbols.get(symbol, 0))
        best_matches_list = []

        for k, v in best_matched_symbols.items():
            best_matches_list.append((k, v))
        # # sym = name_to_symbol[matching_name][0]
        matches = pd.DataFrame(best_matches_list, columns=['ticker', 'matching_score'])
        return matches[matches['matching_score'] >= 85]

    @staticmethod
    def get_latest_prices_for_tickers(kite_quote_symbols):
        # TODO: - create loop for cases with more than 500 holdings
        symbols = kite_quote_symbols[:500]
        url = "https://api.kite.trade/quote/ohlc"
        api_key = os.environ.get('KITE_API_KEY')
        access_token = os.environ.get('KITE_ACCESS_TOKEN')
        # access_token = PortfolioService.get_kite_access_token()
        headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {api_key}:{access_token}"
        }
        params = {
            "i": symbols
        }
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        last_prices = {}
        if not data:
            return last_prices
        for k, v in data['data'].items():
            last_prices[k] = v['last_price']
        return last_prices

    @staticmethod
    def get_price_history_user_holdings(user_id, num_days=180):
        holdings_df = PortfolioSQL.get_user_current_holdings(user_id=user_id)
        user_investment_ids = list(set(holdings_df['investment_option_id']))
        portfolio_history = PortfolioSQL.get_investment_option_price_history(investment_id_list=user_investment_ids, num_days=num_days)
        portfolio_history = pd.merge(portfolio_history, holdings_df[['kite_quotes_symbol', 'investment_option_id', 'ticker']], how='left', on='investment_option_id')
        kite_quotes_symbols = list(set(holdings_df['kite_quotes_symbol']))
        portfolio_current_prices = PortfolioService.get_latest_prices_from_sql(company_kite_symbols=kite_quotes_symbols)
        # portfolio_current_prices = PortfolioSQL.get_latest_prices_for_instrument_ids(investment_id_list=user_investment_ids)
        portfolio_current_prices_df = pd.DataFrame.from_dict(portfolio_current_prices, orient='index', columns=['price']).reset_index().rename(
            columns={'index': 'kite_quotes_symbol'})
        portfolio_current_prices_df['dt'] = datetime.now().strftime('%Y-%m-%d')
        portfolio_current_prices_df = pd.merge(portfolio_current_prices_df, holdings_df[['kite_quotes_symbol', 'investment_option_id', 'ticker']], how='left',
                                               on='kite_quotes_symbol')
        portfolio_history = pd.concat([portfolio_history, portfolio_current_prices_df], ignore_index=True)
        portfolio_history = portfolio_history.drop_duplicates(['investment_option_id', 'dt'], keep='last')
        portfolio_history = pd.merge(portfolio_history, holdings_df[['investment_option_id', 'quantity', 'average_price']], how='left', on='investment_option_id')
        # df = pd.merge(portfolio_history, holdings_df, how='inner', on='ticker')
        portfolio_history['dt'] = portfolio_history['dt'].astype('datetime64[ns]')
        portfolio_history['price'] = portfolio_history['price'].astype('float')
        portfolio_history['value'] = portfolio_history['price'] * portfolio_history['quantity']
        return portfolio_history

    @staticmethod
    def filter_portfolio_by_names_list(companies_list, portfolio_df):
        companies_df_list = []
        for company in companies_list:
            cur_df = PortfolioService.filter_portfolio_by_name(company_name=company, portfolio_df=portfolio_df)
            companies_df_list.append(cur_df)
        df = pd.concat(companies_df_list)
        unique_tickers = list(set(list(df['ticker'])))
        return portfolio_df[portfolio_df['ticker'].isin(unique_tickers)]

    @staticmethod
    def filter_all_companies_by_name(companies_list):
        all_nse_symbols = PortfolioSQL.get_all_nse_symbols()
        all_nse_symbols = all_nse_symbols.drop_duplicates('name')
        companies_df_list = []
        for company in companies_list:
            cur_company_df = PortfolioService.filter_portfolio_by_name(company_name=company, portfolio_df=all_nse_symbols)
            cur_company_df['user_query'] = company
            companies_df_list.append(cur_company_df)
        companies_df = pd.concat(companies_df_list)
        companies_df = pd.merge(companies_df, all_nse_symbols[['investment_option_id', 'ticker', 'kite_quotes_symbol', 'name']], how='left', on='ticker')
        return companies_df

    @staticmethod
    def get_latest_prices_from_sql(company_kite_symbols):
        kite_to_investment_id_mapping = PortfolioSQL.get_investment_option_id_for_kite_symbol(company_kite_symbols)
        investment_id_to_kite_mapping = {v: k for k, v in kite_to_investment_id_mapping.items()}
        latest_id_prices = PortfolioSQL.get_latest_prices_for_instrument_ids(investment_id_list=list(kite_to_investment_id_mapping.values()))
        return {investment_id_to_kite_mapping[i]: price for i, price in latest_id_prices.items()}

    @staticmethod
    def get_latest_share_price_trend_for_companies(companies_list, num_days=180):
        # Getting current price
        try:
            companies_df = PortfolioService.filter_all_companies_by_name(companies_list=companies_list)
            # investment_option_ids = list(set(companies_df['investment_option_id']))
            company_kite_symbols = list(set(companies_df['kite_quotes_symbol']))
            if not company_kite_symbols:
                company_kite_symbols = ['NSE:NIFTY 50']
            latest_prices = PortfolioService.get_latest_prices_from_sql(company_kite_symbols=company_kite_symbols)
            companies_df['price'] = companies_df['kite_quotes_symbol'].apply(lambda x: latest_prices.get(x, None))
            companies_df = companies_df[companies_df.price.notnull()]
            # Keeping one company per keyword based on max share price
            companies_df = companies_df.sort_values(['user_query', 'matching_score', 'price'], ascending=[True, False, False])
            companies_df = companies_df.drop_duplicates(subset='user_query', keep='first')[['investment_option_id', 'ticker', 'name', 'price']]
            companies_df['dt'] = datetime.now().strftime('%Y-%m-%d')
            # Getting history
            investment_ids = list(set(companies_df['investment_option_id']))
            if num_days >= 3:
                portfolio_history = PortfolioSQL.get_investment_option_price_long_history(investment_id_list=investment_ids, num_days=num_days)
            else:
                # TODO: - update the function
                portfolio_history = PortfolioSQL.get_investment_option_price_long_history(investment_id_list=investment_ids, num_days=num_days)
            portfolio_history = pd.merge(portfolio_history, companies_df[['investment_option_id', 'ticker', 'name']], how='left', on='investment_option_id')
            portfolio_history = pd.concat([portfolio_history, companies_df])
            portfolio_history = portfolio_history.drop_duplicates(['investment_option_id', 'dt'], keep='last')
            df_sorted = portfolio_history.sort_values(by=['investment_option_id', 'dt'])
            companies_starting_price = df_sorted.drop_duplicates(subset='investment_option_id', keep='first')
            # companies_starting_price = portfolio_history.loc[portfolio_history.groupby('investment_option_id')['dt'].idxmin()].rename(columns={'price': 'starting_price'})
            companies_starting_price = companies_starting_price[['investment_option_id', 'price']].rename(columns={'price': 'starting_price'})

            portfolio_history = pd.merge(portfolio_history, companies_starting_price, how='left', on='investment_option_id')
            portfolio_history['movement'] = (portfolio_history['price'] - portfolio_history['starting_price'])/portfolio_history['starting_price']
            filtered_companies = set(companies_df['ticker'])
            if len(filtered_companies) > 1:
                line_chart_variable = 'movement'
                line_chart_value_type = 'percent'
            else:
                line_chart_variable = 'price'
                line_chart_value_type = 'rupees'

            # return portfolio_history
            response = []
            if len(filtered_companies) == 1:
                latest_stats = [{'value': round(x['price'], 4) for i, x in companies_df.iterrows()}]
                latest_plot = {'text_box': {'value_type': 'rupees', 'chart_title': f'Latest share price of {list(latest_stats[0].keys())[0].capitalize()}',
                                            'data': latest_stats}}
                response.append(latest_plot)
            historic_stats = []
            for company_ticker in set(portfolio_history['ticker']):
                cur_company_history_df = portfolio_history[portfolio_history['ticker'] == company_ticker]
                cur_company_stats = {x['dt']: round(x[line_chart_variable], 4) for i, x in cur_company_history_df.iterrows()}
                historic_stats.append({company_ticker: cur_company_stats})
            historic_plot = {'line_chart': {'value_type': line_chart_value_type, 'chart_title': f'Share price history of {", ".join(companies_list)}',
                                            'data': historic_stats}}
            response.append(historic_plot)
            return response
        except Exception as e:
            print(e)
            logger.info(f'expected {e}')

    # @staticmethod
    # def calculate_companies_growth_rate(companies_list, num_days=180):
    #     history_df = PortfolioService.get_latest_share_price_trend_for_companies(companies_list=companies_list, num_days=num_days)
    #     growth_df = history_df.groupby('nse_ticker').apply(lambda x: pd.Series({
    #         'min_date_price': x.loc[x['dt'].idxmin(), 'close'],
    #         'max_date_price': x.loc[x['dt'].idxmax(), 'close']
    #     })).reset_index()
    #     growth_df['growth'] = np.round((growth_df['max_date_price'] - growth_df['min_date_price'])/growth_df['min_date_price'], 4)
    #     return growth_df
    @staticmethod
    def calc_growth_rate_for_instrument_option_ids(instrument_option_ids, num_days=180):
        portfolio_history = PortfolioSQL.get_investment_option_price_long_history(investment_id_list=instrument_option_ids, num_days=num_days)
        growth_df = portfolio_history.groupby('investment_option_id').apply(lambda x: pd.Series({
            'min_date_price': x.loc[x['dt'].idxmin(), 'price'],
            'max_date_price': x.loc[x['dt'].idxmax(), 'price']
        })).reset_index()
        growth_df['growth'] = np.round((growth_df['max_date_price'] - growth_df['min_date_price']) / growth_df['min_date_price'], 4)
        return growth_df

    @staticmethod
    def get_kite_access_token():
        # Create a client
        ssm = boto3.client('ssm', region_name='ap-south-1')

        # Specify the name of the parameter you want to get
        parameter_name = 'kite-tokens'

        # Get the parameter
        parameter = ssm.get_parameter(Name=parameter_name, WithDecryption=True)

        # The parameter value is stored in the 'Parameter' key, then 'Value'
        value = parameter['Parameter']['Value']
        return json.loads(value)['accessToken']
        # secret_name = "ArticleDbMasterCreds"
        # region_name = "ap-south-1"
        #
        # session = boto3.session.Session()
        # client = session.client(
        #     service_name='secretsmanager',
        #     region_name=region_name,
        # )
        # try:
        #     get_secret_value_response = client.get_secret_value(
        #         SecretId=secret_name
        #     )
        # except Exception as e:
        #     raise e
        # else:
        #     # Decrypts secret using the associated KMS CMK.
        #     # Depending on whether the secret is a string or binary, one of these fields will be populated.
        #     if 'SecretString' in get_secret_value_response:
        #         secret = get_secret_value_response['SecretString']
        #     else:
        #         secret = base64.b64decode(get_secret_value_response['SecretBinary'])
        #
        #     return json.loads(secret)  # returns the secret as dictionary

    @staticmethod
    def calculate_annualized_growth_rate(growth_rate, days):
        """
        Calculate the annualized growth rate from a given growth rate over a certain number of days.

        :param growth_rate: The growth rate over the period (e.g., 1.25 for 25% growth)
        :param days: The number of days over which the growth rate was observed
        :return: The annualized growth rate as a decimal (e.g., 0.25 for 25%)
        """
        if days == 0:
            raise ValueError("Number of days cannot be zero")
        # Convert growth rate to a rate of change (e.g., 1.25 to 0.25)
        rate_of_change = growth_rate
        # Calculate the annualized growth rate
        annualized_growth_rate = (1 + rate_of_change) ** (365 / days) - 1
        return annualized_growth_rate

    @staticmethod
    def calculate_day_wise_portfolio_performance(df):
        """
        Calculate the performance of the portfolio based on a DataFrame.

        :param df: DataFrame containing 'min_date_price', 'max_date_price', and 'quantity' for each stock
        :return: The performance of the portfolio as a percentage
        """
        # Calculate total value at minimum and maximum dates
        total_min_value = (df['min_date_price'] * df['quantity']).sum()
        total_max_value = (df['max_date_price'] * df['quantity']).sum()
        # Calculate the change in total value and performance percentage
        change_in_value = total_max_value - total_min_value
        performance = (change_in_value / total_min_value) * 100
        return performance

    @staticmethod
    def calculate_portfolio_performance(df):
        """
        Calculate the performance of the portfolio based on a DataFrame.

        :param df: DataFrame containing 'min_date_price', 'max_date_price', and 'quantity' for each stock
        :return: The performance of the portfolio as a percentage
        """
        # Calculate total value at minimum and maximum dates
        total_min_value = (df['min_date_price'] * df['quantity']).sum()
        total_max_value = (df['max_date_price'] * df['quantity']).sum()
        # Calculate the change in total value and performance percentage
        change_in_value = total_max_value - total_min_value
        performance = (change_in_value / total_min_value) * 100
        return performance

    @staticmethod
    def get_agg_growth_df_for_history(history_df, num_days):
        # history_df['dt'] = pd.to_datetime(history_df['dt'])
        # growth_df = history_df.groupby('investment_option_id').apply(lambda x: pd.Series({
        #     'min_date_price': x.loc[x['dt'].idxmin(), 'price'],
        #     'max_date_price': x.loc[x['dt'].idxmax(), 'price']
        # })).reset_index()
        # Assuming history_df is defined with columns: 'investment_option_id', 'dt', 'price'

        # Sort history_df by 'investment_option_id' and 'dt' (date)
        history_df_sorted = history_df.sort_values(by=['investment_option_id', 'dt'])

        # Group by 'investment_option_id' and extract the price for the min and max dates
        growth_df = history_df_sorted.groupby('investment_option_id').apply(lambda x: pd.Series({
            'min_date_price': x.iloc[0]['price'],  # First row in the sorted group
            'max_date_price': x.iloc[-1]['price']  # Last row in the sorted group
        })).reset_index()
        logger.info(f'agg growth group by is done as {growth_df.head(3)}')
        growth_df['growth'] = np.round((growth_df['max_date_price'] - growth_df['min_date_price']) / growth_df['min_date_price'], 4)
        growth_df['annualized_growth'] = growth_df['growth'].apply(
            lambda x: PortfolioService.calculate_annualized_growth_rate(growth_rate=x, days=num_days))
        # growth_df = pd.merge(growth_df, history_df[['investment_option_id', 'name', 'ticker']], how='left', on='investment_option_id')
        return growth_df

    @staticmethod
    def calc_growth_rate_for_user_portfolio_companies(user_id,
                                                      companies_list=None,
                                                      num_days=180,
                                                      aggregation_level=PortfolioAggLevel.COMPANY.value,
                                                      aggregation_metric=GrowthAggMetric.GROWTH.value,
                                                      sorting_order='descending'):
        user_portfolio_df = PortfolioSQL.get_user_current_holdings(user_id=user_id)
        logger.info(f'user portfolio is fetched as {user_portfolio_df}')
        user_portfolio_df = user_portfolio_df.drop_duplicates('ticker')
        if companies_list:
            user_portfolio_df = PortfolioService.filter_portfolio_by_names_list(companies_list=companies_list, portfolio_df=user_portfolio_df)
        instrument_option_ids = list(set(user_portfolio_df['investment_option_id']))
        portfolio_history = PortfolioSQL.get_investment_option_price_long_history(investment_id_list=instrument_option_ids, num_days=num_days)
        logger.info(f'portfolio history is fetched with {len(portfolio_history)} rows and {portfolio_history.columns} columns as {portfolio_history.head(10)}')
        portfolio_history = pd.merge(portfolio_history, user_portfolio_df, how='left', on='investment_option_id')
        logger.info(f'merging of history and user portfolio is done as {portfolio_history.head(10)}')
        portfolio_history['price'] = portfolio_history['price'].astype('float')
        portfolio_history['dt'] = portfolio_history['dt'].astype('str')
        portfolio_history['value'] = portfolio_history['price'] * portfolio_history['quantity']

        company_growth_df = PortfolioService.get_agg_growth_df_for_history(history_df=portfolio_history, num_days=num_days)
        logger.info(f'portfolio history is aggregated')
        company_growth_df = pd.merge(company_growth_df, user_portfolio_df, how='left', on='investment_option_id')
        # company_growth_df = pd.merge(company_growth_df, user_portfolio_df[['investment_option_id', 'ticker', 'name']], how='left', on='investment_option_id')

        # overall portfolio stats
        overall_portfolio_starting_value = (company_growth_df['quantity'] * company_growth_df['min_date_price']).sum()
        overall_portfolio_current_value = (company_growth_df['quantity'] * company_growth_df['max_date_price']).sum()
        overall_portfolio_growth = (overall_portfolio_current_value - overall_portfolio_starting_value) / overall_portfolio_starting_value
        logger.info(f'overall stats at portfolio are computed')
        # index performance
        index_investment_option = PortfolioSQL.get_instrument_token_for_nse_ticker('NIFTY 50')
        index_history = PortfolioSQL.get_investment_option_price_long_history([index_investment_option], num_days=num_days)
        index_growth_df = PortfolioService.get_agg_growth_df_for_history(history_df=index_history, num_days=num_days)
        index_growth = index_growth_df.iloc[0]['growth']
        # index_growth = 0
        overall_portfolio_growth_over_index = overall_portfolio_growth - index_growth

        # company_growth_df['index_growth'] = index_growth_df.iloc[0]['growth']
        # company_growth_df['annualized_index_growth'] = index_growth_df.iloc[0]['annualized_growth']
        company_growth_df['index_growth'] = index_growth
        company_growth_df['annualized_index_growth'] = index_growth
        company_growth_df['growth_over_index'] = company_growth_df['growth'] - company_growth_df['index_growth']
        company_growth_df['annualized_growth_over_index'] = company_growth_df['annualized_growth'] - company_growth_df['annualized_index_growth']
        logger.info(f'company level index stats are computed')
        # return company_growth_df
        most_profitable = sorting_order == 'ascending'
        company_growth_df = company_growth_df.sort_values('growth', ascending=most_profitable)
        agg_metrics = {GrowthAggMetric.GROWTH.value: overall_portfolio_growth, GrowthAggMetric.GROWTH_OVER_INDEX.value: overall_portfolio_growth_over_index}
        portfolio_stats = []
        value_type = 'percent'
        named_agg_metric = {'growth': 'Growth', 'growth_over_index': 'Growth Over Index'}
        if aggregation_level == PortfolioAggLevel.OVERALL.value:
            overall_stats = {'text_box': {'data': [{'value': agg_metrics.get(aggregation_metric, None)}], 'value_type': value_type,
                                          'chart_title': named_agg_metric[aggregation_metric]}}
            portfolio_stats.append(overall_stats)
        company_level_stats = [{x['name']: round(x[aggregation_metric], 4)} for i, x in company_growth_df.iterrows()]
        logger.info(f'company level stats computed')
        company_level_stats_dict = {
            'bar_chart': {'value_type': value_type, 'chart_title': f'Top Holdings by {named_agg_metric[aggregation_metric]}', 'data': company_level_stats}}
        # sorted_portfolio_details = user_portfolio_df.sort_values(by=aggregation_metric, ascending=ascending)
        portfolio_stats.append(company_level_stats_dict)
        logger.info(f'returning response')
        # index_growth_df =

        return portfolio_stats

    @staticmethod
    def get_portfolio_performance_over_period(user_id,
                                              aggregation_level=PortfolioAggLevel.OVERALL.value,
                                              compare_against_index=False,
                                              companies_list=None,
                                              sorting_order='descending',
                                              num_days=180):
        day_wise_portfolio_performance = PortfolioService.get_price_history_user_holdings(user_id=user_id, num_days=num_days)
        if companies_list:
            day_wise_portfolio_performance = PortfolioService.filter_portfolio_by_names_list(companies_list=companies_list, portfolio_df=day_wise_portfolio_performance)
        company_overall_growth_df = day_wise_portfolio_performance.groupby('ticker').apply(lambda x:
                                                                                           pd.Series({'min_date_price': x.loc[x['dt'].idxmin(), 'price'],
                                                                                                      'max_date_price': x.loc[x['dt'].idxmax(), 'price'],
                                                                                                      'starting_value': x.loc[x['dt'].idxmin(), 'value'],
                                                                                                      'current_value': x.loc[x['dt'].idxmax(), 'value']})).reset_index()
        company_overall_growth_df['growth'] = np.round(
            (company_overall_growth_df['max_date_price'] - company_overall_growth_df['min_date_price']) / company_overall_growth_df['min_date_price'], 4)
        portfolio_day_growth_df = day_wise_portfolio_performance.groupby('dt')['value'].sum()
        # return portfolio_day_growth_df
        most_profitable = sorting_order == 'ascending'
        if aggregation_level == PortfolioAggLevel.COMPANY.value:
            company_overall_growth_df = company_overall_growth_df.sort_values('growth', ascending=most_profitable)
        else:
            overall_portfolio_starting_value = company_overall_growth_df['starting_value'].sum()
            overall_portfolio_current_value = company_overall_growth_df['current_value'].sum()
            overall_portfolio_growth = (overall_portfolio_current_value - overall_portfolio_starting_value) / overall_portfolio_starting_value
        if compare_against_index:
            index_investment_option = PortfolioSQL.get_instrument_token_for_nse_ticker('NIFTY 50')
            day_wise_index_performance = PortfolioSQL.get_investment_option_price_history([index_investment_option], num_days=180)
            index_starting_value = day_wise_index_performance.loc[day_wise_index_performance['dt'].idxmin(), 'price']
            index_current_value = day_wise_index_performance.loc[day_wise_index_performance['dt'].idxmax(), 'price']
            overall_index_growth = (index_current_value - index_starting_value) / index_starting_value
        # df = pd.merge(agg_growth_df, holdings_df, how='inner', on='nse_ticker')

        # agg_growth_df['starting_value'] = agg_growth_df['min_date_price'] * agg_growth_df['quantity']
        # agg_growth_df['current_value'] = agg_growth_df['max_date_price'] * agg_growth_df['quantity']
        return company_overall_growth_df

    @staticmethod
    def get_current_portfolio_value(user_id,
                                    aggregation_metric=PortfolioAggMetric.CURRENT_VALUE.value,
                                    aggregation_level=PortfolioAggLevel.OVERALL.value,
                                    companies_list=None,
                                    sorting_order='descending'):
        user_portfolio_df = PortfolioSQL.get_user_current_holdings(user_id=user_id)
        logger.info(f'user portfolio is {user_portfolio_df}')
        if companies_list:
            user_portfolio_df = PortfolioService.filter_portfolio_by_names_list(companies_list=companies_list, portfolio_df=user_portfolio_df)
            if user_portfolio_df.empty:
                return {}

        user_nse_tickers = list(user_portfolio_df['kite_quotes_symbol'])
        latest_prices = PortfolioService.get_latest_prices_from_sql(company_kite_symbols=user_nse_tickers)
        # latest_prices = PortfolioService.get_latest_prices_for_tickers(kite_quote_symbols=user_nse_tickers)
        logger.info(f'fetched latest prices for {user_nse_tickers}')
        user_portfolio_df = user_portfolio_df[user_portfolio_df['kite_quotes_symbol'].isin(list(latest_prices.keys()))]
        user_portfolio_df['current_price'] = user_portfolio_df['kite_quotes_symbol'].apply(lambda x: latest_prices[x])
        # user_portfolio_df['current_price'] = user_portfolio_df['average_price'].apply(lambda x: x * np.random.uniform(0.5,1.5))
        user_portfolio_df['current_value'] = user_portfolio_df['current_price'] * user_portfolio_df['quantity']
        user_portfolio_df['invested_value'] = user_portfolio_df['average_price'] * user_portfolio_df['quantity']
        user_portfolio_df['profit'] = user_portfolio_df['current_value'] - user_portfolio_df['invested_value']
        user_portfolio_df['profit_percent'] = (user_portfolio_df['current_value'] - user_portfolio_df['invested_value']) / (user_portfolio_df['invested_value'])

        # Aggregate metrics
        total_current_value = user_portfolio_df['current_value'].sum()
        total_invested_value = user_portfolio_df['invested_value'].sum()
        total_profit = user_portfolio_df['profit'].sum()
        total_profit_percent = (total_current_value - total_invested_value) / total_invested_value

        agg_metrics = {PortfolioAggMetric.CURRENT_VALUE.value: total_current_value,
                       PortfolioAggMetric.INVESTED_VALUE.value: total_invested_value,
                       PortfolioAggMetric.PROFIT.value: total_profit,
                       PortfolioAggMetric.PROFIT_PERCENT.value: total_profit_percent}
        ascending = sorting_order == 'ascending'
        portfolio_stats = []
        named_agg_metric = {'current_value': 'Current Value', 'invested_value': 'Invested Value', 'profit': 'Total Profit', 'profit_percent': 'Profit Percent'}
        formatted_results_df = PortfolioService.create_others_group(df=user_portfolio_df, column=aggregation_metric, n=9, ascending=ascending)
        formatted_results_df = formatted_results_df[['name', aggregation_metric]].rename(columns={'name': 'Name', aggregation_metric: named_agg_metric[aggregation_metric]})
        # return formatted_results_df
        if aggregation_metric == PortfolioAggMetric.PROFIT_PERCENT.value:
            value_type = 'percent'
        else:
            value_type = 'rupees'
        if aggregation_level == PortfolioAggLevel.OVERALL.value:
            overall_stats = {'text_box': {'data': [{'value': agg_metrics.get(aggregation_metric, None)}], 'value_type': value_type,
                                          'chart_title': named_agg_metric[aggregation_metric]}}
            portfolio_stats.append(overall_stats)
        # company_level_stats = formatted_results_df.to_dict('index')
        company_level_stats = [{x['Name']: round(x[named_agg_metric[aggregation_metric]], 4)} for i, x in formatted_results_df.iterrows()]
        company_level_stats_dict = {'bar_chart': {'value_type': value_type, 'chart_title': f'Top Holdings by {named_agg_metric[aggregation_metric]}', 'data': company_level_stats}}
        # sorted_portfolio_details = user_portfolio_df.sort_values(by=aggregation_metric, ascending=ascending)
        portfolio_stats.append(company_level_stats_dict)
        return portfolio_stats

    @staticmethod
    def create_others_group(df, column, n=9, ascending=False):
        result_df = df.sort_values(by=column, ascending=ascending)
        if len(result_df) > 9:
            top_n = result_df.head(n)
            others = result_df.iloc[n:].sum(numeric_only=True)
            others['name'] = 'others'
            result_df = pd.concat([top_n, pd.DataFrame([others])])
        return result_df
