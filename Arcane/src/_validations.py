import numpy as np


def _validate_stories(stories):
    # stories should be either from 0 to len(stories) - 1 or should start from -1 to len(stories) - 2
    outlier_expected_topics = set(range(-1, len(stories) - 1))
    non_outlier_expected_topics = set(range(0, len(stories)))
    sorted_stories = set(sorted(stories))
    assert sorted_stories in [outlier_expected_topics, non_outlier_expected_topics], f"topics keys are not as the expected values"
    # ensure that all the topics of the bertopic model have a corresponding cluster mapped


def _validate_story_cluster_map(stories: list, story_cluster_map: dict):
    for story in stories:
        if story == -1:
            continue
        assert story in story_cluster_map, f"topic {story} is present in the bertopic model but does not have a cluster mapping in topic_to_cluster dictionary"


def _validate_embedding_and_model(embedding, expected_emb_size, actual_emb_model, expected_emb_model):
    validate_embedding(embedding=embedding)
    assert actual_emb_model == expected_emb_model, f"article embeddings are generated with {actual_emb_model} and not with expected {expected_emb_model}"
    assert len(embedding) == expected_emb_size, f"article embeddings of size {len(embedding)} not same as expected embedding size of {expected_emb_size}"


def validate_embedding(embedding):
    # Check if input is a list
    assert embedding is not None, f"embedding is empty"
    if not isinstance(embedding, (list, np.ndarray)):
        raise ValueError("Input should be a list or ndarray")

    # Check if all elements in the list are floats
    if not all(isinstance(x, (float, np.float32, np.float64, np.float16)) for x in embedding):
        raise ValueError("All elements in the list should be of type float")
