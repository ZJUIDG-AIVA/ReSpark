import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json

def calculate_cosine_similarity(vector1, vector2):
    vector1 = np.array(vector1).reshape(1, -1)
    vector2 = np.array(vector2).reshape(1, -1)
    similarity = cosine_similarity(vector1, vector2)
    return similarity[0][0]

def get_recommend(cache_path="test_cache", use_cache=True, update_cache=True):
    with open('data/database/reports/reports_information.json', 'r', encoding='utf-8') as file:
        reports_inform = json.load(file)
    with open('data/cache/selected/dataset/selected_dataset.json', 'r', encoding='utf-8') as file:
        dataset_inform = json.load(file)
    dataset_embedding_semantics = dataset_inform['embedding_semantics']
    dataset_embedding_data = dataset_inform['embedding_data']

    for report in reports_inform:
        report_embedding_semantics = report['embedding_semantics']
        report_embedding_data = report['embedding_data']
        score_semantics = calculate_cosine_similarity(report_embedding_semantics, dataset_embedding_semantics)
        score_data = calculate_cosine_similarity(dataset_embedding_data, report_embedding_data)
        report['score'] = (score_semantics + score_data) / 2
        del report['embedding_data']
        del report['embedding_semantics']
    sorted_reports = sorted(reports_inform, key=lambda x: x['score'], reverse=True)
    return sorted_reports