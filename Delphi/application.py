import json
import numpy as np
import boto3
import pandas as pd
import umap
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
from src.ArticleService import ArticleService
from flask import Flask, jsonify, current_app, request, render_template, make_response, redirect, url_for
from sql.SQLQueries import get_article_ids_with_embeddings
from sql.PostgresDatabaseOperation import PostgresDatabaseOperation

application = Flask(__name__)

all_articles = get_article_ids_with_embeddings()


@application.route('/create_umap_plot', methods=['GET'])
def create_umap_plot():
    print('create umap function entered')
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
    all_article_dict = ArticleService.parallel_get_Articles(all_article_ids)
    articles = [(all_article_dict[article_id].article_id, all_article_dict[article_id].title) for article_id in all_article_dict.keys()]
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


@application.route('/cluster_voyager/', methods=['GET', 'POST'])
def cluster_voyager():
    return render_template('index.html')  # render the HTML page


@application.route('/visualize_clusters')
def visualize_clusters():
    print('something happened')
    plot_html = create_umap_plot()
    return render_template('plot.html', plot_html=plot_html)



@application.route('/chitragupta/', methods=['GET', 'POST'])
def article_qc_tool():
    with PostgresDatabaseOperation() as cursor:
        sql = 'SELECT DISTINCT article_id FROM article_qc_table'
        cursor.execute(sql)
        results = cursor.fetchall()
        qc_articles = [item[0] for item in results]

    with PostgresDatabaseOperation() as cursor:
        sql = """SELECT source_name, COUNT(is_cleaned_completely) total, SUM(CAST(is_cleaned_completely AS INT)) clean 
        FROM article_qc_table
        GROUP BY source_name
        """
        cursor.execute(sql)
        results = cursor.fetchall()
        source_count_df = pd.DataFrame(results, columns = ['source_name', 'total', 'clean'])

    new_article_id = np.random.choice(list(set(all_articles) - set(qc_articles)))
    print(f'new article_id is {new_article_id}')
    article = ArticleService.get_Article(article_id=new_article_id)
    s3_text = article.cleaned_text
    article = {'title': article.title,
               'source_id': article.source_id,
               'source_name': article.source_name,
               'content': article.cleaned_text,
               'article_id': article.article_id,
               'url': article.url}

    source = request.args.get('source', 'Random')

    # Gather statistics for chart
    source_counts = source_count_df[['source_name', 'total']].set_index('source_name').to_dict()['total']
    clean_counts = source_count_df[['source_name', 'clean']].set_index('source_name').to_dict()['clean']
    not_clean_counts = {src: source_counts[src] - clean_counts.get(src, 0) for src in source_counts}

    stats = {
        'source_counts': source_counts,
        'clean_counts': clean_counts,
        'not_clean_counts': not_clean_counts
    }

    return render_template('chitragupta.html', article=article, username='', user_list='', source=source, stats=stats)


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

    return resp


if __name__ == '__main__':
    application.debug = False
    application.run(host="0.0.0.0", port=8000)
