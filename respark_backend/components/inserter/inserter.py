
import json
from components.tool import gpt4_chat_request, gpt3_chat_request, stream_response
import re


insert_prompt = """
You are a professional data analyst renowned for your expertise in articulating insightful data analysis questions. 
Your task is to propose a new data analysis question that could either stem from previous analysis findings or directly from the dataset itself. 

In cases where the question is based on prior findings, you will be provided with these findings. 
Your new analysis question should logically connect to the previous findings according to one or more of the following relationships:

1. Similarity: change some conditions to analyze a logically parallel question. For example, first analyze the trend of type A, then analyze the trend of type B. 
2. Temporal: analyze the same question but focus on different periods of time. 
3. Contrast: Analyze a contradictory fact compared to the previous segment. For example, after finding that a product's sales trends increased (previous segment), propose an analysis question of "What products have a decreased sales trend?" 
4. Cause-effect: Find the cause and reason of the previous segment result. 
5. Elaboration: Narrow down to a smaller scope of data or add some conditions to analyze the details. The latter segment adds more details to the previous one. 
6. Generalization: Generalizing to a larger scope or reducing some conditions to conduct a more general analysis is the opposite of elaboration.

Otherwise, if your question is based on the data directly, the logic of your question should be: 
0. initial: Initial analysis question from data. 

Additionally, your question should revolve around data fields in the dataset (information provided in summary_dataset). 

You might be directed to utilize certain logic or data fields. 
If not specified, you are encouraged to choose appropriate fields and logical relationships from the available dataset and analysis context.

Your goal is to formulate a SINGLE analysis question, specifying the logical relationship and identifying relevant data fields. 
The question should be concise. 
Return in a JSON format:

{
   "consideration": "Description of the basis for the new analysis question, including logic and fields. ",
   "logic": "The logical relationship (e.g., imitial, similarity, temporal, contrast, cause-effect, elaboration, generalization) that your question follows.",
   "fields": ["List of relevant data fields your question focuses on."],
   "question": "The specific analysis question you propose."
}
"""


def stream_get_insert(summary_dataset, report_data, prompt=["insert_prompt"], use_image=True, force_4 = False, cache_path="test_cache", use_cache=True, update_cache=True):
    """
    data = {
        "select_fields": [],
        "select_logic": [],
        "previous_result": {
            "question": ...
            "content": ...
        }
        or
        "previous_result": ""
    }
    """

    if "previous_result" not in report_data:
        return
    has_image = False
    select_fields = report_data["select_fields"]
    select_logic = report_data["select_logic"]
    previous_result = report_data["previous_result"]
    user_content = []
    user_content.append({"type": "text", "text": f"\"summary_dataset\": \n{json.dumps(summary_dataset)}"})
    if previous_result == "":
        user_content.append({"type": "text", "text": f"\"previous result\": \nNone. Please give an analysis question from the dataset information. \n\n"})
    else:
        question = previous_result["question"]
        content = previous_result["content"]
        previous_result_str = "\"previous result\": \n"
        previous_result_str += f"Previous analysis question: {question}\n"
        if type(previous_result) != str and type(previous_result['content']) != str:
            for obj in previous_result['content']:
                if obj["type"] == "image_url":
                    previous_result['content'].remove(obj)
        previous_result_str += f"Previous findings: {content}\n"
        user_content.append({"type": "text", "text": previous_result_str})
    select_info = ""
    if len(select_fields) > 0:
        temp = json.dumps(select_fields)
        select_info += f"Specified data fields: {temp}\n"
    if len(select_logic) > 0:
        temp = json.dumps(select_logic)
        select_info += f"Specified data logic: {temp}\n"
    if select_info != "":
        user_content.append({"type": "text", "text": select_info})
    messages = [
        {"role": "system", "content": insert_prompt},
        {"role": "user", "content": user_content},
    ]

    yield {"messages": messages}
    if (has_image != False and use_image == True) or force_4 == True:
        function_result, function_key = gpt4_chat_request(messages=messages, prompt=prompt, max_tokens=300, stream=True, cache_path=cache_path, use_cache=use_cache, update_cache=update_cache)
    else:
        function_result, function_key = gpt3_chat_request(messages=messages, prompt=prompt, max_tokens=300, stream=True, cache_path=cache_path, use_cache=use_cache, update_cache=update_cache)
    for temp in stream_response(function_result, function_key, cache_path=cache_path, update_cache=update_cache):
        yield temp

def stream_insert(summary_dataset, report_data, use_image=True, force_4 = False, cache_path="test_cache", use_cache=True, update_cache=True):
    """
    data = {
        "select_fields": [],
        "select_logic": [],
        "previous_result": {
            "question": ...
            "content": ...
        }
        or
        "previous_result": ""
    }
    """

    messages = []
    gpt_result = ""

    insert_chunks = stream_get_insert(
        summary_dataset=summary_dataset, 
        report_data=report_data,
        use_image=use_image,
        force_4=force_4, 
        cache_path=cache_path,
        use_cache=use_cache, 
        update_cache=update_cache
    )

    for chunk in insert_chunks:
        if "gpt_result" in chunk:
            gpt_result = chunk["gpt_result"]

    if "```" in gpt_result:
        pattern = r"```(?:\w+\n)?([\s\S]+?)```"
        matches = re.findall(pattern, gpt_result)
        if matches:
            gpt_result = matches[0]


    return json.loads(gpt_result)
