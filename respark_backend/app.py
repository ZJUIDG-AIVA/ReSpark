from io import StringIO

from flask import Flask, Flask, Response,stream_with_context,jsonify, request
from flask_cors import CORS
import sys
import os
from utils import (execute_goal_func,adapt_goal_func,insert_goal_func,organize_title_func,summarize_data_func,split_report_func,
                   recommend_report_func, get_database_func, select_report_func, select_dataset_func, get_cache_list_func,
                   create_cache_func, imitate_text_func, get_report_content_func)
import base64
import json
import pandas as pd
from dotenv import load_dotenv

load_dotenv(override=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
CORS(app)

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/get_database', methods=['GET', 'POST', 'STREAM'])
def get_database():
    '''
    input:{...}
    output:{
        datasets:[{
            'id':,
            'name':,
            'size':,
        }],
        reports:[{
            'id':,
            'name':,
            'size':,
            '
        }],
    }
    '''
    return Response(get_database_func(), mimetype='application/json')

@app.route('/get_cache_list', methods=['GET', 'POST', 'STREAM'])
def get_cache_list():
    '''
    input:{...}
    output:[
        {
            'id':,
            'name':,
            'dataset':,
            'report':
        }, ...
    ]
    '''
    return Response(get_cache_list_func(), mimetype='application/json')

@app.route('/create_cache', methods=['GET', 'POST', 'STREAM'])
def create_cache():
    '''
    input:{
        'name':,
        'select_dataset_id':,
        'select_report_id':,
    }
    '''
    data = request.json
    return Response(create_cache_func(data=data), mimetype='application/json')

@app.route('/get_report_content', methods=['GET', 'POST', 'STREAM'])
def get_report_content():
    '''
    input:{
        'select_report_id':,
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
    '''
    data = request.json
    return Response(get_report_content_func(data=data), mimetype='application/json')

@app.route('/summarize_data', methods=['GET', 'POST', 'STREAM'])
def summarize_data():
    """
    input:
    json: {
        ...
    }
    file: csv
    """
    data = {
        'cache_path': request.args.get('cache_path', 'test_cache'),
        'use_cache': request.args.get('use_cache', True),
        'update_cache': request.args.get('update_cache', False),
    }
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Need a csv file!"}), 400

    return Response(summarize_data_func(data, file), mimetype='application/json')

@app.route('/split_report', methods=['GET', 'POST', 'STREAM'])
def split_report():
    """
    input:
    json: {
        ...
    }
    file: zip
    """
    data = {
        'cache_path': request.args.get('cache_path', 'test_cache'),
        'use_cache': request.args.get('use_cache', True),
        'update_cache': request.args.get('update_cache', False)
    }
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not file.filename.endswith('.zip'):
        return jsonify({"error": "Need a zip file!"}), 400

    return Response(split_report_func(data, file), mimetype='application/json')

@app.route('/recommend_report', methods=['GET', 'POST', 'STREAM'])
def recommend_report():
    """
    input:
    json: {
        ...
    }
    file: csv
    """
    data = request.json
    return Response(recommend_report_func(data), mimetype='application/json')

@app.route('/select_dataset', methods=['GET', 'POST', 'STREAM'])
def select_dataset():
    """
    input:{
        "selected_id":,
    }
    output content:{
        'summary_result':
    }
    """
    data = request.json
    return Response(select_dataset_func(data), mimetype='application/json')

@app.route('/select_report', methods=['GET', 'POST', 'STREAM'])
def select_report():
    """
    input:{
        "selected_id":,
    }
    output content:{
        'split_result':
    }
    """
    data = request.json
    return Response(select_report_func(data), mimetype='application/json')

@app.route('/organize_title', methods=['GET', 'POST', 'STREAM'])
def organize_title():
    """
    input:
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
    process: {'stage': 'title', 'content': [{'type': 'text', 'text': '...'}]}
    result: {'stage': 'title_result', 'content': [{'type': 'text', 'text': '...'}]}
    """
    data = request.json
    return Response(organize_title_func(data), mimetype='text/event-stream')

@app.route('/insert_goal', methods=['GET', 'POST', 'STREAM'])
def insert_goal():
    """
    input: data = {
        "select_fields": [],
        "select_logic": [],
        "generated_segment": {
            "id": {
                "question": ...
                "content": ...
            }
        }
        "fromId": ... # -1 => data
    }
    """
    data = request.json
    return insert_goal_func(data)

@app.route('/adapt_goal', methods=['GET', 'POST', 'STREAM'])
def adapt_goal():
    """
    format of data: 
    {
        "content": ["type": "text", "text": ...],
        "question": ..., // objective
        "relation": [{"edge": ..., "fromNode": {"original": ..., "new": ....}}]
    }
    """
    data = request.json
    return Response(adapt_goal_func(data), mimetype='text/event-stream')

@app.route('/imitate_text', methods=['GET', 'POST', 'STREAM'])
def imitate_text():
    """
    input:
    {
        report_data: {
            "id":
            "match_type":
            "text": [],
            "summary":
        },
    }
    output result content:
    {
        "id":
        "match_type":
        "text": [],
        "summary":
    }
    """
    data = request.json
    return Response(imitate_text_func(data), mimetype='text/event-stream')

@app.route('/execute_goal', methods=['GET', 'POST', 'STREAM'])
def execute_goal():
    """
    format of data: 
    {
        "content": ["type": "text", "text": ...],
        "question": ...
    }
    """
    data = request.json
    return Response(execute_goal_func(data), mimetype='text/event-stream')

@app.route('/data', methods=['POST'])
def get_data():
    file = request.files['file']
    question = request.form.get('question')
    content = request.form.get('content')
    return jsonify({'message': 'POST success','question':question,'content':content,'file':file.filename})

@app.route('/upload_image', methods=['POST'])
def upload_image():
    data = request.get_json()
    image_data = data['image']

    if "data:image/png;base64," in image_data:
        header, image_data = image_data.split("data:image/png;base64,")

    image_bytes = base64.b64decode(image_data)
    return jsonify({'message': 'Image uploaded successfully'})

if __name__ == '__main__':
    app.run(debug=False)