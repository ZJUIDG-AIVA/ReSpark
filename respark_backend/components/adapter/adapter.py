
import json
import os.path

from components.tool import gpt4_chat_request, local_image_to_data_url, stream_response, parse_single_stage, \
    gpt3_chat_request
import time
import re

logical_last_prompt = '''
During the data analysis, analysts iteratively formulate analysis questions, conduct data processing steps, and obtain insights. 
Regarding the analysis question, analysts may form a new question based on either the data directly or the previous insights obtained. 
If the new question is based on previous insights, it can be formed from different logics, such as cause (find the cause of the previous insights) and elaboration (dive into more details of the previous insights).
The new question may also stem from only the data. 
You are a professional data analyst. You need to propose a new analysis question based on (1) data information and (2) previous analysis (optional), including a question and its insights. 

You would be provided with another similar example. This example contains a previous question, its insights (optional), and a new question. 
It also describes its logic to give the new question. 
Please imitate this example to give the new question. 
You must imitate the formed logic and focused data fields of the example and match the given previous insight and dataset information. 

For example, if the example is as follows: 
Source: 
Previous analysis question: What is the worldwide gross trend from 2000 to 2010?
The worldwide gross is the highest in 2010. 

New analysis question: What types of movies caused the highest worldwide gross in 2010 in the UK?
Logic: cause. 

The given information is as follows:
summary_dataset: (information about your movie dataset)
Source:
Previous analysis question: What is the worldwide gross trend from 2015 to 2020?
The worldwide gross in 2020 increased the most. 

Then, to propose the new analysis question for the given information, you should follow the steps as follows:

1. Imitate the logic and match the given insights. 
If the example question stems from the data directly, this step does not need any actions. Output the original question. 
Else, you need to inherit the logic in the example. 
First, you need to summarize the insights of the given previous analysis, such as "worldwide gross in 2020 increased the most". 
The given insights may be a longer narrative. Summarize it. The summarization should answer the previous question. 
Then, give the new question that imitates the logic and matches the given insights. 
That is, imitate the logic "cause" and replace the insights with the new insights you summarize: "worldwide gross in 2020 increased the most". 
Given the example new question "What types of movies caused the highest worldwide gross in 2010 in the UK?", the new question should be "What types of movies caused the increased worldwide gross in 2020 in the UK?" 

2. Inherit the focus data fields and match the given dataset fields. That is, inherit the focus data fields "types of movies." 
Justify if the data has related data field names, such as "genre." 
If yes, the new question does not need to be modified. It can still be "What types of movies caused the increased worldwide gross in 2020 in the UK?". The used fields would include ["genre"]. 
If no, for example, the given dataset information doesn't have any data fields about movie types. Based on the result of step 1 and the given dataset, recommend other suitable data fields. 
For example, the given dataset may contain the data field "director." Modify the question to "Which director's movie might have led to the worldwide gross increase in 2020 in the UK?". The used fields would include ["director"]. 
In this step, you should consider the data fields to use. Output them. 
You may find that the new question can't be given without external data sources or knowledge. 
You may fail to find a suitable data field within the given dataset. 
In such cases, please write the question as "none", and explain the reason in the consideration. 

3. Check the inconsistency with the context and scope of data. 
For example, the given data may be sourced from the USA instead of the UK. Modify the question to "Which director's movie might have led to the worldwide gross increase in 2020 in the USA?".
The scope of data fields also needs to be matched, especially for the data fields about time. 
For example, the original analysis may be conducted in 2015 and pays more attention on 2015. 
The new data stems from 2010 to 2023, then the new analysis should pay attention on 2023. 
You may find that the new question can't be given without external data sources or knowledge. 
The data's scope may not align with the logic needed to form the question. 
For example, the question may be formed based on a generalization to a larger scope, which is not available in the given dataset. 
In such cases, please write the question as "none", and explain the reason in the consideration. 

You need to follow the steps above. For each step, you need to describe your considerations. 
Finally, you must output the result question and the needed data fields to process this question. 
In each step, please note that the new question MUST be different from the previous analysis question. 

Return in this JSON format: 

{
    "step 1": { // Imitate the logic and match the given insights. 
        "consideration": "...", // "none" if the new question can't be given without external data sources or knowledge
        "question": "..."
    },
    "step 2": { // Inherit the focus data fields and match the given dataset fields. 
        "consideration": "...",
        "question": "...", // "none" if the new question can't be given without external data sources or knowledge
        "data fields": [list of data field names]
    },
    "step 3": { // Check the inconsistency with the context and scope of data. 
        "consideration": "...",
        "question": "...", // "none" if the new question can't be given without external data sources or knowledge
        "data fields": [list of data field names]
    },
    "result": {
        "question": "...", // "none" if the new question can't be given without external data sources or knowledge
        "data fields": [list of data field names]
    }
}
'''

def stream_adapt_goal(summary_dataset, report_data, prompt=["adapt_prompt"], use_image=True, force_4=False, cache_path="test_cache",
                      use_cache=True, update_cache=True):
    if "question" not in report_data:
        return
    question = report_data["question"]
    relation = report_data["relation"][0]
    fromNode = relation["fromNode"]
    edge = relation["edge"]
    user_content = []
    user_content.append({"type": "text", "text": f"Here is the example: \n"})
    if fromNode == "data":
        user_content.append(
            {"type": "text", "text": f"Source: \nThis analysis question directly stems from the data. "})
        user_content.append({"type": "text", "text": f"New analysis question: \n{question}"})
        user_content.append({"type": "text", "text": f"Logic: \nThis analysis question directly stems from the data. "})

        user_content.append({"type": "text", "text": f"\nHere is the given information you need. \n"})
        user_content.append({"type": "text", "text": f"\"summary_dataset\": \n{json.dumps(summary_dataset)}"})
        user_content.append({"type": "text", "text": f"\nSource: Your analysis question should stem from the data. \n"})
    else:
        originalFromNode = fromNode["original"]
        originalFromQuestion = originalFromNode["question"]
        originalFromContent = originalFromNode["content"]
        newFromNode = fromNode["new"]
        newFromQuestion = newFromNode["question"]
        newFromContent = newFromNode["content"]
        edge_relation = edge["relation"]
        edge_description = edge["description"]
        user_content.append(
            {"type": "text", "text": f"Source: \nThis analysis question stems from the analysis as follows: "})
        user_content.append({"type": "text", "text": f"Previous analysis question: \n{originalFromQuestion}"})
        for temp in originalFromContent:
            if temp["type"] != "table" and temp["type"] != "code":
                if temp["type"] == "image_path":
                    image_url = local_image_to_data_url(image_path=temp["image_path"])
                    user_content.append({"type": "image_url", "image_url": {"url": image_url}})
                elif temp["type"] == "image_url":
                    user_content.append({"type": "image_url", "image_url": {"url": temp["image_url"]}})
                else:
                    user_content.append(temp)
        user_content.append({"type": "text", "text": f"New analysis question: \n{question}"})
        user_content.append({"type": "text", "text": f"Logic: \n{edge_relation}\n{edge_description}"})

        user_content.append({"type": "text", "text": f"\nHere is the given information you need. \n"})
        user_content.append({"type": "text", "text": f"\"summary_dataset\": \n{json.dumps(summary_dataset)}"})
        user_content.append(
            {"type": "text", "text": f"Source: \nYour analysis question stems from the analysis as follows: "})
        user_content.append({"type": "text", "text": f"Previous analysis question: \n{newFromQuestion}"})
        for temp in newFromContent:
            if temp["type"] != "table" and temp["type"] != "code":
                if temp["type"] == "image_path":
                    image_url = local_image_to_data_url(image_path=temp["image_path"])
                    user_content.append({"type": "image_url", "image_url": {"url": image_url}})
                elif temp["type"] == "image_url":
                    user_content.append({"type": "image_url", "image_url": {"url": temp["image_url"]}})
                else:
                    user_content.append(temp)

    has_image = False
    for item in user_content:
        if item["type"] == "image_path":
            has_image = True
        if item["type"] == "image_url":
            has_image = True

    messages = [
        {"role": "system", "content": logical_last_prompt},
        {"role": "user", "content": user_content},
    ]
    yield {"messages": messages}
    max_tokens = 1000
    if (has_image != False and use_image == True) or force_4 == True:
        function_result, function_key = gpt4_chat_request(messages=messages, prompt=prompt, max_tokens=max_tokens, stream=True,
                                                          cache_path=cache_path, use_cache=use_cache,
                                                          update_cache=update_cache)
    else:
        function_result, function_key = gpt4_chat_request(messages=messages, prompt=prompt, max_tokens=max_tokens, stream=True,
                                                          cache_path=cache_path, use_cache=use_cache,
                                                          update_cache=update_cache)

    for temp in stream_response(function_result, function_key, cache_path=cache_path, update_cache=update_cache):
        yield temp

def get_stage_result(stage, stage_json):
    if stage == "result":
        stage = "Final Result"
    if "consideration" in stage_json:
        yield {"stage": stage, "content": [{"type": "text", "text": stage_json["consideration"]}]}
    if "question" in stage_json:
        yield {"stage": stage, "content": [{"type": "objective", "objective": stage_json["question"]}]}
    if "data fields" in stage_json:
        yield {"stage": stage, "content": [{"type": "data field", "data field": stage_json["data fields"]}]}


def stream_adapt(summary_dataset, report_data, use_image=True, force_4=False, cache_path="test_cache", use_cache=True,
                 update_cache=True):

    question_chunks = stream_adapt_goal(
        summary_dataset=summary_dataset,
        report_data=report_data,
        use_image=use_image,
        cache_path=cache_path,
        force_4=force_4,
        use_cache=use_cache,
        update_cache=update_cache
    )
    cache_chunk = ""
    stage = ""
    for chunk in question_chunks:
        if "generating" in chunk:
            temp_chunk = chunk["generating"]
            cache_chunk = cache_chunk + temp_chunk
            step_pattern = re.compile(r'"step \d"|"\bresult\b"')
            match = step_pattern.search(cache_chunk)
            if match:
                start_pos = match.start()
                end_pos = match.end()
                new_stage = cache_chunk[start_pos + 1:end_pos - 1]
                if stage != "":
                    between_stage = cache_chunk[:start_pos]
                    between_stage = json.loads(parse_single_stage(between_stage))
                    for content in get_stage_result(stage, between_stage):
                        yield content
                        time.sleep(0.1)
                cache_chunk = cache_chunk[end_pos:]
                stage = new_stage
    result = json.loads(parse_single_stage(cache_chunk))
    for content in get_stage_result(stage, result):
        yield content
        time.sleep(0.1)
