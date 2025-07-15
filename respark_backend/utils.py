import base64
import os
from io import StringIO
from mimetypes import guess_type
import time
import json

import openai
import pandas as pd
import zipfile
import shutil
import glob
from flask import jsonify
from openai.lib.azure import AzureOpenAI
from werkzeug.utils import secure_filename

from components.executor import executor
from components.adapter import adapter
from components.organizer import organizer
from components.inserter import inserter
from components.summarizer import summarizer
from components.spliter import spliter
from components.spliter.convert_md_to_json import convert
from components.recommender import recommender
from components.imitator import imitator

def local_image_to_data_url(image_path):
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = 'application/octet-stream' 
    with open(image_path, "rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{base64_encoded_data}"

def get_embedding(input):
    api_base = os.getenv("OPENAI_API_BASE")
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("OPENAI_API_EMBEDDING_NAME")
    client = openai.OpenAI(api_key=api_key, base_url=api_base)
    response = client.embeddings.create(
        input=input,
        model=model_name
    )
    return response.data[0].embedding

def delete_all_files(directory, file_type):
    files = glob.glob(os.path.join(directory, "*"+file_type))

    for file in files:
        try:
            os.remove(file)
        except Exception as e:
            print(f"error: {e}")

def get_database_func():
    with open('data/database/reports/reports_information.json', 'r', encoding='utf-8') as file:
        reports_inform = json.load(file)
    with open('data/database/datasets/datasets_information.json', 'r', encoding='utf-8') as file:
        datasets_inform = json.load(file)

    obj = {
        'datasets': datasets_inform,
        'reports': reports_inform
    }
    return json.dumps(obj, ensure_ascii=False)

def get_cache_list_func():
    with open('data/cache/cache_list.json', 'r', encoding='utf-8') as file:
        cache_list = json.load(file)
    return json.dumps(cache_list, ensure_ascii=False)

def create_cache_func(data):
    """
    input: data={
        'name':,
        'selected_dataset_id':,
        'selected_report_id':,
    }
    """
    folder_path = os.path.join('data/cache', data['name'])
    if not os.path.exists(folder_path):
        with open('data/cache/cache_list.json', 'r', encoding='utf-8') as f:
            cache_list = json.load(f)

        with open('data/database/datasets/datasets_information.json', 'r', encoding='utf-8') as file:
            datasets_inform = json.load(file)
        for dataset in datasets_inform:
            if int(dataset['id']) == int(data['selected_dataset_id']):
                dataset_obj = dataset
                break

        with open('data/database/reports/reports_information.json', 'r', encoding='utf-8') as file:
            reports_inform = json.load(file)
        for report in reports_inform:
            if int(report['id']) == int(data['selected_report_id']):
                report_obj = report
                break
        max_id = max(cache_list, key=lambda x: int(x["id"]))["id"]
        cache_obj = {
            'id': max_id+1,
            'name': data['name'],
            'dataset_name': dataset_obj['name'],
            'dataset_id': dataset_obj['id'],
            'report_name': report_obj['name'],
            'report_id': report_obj['id'],
        }
        cache_list.append(cache_obj)
        with open('data/cache/cache_list.json', 'w') as f:
            json.dump(cache_list, f, indent=4)

        os.makedirs(folder_path)
    else:
        return json.dumps({"error": "Cache already exists"})
    return '{"status": "success"}'

def recommend_report_func(data):
    """
    input:
    data = {
        ...
    }
    output:[{
        'id':
        'name':
        'size':
        'score':
        'predicted_fields':
        'topic':
        'folder_name':
    }]
    """
    recommend_result = recommender.get_recommend(cache_path=data["cache_path"], use_cache=data["use_cache"], update_cache=data["update_cache"])

    return json.dumps(recommend_result, ensure_ascii=False)

def get_report_content_func(data):
    """
    input: data={
        'selected_report_id':,
    }
    output:[
        {
            "type": "header",
            "level: 1,
            "content": ""
        },
        {
            "type": "header"/"paragraph"/"image",
            "content": ""
        }
    ]
    """
    report_id = data['selected_report_id']

    with open(os.path.join('data/database/reports/reports_information.json'), 'r', encoding='utf-8') as f:
        reports_inform = json.load(f)

    inform_obj = {}
    for report in reports_inform:
        if (report['id'] == report_id):
            inform_obj = report
            break

    with open(os.path.join(inform_obj['folder_path'], 'structure_list.json'), 'r', encoding='utf-8') as f:
        report_content = json.load(f)

    return  json.dumps(report_content, ensure_ascii=False)


def summarize_data_func(data, file):
    """
    input:
    data = {
        data_content:[
            {"column1": "value1", "column2": "value2"},
            {"column1": "value3", "column2": "value4"}
        ] #dataframe
        ...
    }
    output:
    result: {'stage': 'summarize_result', 'content': [{'type': 'text', 'text': '...'}]}
    {
        'name':
        'file_name':
        'dataset_description':
        'fields':[]
        'field_names':[]
    }
    """

    data['file_name'] = file.filename
    df = pd.read_csv(StringIO(file.stream.read().decode('utf-8')))
    data['data_content'] = df

    file_name = file.filename
    folder_name = os.path.splitext(file_name)[0]
    folder_path = os.path.join('data/database/datasets', folder_name)
    file_path = os.path.join(folder_path, file_name)
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)

    df.to_csv(file_path, index=False)

    with open(os.path.join('data/database/datasets/datasets_information.json'), 'r', encoding='utf-8') as f:
        datasets_inform = json.load(f)

    size = os.path.getsize(file_path)

    is_existed = False
    for dataset in datasets_inform:
        if(dataset['name'] == folder_name and dataset['size'] == size):
            is_existed = True
            inform_obj = dataset
            break
        elif(dataset['name'] == folder_name and dataset['size'] != size):
            return jsonify({"error": "File name already exists"}), 400
    if(not is_existed):
        summarize_result = summarizer.summarize(dataset_obj=data,
                                                cache_path=data["cache_path"], use_cache=data["use_cache"],
                                                update_cache=data["update_cache"])
        with open(os.path.join(folder_path, 'summary_result.json'), 'w', encoding='utf-8') as f:
            json.dump(summarize_result, f, ensure_ascii=False, indent=4)

        embedding_str_semantics = folder_name + summarize_result['dataset_description']
        dataset_embedding_semantics = get_embedding(embedding_str_semantics)

        embedding_str_data = ""
        for field in summarize_result["fields"]:
            embedding_str_data = embedding_str_data + " " + field['column']
        dataset_embedding_data = get_embedding(embedding_str_data)

        max_id = max(datasets_inform, key=lambda x: int(x["id"]))["id"]
        inform_obj = {
            "id": max_id+1,
            "name": folder_name,
            "size": size,
            "information": summarize_result['dataset_description'],
            "embedding_semantics": dataset_embedding_semantics,
            "embedding_data": dataset_embedding_data
        }
        datasets_inform.append(inform_obj)
        with open('data/database/datasets/datasets_information.json', 'w', encoding='utf-8') as f:
            json.dump(datasets_inform, f, ensure_ascii=False, indent=4)

    else:
        with open(os.path.join(folder_path, 'summary_result.json'), 'r', encoding='utf-8') as f:
            summarize_result = json.load(f)

    delete_all_files('data/cache/selected/dataset', '.csv')
    with open('data/cache/selected/dataset/selected_dataset.json', 'w', encoding='utf-8') as f:
        json.dump(inform_obj, f, ensure_ascii=False, indent=4)
    file_path = os.path.join('data/cache/selected/dataset', file_name)
    df.to_csv(file_path, index=False)
    with open('data/cache/selected/dataset/summary_result.json', 'w', encoding='utf-8') as f:
        json.dump(summarize_result, f, ensure_ascii=False, indent=4)

    return json.dumps(summarize_result, ensure_ascii=False)

def split_report_func(data, file):
    """
    input:
    data = {
        "summary_data":
        "report_content":[
            {'type': '', 'text': '' }
            ...
        ]
        ...
    }
    """
    with open('data/cache/selected/dataset/summary_result.json', 'r') as f:
        summary = json.load(f)
    data['summary_data'] = summary

    filename = file.filename
    file_path = os.path.join('data/cache/uploads', filename)
    file.save(file_path)

    with zipfile.ZipFile(file_path, 'r') as z:
        nested_folder = ""
        for i in z.namelist():
            folders = [f for f in z.namelist() if f.endswith('/')]
            if len(folders)>=1:
                nested_folder = folders[0]

        if nested_folder == "":
            folder_name = os.path.splitext(file.filename)[0]
            folder_path = os.path.join('data/cache/uploads/reports', folder_name)
            os.makedirs(folder_path)
            for i in z.namelist():
                z.extract(i, folder_path)
        else:
            folder_name = nested_folder
            folder_path = os.path.join('data/cache/uploads/reports', folder_name)
            for i in z.namelist():
                z.extract(i, 'data/cache/uploads/reports')

    size = 0
    md_file = ""
    for f in os.listdir(folder_path):
        if f.endswith('.md'):
            md_file = f
        size += os.path.getsize(os.path.join(folder_path, f))

    if md_file == "":
        return jsonify({"error": "no markdown file"}), 400

    report_path = os.path.join(folder_path, md_file)

    with open(os.path.join('data/database/reports/reports_information.json'), 'r', encoding='utf-8') as f:
        reports_inform = json.load(f)

    with open(report_path, 'r', encoding='utf-8') as f:
        header = f.readline()[2:].strip()

    is_existed = False
    for report in reports_inform:
        if (report['name'] == header and report['size'] == size):
            is_existed = True
            inform_obj = report
            break
        elif (report['name'] == header and report['size'] != size):
            return jsonify({"error": "File name already exists"}), 400

    destination_folder_path = os.path.join('data/database/reports', folder_name)
    if(not is_existed):
        try:
            shutil.copytree(folder_path, destination_folder_path)
        except Exception as e:
            print(f"error: {e}")

        report_list = convert(report_path, destination_folder_path)
        data['report_content'] = report_list

        with open(os.path.join(destination_folder_path, 'structure_list.json'), 'w', encoding='utf-8') as f:
            json.dump(report_list, f, ensure_ascii=False, indent=4)

    else:
        true_folder_path = destination_folder_path
        with open(os.path.join(true_folder_path, 'structure_list.json'), 'r', encoding='utf-8') as f:
            report_list = json.load(f)
        data['report_content'] = report_list

    spilt_result = spliter.split(report_data=data, folder_path=destination_folder_path, first_upload=(not is_existed), cache_path=data["cache_path"],
                                     use_cache=data["use_cache"], update_cache=data["update_cache"])

    if (not is_existed):
        report_str_semantics=""
        for seg in spilt_result:
            if seg['match_type'] == 'header':
                report_str_semantics = report_str_semantics + seg['text'][0]
            elif seg['match_type'] == 'matched' or seg['match_type'] == 'data analysis':
                report_str_semantics = report_str_semantics + seg['analysis question']
            elif seg['match_type'] == 'unmatched':
                report_str_semantics = report_str_semantics + seg['summary'][0]
        report_embedding_semantics = get_embedding(report_str_semantics)

        with open(os.path.join(destination_folder_path, "predict_fields.json"), "r", encoding="utf-8") as f:
            fields_result = json.load(f)
        report_str_data = ""
        fields_name = []
        for field in fields_result:
            report_str_data = report_str_data + field['field_name'] + " "
            fields_name.append(field['field_name'])
        report_embedding_data = get_embedding(report_str_data)

        max_id = max(reports_inform, key=lambda x: int(x["id"]))["id"]
        inform_obj = {
            "id": max_id + 1,
            "name": header,
            "size": size,
            "embedding_semantics": report_embedding_semantics,
            "embedding_data": report_embedding_data,
            "predicted_fields": fields_name,
            "folder_path": destination_folder_path,
        }
        reports_inform.append(inform_obj)
        with open('data/database/reports/reports_information.json', 'w', encoding='utf-8') as f:
            json.dump(reports_inform, f, ensure_ascii=False, indent=4)

    try:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"error: {e}")

    return json.dumps(spilt_result, ensure_ascii=False)

def select_dataset_func(data):
    '''
    input:{
        "selected_id":,
    }
    output content:{
        'summary_result':
    }
    '''
    id = data['selected_id']

    with open('data/database/datasets/datasets_information.json', 'r', encoding='utf-8') as file:
        datasets_inform = json.load(file)

    for dataset in datasets_inform:
        if int(dataset['id']) == int(id):
            inform_obj = dataset
            break

    with open('data/cache/selected/dataset/selected_dataset.json', 'w', encoding='utf-8') as f:
        json.dump(inform_obj, f, ensure_ascii=False, indent=4)

    delete_all_files('data/cache/selected/dataset', '.csv')
    folder_path = os.path.join('data/database/datasets', inform_obj['name'])
    source_path = os.path.join(folder_path, inform_obj['name']+".csv")
    destination_path = os.path.join('data/cache/selected/dataset', inform_obj['name']+".csv")
    shutil.copy2(source_path, destination_path)

    with open(os.path.join(folder_path, 'summary_result.json'), 'r', encoding='utf-8') as f:
        summary_result = json.load(f)
    with open('data/cache/selected/dataset/summary_result.json', 'w', encoding='utf-8') as f:
        json.dump(summary_result, f, ensure_ascii=False, indent=4)

    return json.dumps(summary_result, ensure_ascii=False)

def select_report_func(data):
    '''
    input:{
        "selected_id":,
        ...
    }
    output content:{
        'split_result':
    }
    '''
    id = data['selected_id']

    with open('data/database/reports/reports_information.json', 'r', encoding='utf-8') as file:
        reports_inform = json.load(file)

    for report in reports_inform:
        if int(report['id']) == int(id):
            inform_obj = report
            break

    delete_all_files('data/cache/selected/report/adapt_result', '.json')
    delete_all_files('data/cache/selected/report/execute_result', '.json')
    delete_all_files('data/cache/selected/report/insert_result', '.json')
    delete_all_files('data/cache/selected/report/organize_result', '.json')

    with open('data/cache/selected/dataset/summary_result.json', 'r', encoding='utf-8') as f:
        summary = json.load(f)
    with open(os.path.join(inform_obj['folder_path'], 'structure_list.json'), 'r', encoding='utf-8') as f:
        sturcture_list = json.load(f)
    report_data = {
        'summary_data': summary,
        'report_content': sturcture_list
    }
    spilt_result = spliter.split(report_data=report_data, folder_path=inform_obj['folder_path'], first_upload=False, cache_path=data["cache_path"],
                                 use_cache=data["use_cache"], update_cache=data["update_cache"])

    return json.dumps(spilt_result, ensure_ascii=False)

def organize_title_func(report_data):
    """
    data = {
        "reference_title": ...,
        "report_segments": [
            {
                "content": [],
                "logic":,
                "formed from": []
            },
        ],
        ...
    }
    output:
    process: {'stage': 'organize', 'content': [{'type': 'text', 'text': '...'}]}
    result: {'stage': 'organize_result', 'content': [{'type': 'text', 'text': '...'}]}
    """

    with open('data/cache/selected/dataset/summary_result.json', 'r', encoding='utf-8') as f:
        summary = json.load(f)
    update_chunk = organizer.stream_organize(summary_dataset=summary, report_data=report_data, cache_path=report_data["cache_path"], use_cache=report_data["use_cache"], update_cache=report_data["update_cache"])
    for chunk in update_chunk:
        yield f"data: {json.dumps(chunk)}\n\n"

def insert_goal_func(report_data):
    """
    input: {
        "select_fields": [],
        "select_logic": [],
        "previous_result": {
            "question": ...
            "content": ...
        }
        or
        "previous_result": ""
    }
    output: 
    process: {'stage': 'insert', 'content': [{'type': 'text', 'text': '...'}]}
    {
        "consideration": "Building on the previous findings of homicide trends in Los Angeles from 2020 to 2023, an elaboration on the age groups of the victims could provide a deeper understanding of who was most impacted by these homicides. This would involve examining if certain age groups faced higher incidences of becoming homicide victims and how these patterns changed over the years.",
        "logic": "elaboration",
        "fields": ["Date Occ", "Crm Type", "Vict Age"],
        "question": "What are the age distribution patterns of homicide victims from 2020 to 2023 in Los Angeles, and how do these patterns correlate with the fluctuations in annual homicide rates?"
    }
    result: {'stage': 'insert_result', 'content': [{'type': 'text', 'text': '...'}]}
    """
    with open('data/cache/selected/dataset/summary_result.json', 'r') as file:
        summary = json.load(file)

    insert_chunk = inserter.stream_insert(summary_dataset=summary, report_data=report_data, cache_path=report_data["cache_path"], use_cache=report_data["use_cache"], update_cache=report_data["update_cache"])
    return jsonify(insert_chunk)


def adapt_goal_func(report_data):
    """
    format of data: 
    {
        "content": ["type": "text", "text": ...],
        "question": ...,
        "relation": [{"edge": ..., "fromNode": {"original": ..., "new": ....}}]
    }
    """

    with open('data/cache/selected/dataset/summary_result.json', 'r', encoding='utf-8') as file:
        summary = json.load(file)

    adapt_chunk = adapter.stream_adapt(summary_dataset=summary, report_data=report_data, cache_path=report_data["cache_path"], use_cache=report_data["use_cache"], update_cache=report_data["update_cache"])
    for chunk in adapt_chunk:
        yield f"data: {json.dumps(chunk)}\n\n"

def imitate_text_func(data):
    """
    input:
    {
        report_data: {
            "id":
            "match_type":
            "text": [],
            "summary":
        },
        ...
    }
    """
    with open('data/cache/selected/dataset/summary_result.json', 'r', encoding='utf-8') as file:
        summary = json.load(file)

    imitate_chunk = imitator.stream_imitate(summary_dataset=summary, report_data=data["report_content"],
                                            cache_path=data["cache_path"], use_cache=data["use_cache"],
                                            update_cache=data["update_cache"])
    for chunk in imitate_chunk:
        yield f"data: {json.dumps(chunk)}\n\n"

def execute_goal_func(report_data):
    """
    format of data: 
    {
        "content": ["type": "text", "text": ...],
        "question": ...
    }
    """

    with open('data/cache/selected/dataset/summary_result.json', 'r', encoding='utf-8') as file:
        summary = json.load(file)

    file_name = glob.glob(os.path.join('data/cache/selected/dataset', "*.csv"))[0]
    df = pd.read_csv(file_name)
    execute_chunk = executor.stream_execute(summary_dataset=summary, df=df, report_data=report_data, cache_path=report_data["cache_path"], use_cache=report_data["use_cache"], update_cache=report_data["update_cache"])
    for chunk in execute_chunk:
        yield f"data: {json.dumps(chunk)}\n\n"
    

def generate_stream_data():
    image_path = 'test_data/Crime in Chicago in 2022/Figure 1.png'
    data_url = local_image_to_data_url(image_path)
    data=[{
            "stage": "exe",
            "content": [{"type": "image_url","image_url": data_url},]  
        },
        {
            "stage": "narration",
            "content": [{"type": "text", "text": "some hated friends to chat with, music for dreams, and the smoking of bitter ashes. "},
                        {"type": "image_url","image_url": data_url},]
        },
        {
            "stage": "code",
            "content": [{"type": "code", "code": "print('world!')"},
                        {"type": "code", "code": "numpy([1,2,3])"},]
        },
        {
            "stage": "narration",
            "content": [{"type": "text", "text": " The things my hungry heart has no use for."},
                        {"type": "text", "text": "some hated friends to chat with"},]
        },
        {
            "stage": "code",
            "content": [{"type": "code", "code": "print('hello')"},
                        {"type": "code", "code": "def funtion:"},]
        },
        ]
    count = 0
    while True:
        time.sleep(1)
        d = data[count%5]
        count += 1
        
        yield f"data: {json.dumps(d)}\n\n"

def generate_data():
    while True:
        yield f"{time.ctime()}\n"
        time.sleep(1)