import json
from components.tool import gpt4_chat_request, gpt3_chat_request, stream_response
import re
from lida import Manager, llm

summarize_prompt = '''
This is the information of a dataset. 
"file_name" denotes the file name of my dataset, 
"field_names" lists all the data field names, 
and "fields" denotes the information of each data field, including the column name and properties, such as data type, min, max, std, num_unique_values, and samples. 
Firstly, Based on these information, briefly describe the meaning of each data field.
Secondly, describe the total dataset, including what the dataset is about, what the each row of data is about. 


Return in this JSON format:
{
    "name of data field1": ..., # meaning of this field. Please limit to 50 characters.
    "name of data field2": ...,
    ...,
    "dataset_description": ... # The description of the dataset. Please limit to 150 words.
}
'''

default_file_name = "../test_data/detail type data/Crime Data from 2020 to 2023 in LA.csv"
save_summary = "../test_data/detail type data/summary.json"

def get_pre_summary(df_data, file_name):
    lida = Manager(text_gen=llm("cohere"))  # palm, cohere ..
    summary = lida.summarize(df_data)
    summary['name'] = file_name
    summary['file_name'] = file_name
    return summary


def get_summarize(df_data, file_name, prompt=["summarize_prompt"], use_image=True, force_4=False, cache_path="test_cache", use_cache=False,
                         update_cache=True):
    summary = get_pre_summary(df_data, file_name)

    messages = [
        {"role": "system", "content": summarize_prompt},
        {"role": "user", "content": json.dumps(summary)}
    ]
    function_result = gpt4_chat_request(messages=messages, prompt=prompt, max_tokens=1000, stream=False, cache_path=cache_path,
                                        use_cache=use_cache, update_cache=update_cache)

    function_result = function_result[0]

    pattern = re.compile(r'\{([^{}]*)\}')
    match = pattern.search(function_result)
    if match:
        result = json.loads(match.group())
    else:
        result = {}
    for field in summary["fields"]:
        del field["properties"]["semantic_type"]
        field["properties"]["description"] = result[field["column"]]

    summary['dataset_description'] = result['dataset_description']

    return summary

def summarize(dataset_obj, use_image=True, force_4=False, cache_path="test_cache", use_cache=True, update_cache=True):
    df_data = dataset_obj['data_content']
    file_name = dataset_obj['file_name']

    summary = get_summarize(
        df_data=df_data,
        file_name=file_name,
        use_image=use_image,
        force_4=force_4,
        cache_path=cache_path,
        use_cache=use_cache,
        update_cache=update_cache
    )

    return summary
