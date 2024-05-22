import json
import os
import time
from datetime import datetime
import numpy as np
import pandas as pd
import umap
from _plotly_utils.utils import PlotlyJSONEncoder
import plotly.express as px
from constants import YT_SOURCE_ID
from sql.articles.MongoDBArticle import MongoDBArticle
from src.articles.ArticleService import ArticleService
from src.candidates._utils import is_candidate, get_prior_for_popularity
from src.candidates.CandidatesService import CandidatesService
import boto3
import logging
from flask import Flask, jsonify, request, Response
from concurrent.futures import ThreadPoolExecutor, as_completed
from sql.PostgresDatabaseOperation import PostgresDatabaseOperation
from sql._utils import remove_article_ids_from_ml_db
from sql.articles.ArticleAttributesSQL import ArticleAttributesSQL
from flask import Flask, jsonify, current_app, request, render_template, make_response, redirect, url_for
from src.articles.ArticleAttributesService import ArticleAttributesService
from sql.candidates.CandidateSQL import CandidateSQL
from src.clustering.ClustersResetService import ClustersResetService
from src.data_models.Article import Article
from src.embeddings.EmbeddingsService import EmbeddingsService  # Adjust the import based on the class name in the EmbeddingsService.py
from src.clustering.ClusterAssignmentService import ClusterAssignmentService
from src.topics.TopicClusterMapping import TopicClusterMapping
from sql.clustering.ClusteringSQL import ClusteringSQL
from hydra import compose, initialize
from huggingface_hub import login
from sql.MongoDatabaseConnection import MongoDatabaseConnection
from src._utils import get_embedding_model_name, load_bertopic_model_from_s3, load_bertopic_model_from_hf

application = Flask(__name__)
login(token=os.environ.get('HF_TOKEN'))
sqs = boto3.client('sqs', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY'), aws_secret_access_key=os.environ.get('AWS_SECRET_KEY'), region_name='ap-south-1')
# TODO: - move to conf
queue_url = 'https://sqs.ap-south-1.amazonaws.com/005418323977/post-article-embeddings-creation'
llm_finetune_id = 'OpenHermes_WatermelonSapphireZipline'
logging.basicConfig(level=logging.INFO)  # or DEBUG, ERROR, etc.
logger = logging.getLogger(__name__)

with initialize(config_path="./conf"):
    # Compose the configuration
    cfg = compose(config_name="TopicClusterMapping.yaml")
# TODO: - move the model name to env variable or conf

clustering_run_id = ClusteringSQL.get_latest_run_id()
print(f'fetched clustering run id {clustering_run_id}')
embedding_model_name = get_embedding_model_name(run_id=clustering_run_id)
print(f'embedding model name fetched {embedding_model_name}')
if os.environ.get('BERTOPIC_MODEL_TYPE') == 'full':
    bertopic_model = load_bertopic_model_from_s3(run_id=clustering_run_id, hf_embedding_model_name=embedding_model_name)
else:
    bertopic_model = load_bertopic_model_from_hf(run_id=clustering_run_id)
print('bertopic model loaded')
embedding_service = EmbeddingsService(hf_model_path='BAAI/bge-large-en-v1.5')
print('embedding service instantiated loaded')

cluster_assignment_service = ClusterAssignmentService(clustering_run_id=clustering_run_id, bertopic_model=bertopic_model)
print('cluster assignment service loaded')
topic_cluster_mapping = TopicClusterMapping(clustering_run_id=clustering_run_id, bertopic_model=bertopic_model, cfg=cfg)
print('topic cluster mapping service loaded')
attributes_service = ArticleAttributesService()
print('attributes service loaded')


# TODO: - evaluate using a routes type file
@application.route('/create_embedding', methods=['POST'])
def create_embedding():
    data = request.get_json()
    # Validate data
    if not data or 'articleId' not in data:
        return jsonify({'error': 'articleId not present in request json'}), 400

    article_id = data['articleId']
    logger.info(f'embeddings creation called for {article_id}')
    article = ArticleService.get_Article(article_id=article_id)
    logger.info(f'embeddings creation: article fetched for {article_id}')
    embedding_service.create_article_embeddings(article=article)
    article_dict = article.to_dict()
    article_dict['articleId'] = article_dict['article_id']
    message_body = json.dumps(article_dict)
    response = sqs.send_message(QueueUrl=queue_url, MessageBody=message_body)
    return f'embeddings created for articleId {article_id} and got response of {response}'


@application.route('/create_embedding_for_text', methods=['POST'])
def create_embedding_for_text():
    data = request.get_json()

    # Validate data
    if not data or 'query_text' not in data:
        return jsonify({'error': 'query_text not present in request json'}), 400
    query_text = data['query_text']
    emb = embedding_service.extract_embeddings_for_text(content=query_text)
    return emb


@application.route('/get_article_attributes_from_llm', methods=['POST'])
def get_article_attributes_from_llm():
    data = request.get_json()
    if not data or 'articleId' not in data:
        return jsonify({'error': 'articleId not present in request json'}), 400
    article_id = data['articleId']
    assert isinstance(article_id, str), f"{article_id} is not a string"
    # article_id_list = data['articleIds'].split(',')
    article_attributes = attributes_service.compute_save_article_attributes_from_llm(article_id=article_id)
    return json.dumps(article_attributes)


@application.route('/get_recent_published_document_ids', methods=['POST'])
def get_recent_published_document_ids():
    data = request.get_json()
    num_days = data.get('num_days', 7)
    all_article_ids = MongoDBArticle.fetch_recent_published_document_ids(days=num_days)
    return jsonify({'articleIds': all_article_ids})


@application.route('/get_all_missing_article_attributes_from_llm', methods=['POST'])
def get_all_missing_article_attributes_from_llm():
    all_article_ids = MongoDBArticle.fetch_all_document_ids()
    with PostgresDatabaseOperation() as cursor:
        sql = 'SELECT DISTINCT article_id FROM llm_article_attributes'
        cursor.execute(sql)
        results = cursor.fetchall()
        db_saved_results = [x[0] for x in results]
    pending_articles = list(set(all_article_ids) - set(db_saved_results))
    print(f'{len(pending_articles)} pending articles found')
    chunk_size = 100
    num_chunks = (len(pending_articles) // chunk_size) + 1
    for i in range(num_chunks):
        cur_article_ids = pending_articles[i * chunk_size: (i + 1) * chunk_size]
        start_time = time.time()
        completed = 0
        with ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(attributes_service.compute_save_article_attributes_from_llm, art_id) for art_id in cur_article_ids]
            for future in as_completed(futures):
                if future.result():
                    response = future.result()
                    if response:
                        try:
                            completed += 1
                        except:
                            pass
        num_pending = len(pending_articles) - i * chunk_size
        print(f'Processed chunk {i} in {time.time() - start_time} seconds at {datetime.now()}. {num_pending} articles pending')
    return 'llm attributes for pending articles now recomputed'


@application.route('/delete_article_ids_from_ml_db', methods=['POST'])
def delete_article_ids_from_ml_db():
    data = request.get_json()
    if not data or 'articleIds' not in data:
        return jsonify({'error': 'articleIds not present in request json'}), 400
    article_id_list = data['articleIds'].split(',')
    assert len(article_id_list) <= 1000, f'limit for article deletion is 1000. {len(article_id_list)} sent'
    remove_article_ids_from_ml_db(article_ids=article_id_list)
    return f'{len(article_id_list)} articles are removed from the db'


@application.route('/update_candidates', methods=['POST'])
def update_candidates():
    CandidatesService.update_candidate_articles()
    return 'candidates updated'


@application.route('/assign_cluster', methods=['POST'])
def assign_cluster():
    data = request.get_json()

    # Validate data
    if not data or 'articleId' not in data:
        return jsonify({'error': 'article_id not present in request json'}), 400

    article_id = data['articleId']
    article = ArticleService.get_Article(article_id=article_id)
    article_text = article.full_content
    cluster_assignment_service.compute_save_cluster_id_for_article_id(article_id=article_id, article_text=article_text, article=article)
    evaluate_save_article_to_candidates(article=article)
    return f'cluster successfully assigned for articleId {article_id}'


def evaluate_save_article_to_candidates(article: Article):
    article_id = article.article_id
    article_attributes = ArticleAttributesSQL.get_attributes_for_article_id(article_id=article_id)

    published_time = pd.to_datetime(article.published_time).replace(tzinfo=None)
    hours_since_publication = (datetime.today() - published_time) / np.timedelta64(1, 'h')
    article_attributes['hours_since_publication'] = hours_since_publication
    keep = False
    prior_a = 1
    prior_b = 10
    if article_attributes:
        keep = is_candidate(article_attributes)
        if 'expected_popularity' in article_attributes:
            prior_a = get_prior_for_popularity(article_attributes)
    if article.source_id == YT_SOURCE_ID:
        keep = False
    if keep:
        CandidateSQL.add_article_to_candidates_with_priors(article_id=article.article_id, published_at=article.published_time, source_id=article.source_id,
                                                           prior_a=prior_a, prior_b=prior_b, content_type=article.content_type)
        logger.info(f'article_id {article_id} is added to candidates with prior_a of {prior_a}')
    else:
        logger.info(f'article_id {article_id} is not added to candidates')
    return


@application.route('/get_missing_candidate_summaries', methods=['POST'])
def get_missing_candidate_summaries():
    def has_summary(metadata):
        if 'ai_generated_info' not in metadata:
            return False
        if 'summary' not in metadata['ai_generated_info']:
            return False
        all_models = list(metadata['ai_generated_info']['summary'].keys())
        if len(all_models) == 0:
            return False
        first_model = all_models[0]
        if 'value' not in metadata['ai_generated_info']['summary'][first_model]:
            return False
        return True

    candidate_article_ids = CandidateSQL.get_all_candidate_article_ids()
    candidate_articles_metadata = MongoDBArticle.fetch_documents_by_ids(string_ids=candidate_article_ids)
    logger.info(f'sample first article is {candidate_articles_metadata[0]}')
    missing_summary_candidates = []
    for article_metadata in candidate_articles_metadata:
        if has_summary(metadata=article_metadata):
            continue
        else:
            article_id = str(article_metadata['_id'])
            missing_summary_candidates.append(article_id)

    if len(missing_summary_candidates) == 0:
        return 'all candidates have summary'

    logger.info(f'{len(missing_summary_candidates)} candidates found without summary')
    chunk_size = 20
    num_chunks = (len(missing_summary_candidates) // chunk_size) + 1
    for i in range(num_chunks):
        cur_article_ids = missing_summary_candidates[i * chunk_size: (i + 1) * chunk_size]
        start_time = time.time()
        completed = 0
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(attributes_service.compute_save_article_attributes_from_llm, art_id) for art_id in cur_article_ids]
            for future in as_completed(futures):
                if future.result():
                    response = future.result()
                    if response:
                        try:
                            completed += 1
                        except:
                            pass
        num_pending = len(missing_summary_candidates) - i * chunk_size
        logger.info(f'Processed chunk {i} in {time.time() - start_time} seconds at {datetime.now()}. {num_pending} articles pending')
    return 'missing summaries for candidates generated'


@application.route('/generate_new_clusters_to_s3', methods=['POST'])
def generate_new_clusters_to_s3():
    with initialize(config_path="./conf"):
        # Compose the configuration
        reset_cfg = compose(config_name="ClustersResetService.yaml")
    ClustersResetService(cfg=reset_cfg, random_state=86)
    return 'clusters successfully reset'


@application.route('/add_new_source', methods=['POST'])
def add_new_source():
    data = request.get_json()
    # Validate data
    if not data or 'sourceId' not in data or 'sourceName' not in data or 'publicationDateDecay' not in data:
        return jsonify({'error': f'sourceId or sourceName or  not publicationDateDecay present in request json'}), 400
    assert isinstance(data['publicationDateDecay'], float), f"publicationDateDecay value of {data['publicationDateDecay']} is not a float value"
    assert 0.7 <= data['publicationDateDecay'] <= 1.0, f"value of publicationDateDecay {data['publicationDateDecay']} is not between 0.7 to 1.0"
    source_id = data['sourceId']
    source_name = data['sourceName']
    publication_date_decay = data['publicationDateDecay']
    CandidateSQL.add_new_source_details(source_id=source_id, source_name=source_name, publication_date_decay=publication_date_decay)
    return f'sourceId added/updated successfully to ML db'
# TODO: - add one more api to update decay of a source_id


@application.route('/ping', methods=['GET'])
def ping():
    return jsonify(status='ok'), 200


@application.route('/invocations', methods=['POST'])
def invocations():
    return jsonify(status='ok'), 200


@application.route('/create_umap_plot', methods=['GET'])
def create_umap_plot():
    # Prepare embeddings
    with PostgresDatabaseOperation() as cursor:
        sql = 'SELECT article_id, embedding FROM embeddings'
        cursor.execute(sql)
        results = cursor.fetchall()
        embeddings_df = pd.DataFrame(results, columns=['article_id', 'embedding'])

    with PostgresDatabaseOperation() as cursor:
        sql = 'SELECT DISTINCT article_id, cluster_id, parent_name cluster_name FROM article_to_cluster_mapping acm LEFT JOIN cluster_hierarchy ch ON acm.cluster_id = ch.parent_id'
        cursor.execute(sql)
        results = cursor.fetchall()
        clusters_df = pd.DataFrame(results, columns=['article_id', 'cluster_id', 'cluster_name'])

    combined_df = pd.merge(embeddings_df, clusters_df, how='left', on='article_id')
    combined_df = combined_df.dropna()

    all_article_ids = list(embeddings_df.article_id.unique())
    metadata_dict = ArticleService.get_all_Articles_metadata()
    articles = [(k, metadata_dict[k]['title']) for k in metadata_dict.keys()]
    titles_df = pd.DataFrame(articles, columns=['article_id', 'article_title'])

    df = pd.merge(titles_df, combined_df, how='left', on='article_id')
    df = df.dropna()
    embeddings = pd.DataFrame(df['embedding'].tolist())

    # Perform UMAP dimensionality reduction
    reducer = umap.UMAP(n_components=3, random_state=86)
    embedding_3d = reducer.fit_transform(embeddings)

    # Prepare data for plotting
    plot_df = pd.DataFrame(embedding_3d, columns=['x', 'y', 'z'])
    plot_df['article_title'] = df['article_title']
    plot_df['cluster_name'] = df['cluster_name']
    plot_df['cluster_id'] = df['cluster_id']

    # Create the Plotly visualization
    fig = px.scatter_3d(
        plot_df,
        x='x',
        y='y',
        z='z',
        color='cluster_id',
        hover_data=['article_title', 'cluster_name'],
        title='UMAP Projection of Article Embeddings',
        color_continuous_scale=px.colors.qualitative.Vivid,
        width=1600,  # Adjusting dimensions for a more square-like appearance
        height=800
    )

    fig.update_traces(marker=dict(size=5, opacity=0.8, line=dict(width=0.5, color='DarkSlateGrey')),
                      selector=dict(mode='markers'))

    # You might want to adjust layout for a better view
    fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))

    fig.update_layout(scene=dict(xaxis=dict(showgrid=False, showticklabels=False, showspikes = False),
                                 yaxis=dict(showgrid=False, showticklabels=False, showspikes = False),
                                 zaxis=dict(showgrid=False, showticklabels=False, showspikes = False)
                                 ))

    graph_json = json.dumps(fig, cls=PlotlyJSONEncoder)
    return jsonify({'graph': graph_json})  # return JSON response

    # return pio.to_html(fig, full_html=False)

# Sample dataframe for demonstration
df = pd.DataFrame({
    'title': ['Article1', 'Article2', 'Article3'],
    'content': ['Content1', 'Content2', 'Content3'],
    'source': ['Source1', 'Source2', 'Source3'],
    'url': ['http://example1.com', 'http://example2.com', 'http://example3.com'],
    'article_id': [101, 102, 103],
    'clean': [True, False, True]  # Sample column indicating if article is clean
})


# @application.route('/chitragupta/', methods=['GET', 'POST'])
# def article_qc_tool():
#     with PostgresDatabaseOperation() as cursor:
#         sql = 'SELECT DISTINCT article_id FROM article_qc_table'
#         cursor.execute(sql)
#         results = cursor.fetchall()
#         qc_articles = [item[0] for item in results]
#
#     with PostgresDatabaseOperation() as cursor:
#         sql = """SELECT source_name, COUNT(is_cleaned_completely) total, SUM(CAST(is_cleaned_completely AS INT)) clean
#         FROM article_qc_table
#         GROUP BY source_name
#         """
#         cursor.execute(sql)
#         results = cursor.fetchall()
#         source_count_df = pd.DataFrame(results, columns = ['source_name', 'total', 'clean'])
#
#     new_article_id = np.random.choice(list(set(all_articles) - set(qc_articles)))
#     s3_text = __get_article_text_from_s3(article_id=new_article_id)
#     metadata = get_article_metadata_from_api(article_id=new_article_id)
#     article = {'title': metadata['title'],
#                'source_id': metadata['source']['sourceId'],
#                'source_name': metadata['source']['sourceName'],
#                'content': s3_text['cleaned_text'],
#                'article_id': metadata['articleId'],
#                'url': metadata['url']}
#
#     source = request.args.get('source', 'Random')
#     # if source and source != 'Random':
#     #     sample_df = df[df['source'] == source].sample(n=1)
#     # else:
#     #     sample_df = df.sample(n=1)
#     #
#     # username = request.cookies.get('username', None)
#
#     # Gather statistics for chart
#     source_counts = source_count_df[['source_name', 'total']].set_index('source_name').to_dict()['total']
#     clean_counts = source_count_df[['source_name', 'clean']].set_index('source_name').to_dict()['clean']
#     not_clean_counts = {src: source_counts[src] - clean_counts.get(src, 0) for src in source_counts}
#
#     stats = {
#         'source_counts': source_counts,
#         'clean_counts': clean_counts,
#         'not_clean_counts': not_clean_counts
#     }
#
#     return render_template('chitragupta.html', article=article, username='', user_list='', source=source, stats=stats)

@application.route('/submit_next_qc_article', methods=['POST'])
def submit_next_qc_article():
    selected_source = request.form['sourceSelect']
    selected_user = request.form.get('userSelect')  # Use get to avoid KeyError
    redirect_url = url_for('article_qc_tool', source=selected_source)  # Here, 'source' is passed as a query parameter
    resp = make_response(redirect(redirect_url))

    # Capture user's input for relevance, cleanliness, and the article details
    is_relevant = request.form.get('relevance')
    is_cleaned = request.form.get('cleaned')
    article_id = request.form.get('article_id')
    source_id = request.form.get('source_id')
    source_name = request.form.get('source_name')

    with PostgresDatabaseOperation() as cursor:
        sql = """INSERT INTO article_qc_table (article_id, is_relevant, is_cleaned_completely, comments, source_id, source_name)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (article_id)
        DO UPDATE SET
        is_relevant = EXCLUDED.is_relevant,
        is_cleaned_completely = EXCLUDED.is_cleaned_completely,
        comments = EXCLUDED.comments
        """
        cursor.execute(sql, (article_id, is_relevant, is_cleaned, '', source_id, source_name))

    # resp.set_cookie('username', request.form['userSelect'], max_age=60*60*24*7)  # This cookie lasts for a week
    # if selected_user:
        # resp.set_cookie('username', selected_user, max_age=60*60*24*7)  # This cookie lasts for a week
    return resp


@application.route('/cluster_voyager')
def cluster_voyager():
    return render_template('index.html')  # render the HTML page


@application.route('/visualize_clusters')
def visualize_clusters():
    plot_html = create_umap_plot()
    return render_template('plot.html', plot_html=plot_html)


if __name__ == '__main__':
    application.debug = False
    application.run(host="0.0.0.0", port=8000)
