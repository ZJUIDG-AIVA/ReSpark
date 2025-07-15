import json
import os

from components.tool import gpt4_chat_request, stream_response, gpt3_chat_request

organize_prompt = """
Your task is to simulate a given reference title and generate a title for the provided content.

There are several requirements for generating titles:
1. Imitate the sentence structure and style of the reference title
2. Concise and clear
3. The title length is similar to the reference title
4. If no reference title is provided, create a title based on your judgment directly
5. The angle explained is consistent with the reference title. For example, if the reference title is "Comedy Movie" and the given content is about the changes in ratings of an action movie, then the title you generate should be "Action Movie" and no additional content needs to be added.
6. Each segment contains a generation logic and the segment content that the logic depends on. You need to understand the logical relationship between this segment and the segment it depends on, and reflect this logical relationship in the title you generate.
    The logics of forming a segment can be one of these types:
    a. initial: initial analysis question from dataset. In this case, you don't need to reflect the logic in the title.
    b. similarity: change some condition to analysis a logically parallel question of the previous segment. For example, the previous segment analyze the trend of type A, then this segment analyze the trend of type B.
    c. contrast: analyze a contradiction fact compared to the previous segment. For example, after previous segment finding that the sales trends of a product increases (previous segment), this segment propose an analysis question of "What prodocts have a decrease sales trend?".
    d. cause: find the cause of the result of previous segment.
    e. effect: find the effect of the result of previous segment.
    f. elaboration: narrow down to a smaller scope of data that analysed in the previous segment or add some conditions to analyze the details. The latter segment adds more details to the previous one.
    g. generalization: generalize to a larger scope such as a wider time period, or reduce some conditions, to conduct a more general analysis, which is in opposite to elaboration.
    h. temporal: analyze the same question as the previous segment but focus on different period of time. If the generation logic of a segment does not belong to any of the above, but only changes the focused time period, it belongs to this logic.
7. If there are multiple segments in the content list, you do not need to generate separate titles, but integrate and summarize these analysis questions and results to generate a unique title.

The data I provided to you includes: reference title, content list.
The format of data I provided is:
{
    "reference title": ,# "New Title" if there is no reference title
    "content list":[
        {
            "content": [],# The content of this segment
            "logic": ,# The logic of generating this segment
            "formed from": [],# The segment content that the generation logic of this segment depends on
        }
    ]
}

Your goal is to generate concise and accurate titles for some given content based on the above instructions.
"""


def stream_get_organize(report_data, prompt=["organize_prompt"], use_image=True, force_4 = False, cache_path="test_cache", use_cache=True, update_cache=True):
    if "report_segments" not in report_data:
        return
    has_image = False
    title = report_data["reference_title"]
    segments = report_data["report_segments"]
    for segment in segments:
        if "logic" not in segment:
            segment["logic"] = "initial"
            segment["formed from"] = -1
    contents_to_send = {
        "reference_title": title,
        "content_list": [],
    }

    for seg in segments:
        contents_to_send["content_list"].append({
            "content": seg["content"],
            "logic": seg["logic"],
            "formed from": seg["formed from"],
        })

    messages = [
        {"role": "system", "content": organize_prompt},
        {"role": "user", "content": json.dumps(contents_to_send)},
    ]

    yield {"messages": messages}
    if (has_image != False and use_image == True) or force_4 == True:
        function_result, function_key = gpt4_chat_request(messages=messages, prompt=prompt, max_tokens=100, stream=True, cache_path=cache_path, use_cache=use_cache, update_cache=update_cache)
    else:
        function_result, function_key = gpt3_chat_request(messages=messages, prompt=prompt, max_tokens=100, stream=True, cache_path=cache_path, use_cache=use_cache, update_cache=update_cache)
    for temp in stream_response(function_result, function_key, cache_path=cache_path, update_cache=update_cache):
        yield temp

def stream_organize(summary_dataset, report_data, use_image=True, force_4 = False, cache_path="test_cache", use_cache=True, update_cache=True):
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
    """

    gpt_result = ""

    organize_chunks = stream_get_organize(
        report_data=report_data,
        use_image=use_image,
        force_4=force_4, 
        cache_path=cache_path, 
        use_cache=use_cache, 
        update_cache=update_cache
    )

    for chunk in organize_chunks:
        if "messages" in chunk:
            messages = chunk["messages"]
        if "generating" in chunk:
            temp_chunk = chunk["generating"]
            yield {"stage": "organize", "content": [{"type": "text", "text": temp_chunk}]}
        if "gpt_result" in chunk:
            gpt_result = chunk["gpt_result"].strip('"').strip("'")
    
    yield {"stage": "organize_result", "content": [{"type": "text", "text": gpt_result}]} # mark the end of execution
