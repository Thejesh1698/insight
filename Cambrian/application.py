import json
import logging
from flask import Flask, jsonify, current_app, request
from src.ArticleSelectionService import ArticleSelectionService
from typing import List
from constants import ContentType, SourceType
application = Flask(__name__)

logging.basicConfig(level=logging.INFO)  # or DEBUG, ERROR, etc.
logger = logging.getLogger(__name__)


# article_selection_service = ArticleSelectionService()

#
# # TODO: - evaluate using a routes type file
# @application.route('/create_embedding', methods=['POST'])
# def create_embedding():
#     data = request.get_json()
#
#     # Validate data
#     if not data or 'articleId' not in data:
#         return jsonify({'error': 'articleId not present in request json'}), 400
#
#     article_id = data['articleId']
#     article = ArticleService.get_Article(article_id=article_id)
#     embedding_service.create_article_embeddings(article_id=article.article_id, cleaned_article_content=article.full_content)
#     article_dict = article.to_dict()
#     message_body = json.dumps(article_dict)
#     response = sqs.send_message(QueueUrl=queue_url, MessageBody=message_body)
#     return f'embeddings created for articleId {article_id} and got response of {response}'
#
#
# @application.route('/assign_cluster', methods=['POST'])
# def assign_cluster():
#     data = request.get_json()
#
#     # Validate data
#     # TODO: - update the cluster assignment lambda to extract article_id instead of articleId
#     if not data or 'articleId' not in data:
#         return jsonify({'error': 'article_id not present in request json'}), 400
#
#     article_id = data['articleId']
#     if 'full_content' in data:
#         article_text = data['full_content']
#     else:
#         article = ArticleService.get_Article(article_id=article_id)
#         article_text = article.full_content
#     cluster_assignment_service.compute_save_cluster_id_for_article_id(article_id=article_id, article_text=article_text)
#     # TODO: - save the probability against storyline and cluster_id
#     add_as_candidate_article(articleId=article_id)
#     return f'cluster successfully assigned for articleId {article_id}'
#
#
# @application.route('/articles/<articleId>/add_as_candidate', methods=['POST'])
# def add_as_candidate_article():
#     data = request.get_json()
#
#     # Validate data
#     if not data or 'article_id' not in data:
#         return jsonify({'error': 'article_id not present in request json'}), 400
#
#     article_id = data['articleId']
#     try:
#         article = Article.from_dict(data)
#     except:
#         article = ArticleService.get_Article(article_id=article_id)
#
#     CandidateSQL.add_article_to_candidates(article_id=article_id, published_at=article.published_time, source_id=article.source_id)
#     return f'article {article_id} successfully inserted into candidate articles'
#
#
# @application.route('/update_candidates', methods=['POST'])
# def update_candidate_articles():
#     CandidateSelectionService.update_candidate_articles()
#     return 'candidates updated successfully'
#
#
# @application.route('/update_topic_preferences', methods=['POST'])
# def update_topic_preferences():
#     topic_cluster_mapping.recompute_preferences_for_all_topics()
#     return 'topic preferences updated successfully'
def is_valid_api_request_json(json_data: dict, expected_keys: List[str]) -> bool:
    if not expected_keys:
        return True
    else:
        for key in expected_keys:
            if key not in json_data:
                return False
        return True


# @application.route('/get_feed', methods=['POST'])
# def generate_feed():
#     data = request.get_json()
#     expected_keys = ['user_id', 'topic_ids', 'feed_article_count', 'seconds_since_last_api_call', 'current_feed_session_article_ids']
#     if not is_valid_api_request_json(json_data=data, expected_keys=expected_keys):
#         return jsonify({'error': f'not all of {",".join(expected_keys)} present in request json'}), 400
#
#     # Extract user_id, topic_ids, feed count and mins_since_last_api_call from the JSON request
#     user_id = data.get('user_id')
#     topic_ids = data.get('topic_ids')
#     feed_article_count = data.get('feed_article_count')
#     seconds_since_last_api = data.get('seconds_since_last_api_call')
#     cur_feed_article_ids = data.get('current_feed_session_article_ids')
#
#     cluster_preferences = cluster_selection_service.get_overall_user_preferences(user_id=user_id, topic_id_list=topic_ids)
#     cluster_allotment = cluster_selection_service.allot_articles_per_cluster(cluster_preferences=cluster_preferences,
#                                                                              feed_article_count=feed_article_count,
#                                                                              seconds_since_last_api=seconds_since_last_api)
#     # TODO: - this should work for new user, old user, empty topics, non existing topics: basically consider a host of values for all params
#     feed = article_selection_service.get_ordered_feed(user_id=user_id, articles_per_cluster=cluster_allotment, cur_feed_article_ids=cur_feed_article_ids,
#                                                       cluster_preferences=cluster_preferences)
#     return feed


@application.route('/get_feed', methods=['POST'])
def generate_feed():
    data = request.get_json()
    expected_keys = ['user_id', 'topic_ids', 'feed_article_count', 'seconds_since_last_api_call', 'current_feed_session_article_ids', 'page']
    if not is_valid_api_request_json(json_data=data, expected_keys=expected_keys):
        return jsonify({'error': f'not all of {",".join(expected_keys)} present in request json'}), 400

    if data.get('content_type') == ContentType.podcast_episode.value:
        content_type = ContentType.podcast_episode.value
    elif data.get('content_type') == SourceType.podcast.value:
        content_type = SourceType.podcast.value
    else:
        content_type = ContentType.article.value
    # Extract user_id, topic_ids, feed count and mins_since_last_api_call from the JSON request
    user_id = data.get('user_id')
    topic_ids = data.get('topic_ids')
    feed_article_count = data.get('feed_article_count')
    seconds_since_last_api = data.get('seconds_since_last_api_call')
    cur_feed_article_ids = data.get('current_feed_session_article_ids')
    page_number = data.get('page')
    logger.info(f'feed called for params of user_id, topic_ids, count, seconds, cur_article_ids, page of {(user_id, topic_ids, feed_article_count, seconds_since_last_api, cur_feed_article_ids, page_number)}')
    feed = ArticleSelectionService.get_feed(user_id=user_id, topic_ids=topic_ids, feed_article_count=feed_article_count,
                                            seconds_since_last_api_call=seconds_since_last_api, cur_feed_article_ids=cur_feed_article_ids, session_page=page_number,
                                            content_type=content_type)
    logger.info(f'returning response for feed for {user_id} and page of {page_number}')
    return feed


@application.route('/ping', methods=['GET'])
def ping():
    """Determine if the container is working and healthy."""
    # (Optional) You can insert logic here to check the health of your model or dependencies.
    return jsonify(status='ok'), 200


@application.route('/invocations', methods=['POST'])
def invocations():
    """Do an inference on the model."""
    # If you don't want to do anything and just return a dummy response:
    return jsonify(result='dummy_result'), 200


if __name__ == '__main__':
    application.debug = False
    # if len(sys.argv) > 1 and sys.argv[1] == 'serve':
    application.run(host="0.0.0.0", port=8080)
