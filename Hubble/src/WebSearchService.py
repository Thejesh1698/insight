from gnews import GNews
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
logger = logging.getLogger('__name__')


google_news = GNews(language='en', country='IN',max_results=3)


class WebSearchService:

    @staticmethod
    def get_top_gnews_results_for_query(query_text):
        start_time = time.time()
        news = google_news.get_news(query_text)
        logger.info(f'took {time.time() - start_time} to get results from google news for {query_text}')
        thread_articles = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(google_news.get_full_article, news[i]['url']) for i in range(3)]
            for future in as_completed(futures):
                if future.result():
                    response = future.result()
                    thread_articles.append(response)
        return thread_articles
