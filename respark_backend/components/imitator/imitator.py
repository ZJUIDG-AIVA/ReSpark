import json
import os.path

from components.tool import gpt4_chat_request, gpt3_chat_request, stream_response

imitate_prompt = '''
You are an expert report writer with deep knowledge of historical and current events.
Your task is to generate new statement based on a provided dataset imitating the provided statement example.

Please follow these guidelines when writing the new statement:
1. Please imitate the writing in "reference_statement". Use the same tone and narrative perspective.
2. Follow the theme of the provided dataset.
3. DON'T introduce the dataset. DON'T mention any data.
4. Avoid repeating the exact content of the provided statement; instead, create original text that fits naturally within the report.
5. The length of the new statement should be similar to the "reference_statement".

I will provide you with a description of a dataset, and a reference statement.
Your goal is to generate a new statement that is consistent with the theme of the dataset, with writing style and tone consistent with the "reference_statement". 
At the same time, generate a brief summary of the new statement you have written. No more than 20 words.

Your result must fit the following template. Please keep the special mark format (<statement> and <summary>). 
```
<statement> 
Write the content of the new statement here.
<summary>
Write the summary of the new statement here. No more than 20 words.
```

'''

def stream_get_imitate(summary_dataset, report_data, prompt=["imitate_prompt"], cache_path="test_cache", use_cache=True, update_cache=True):
    # report_data = {
    #     "id":
    #     "match_type":
    #     "text": [],
    #     "summary":
    # }

    user_content = []
    user_content.append({"type": "text", "text": f"\"Summary of the dataset:\": \n{summary_dataset}\n\n"})
    user_content.append({"type": "text", "text": f"\"reference_statement: \": \n{report_data['text'][0]}\n\n"})
    messages = [
        {"role": "system", "content": imitate_prompt},
        {"role": "user", "content": user_content},
    ]
    yield {"messages": messages}
    function_result, function_key = gpt3_chat_request(messages=messages, prompt=prompt, max_tokens=800, stream=True, cache_path=cache_path, use_cache=use_cache, update_cache=update_cache)
    for temp in stream_response(function_result, function_key, cache_path=cache_path, update_cache=update_cache):
        yield temp


def stream_imitate(summary_dataset, report_data, cache_path="test_cache", use_cache=True, update_cache=True):
    """
    report data = {
        "id":
        "text": [],
        "summary": [],
    }
    """

    result = ""

    imitate_chunks = stream_get_imitate(
        summary_dataset=summary_dataset,
        report_data=report_data,
        cache_path=cache_path,
        use_cache=use_cache,
        update_cache=update_cache
    )
    next_begin = "none"
    cache_chunk = ""
    label_str = ""
    for chunk in imitate_chunks:
        if "generating" in chunk:
            temp_chunk = chunk["generating"]
            if next_begin == "none":
                cache_chunk = cache_chunk + temp_chunk
                statement_index = cache_chunk.find("<statement>")
                summary_index = cache_chunk.find("<summary>")
                if statement_index != -1 and summary_index != -1:
                    next_begin = "text"
                    chat_stage = "statement"
                    statement_index = statement_index + 11
                    text_chunk = cache_chunk[statement_index:summary_index].strip()
                    yield {"stage": chat_stage,
                           "content": [{"type": next_begin, next_begin: text_chunk}]}
                    summary_index = summary_index + 9
                    cache_chunk = cache_chunk[summary_index:].lstrip()
                    chat_stage = "summary"
                    yield {"stage": chat_stage,
                           "content": [{"type": next_begin, next_begin: cache_chunk}]}
                elif statement_index != -1:
                    next_begin = "text"
                    chat_stage = "statement"
                    statement_index = statement_index + 11
                    cache_chunk = cache_chunk[statement_index:]
                    cache_chunk = cache_chunk.lstrip()
                    yield {"stage": chat_stage,
                           "content": [{"type": next_begin, next_begin: cache_chunk}]}
                elif summary_index != -1:
                    next_begin = "text"
                    chat_stage = "statement"
                    statement_chunk = cache_chunk[:summary_index].rstrip()
                    yield {"stage": chat_stage,
                           "content": [{"type": next_begin, next_begin: statement_chunk}]}
                    chat_stage = "summary"
                    summary_index = summary_index + 9
                    cache_chunk = cache_chunk[summary_index:].lstrip()
                    yield {"stage": chat_stage,
                           "content": [{"type": next_begin, next_begin: cache_chunk}]}
            else:
                label_index = temp_chunk.find("<")
                summary_index = temp_chunk.find("<summary>")
                if label_index != -1 and summary_index == -1:
                    label_str = temp_chunk[label_index:].rstrip()
                    temp_chunk = temp_chunk[:label_index]
                elif summary_index != -1:
                    next_begin = "text"
                    if summary_index != 0:
                        last_chunk = temp_chunk[:summary_index].rstrip()
                        yield {"stage": chat_stage,
                               "content": [{"type": next_begin, next_begin: last_chunk}]}
                    summary_index = summary_index + 9
                    temp_chunk = temp_chunk[summary_index:].lstrip()
                    chat_stage = "summary"
                elif label_str != "":
                    label_end_index = temp_chunk.find(">")
                    temp_chunk = temp_chunk[label_end_index + 1:].lstrip()
                    chat_stage = "summary"
                    label_str = ""

                if temp_chunk.endswith("```"):
                    temp_chunk = temp_chunk[:-3].rstrip()
                yield {"stage": chat_stage,
                       "content": [{"type": next_begin, next_begin: temp_chunk}]}

        if "gpt_result" in chunk:
            gpt_result = chunk["gpt_result"]
            result = gpt_result

    yield {"stage": "imitate_result", "content": [{"type": "text", "text": result}]} # mark the end of execution

