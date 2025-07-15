import base64
import inspect
import math
import random
from mimetypes import guess_type
import openai
from openai import AzureOpenAI, OpenAI
import requests
import functools
import json
import os
import time
import re
import copy

from pyexpat.errors import messages

generate_step = 500

def parse_single_stage(text):
    pattern = re.compile(r'\{[^}]*\}')
    match = pattern.search(text)
    if match:
        content_within_braces = match.group()
        return content_within_braces
    else:
        return ""

def parse_final_result(text, key):
    pattern = re.compile(r'\{([^{}]*)\}')
    matches = re.findall(pattern, text)
    for match in matches:
        match = "{"+match+"}"
        obj = json.loads(match)
        if key in obj:
            return obj
    return {}

def find_outer_braces(text):
    start = -1
    brace_count = 0
    for i, char in enumerate(text):
        if char == '{':
            if brace_count == 0:
                start = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                return text[start:i+1]
    return None

def custom_lru_cache(func):
    cache = {}
    @functools.wraps(func)
    def memoizer(*args, **kwargs):
        cache_path = kwargs["cache_path"]
        cache_file = os.path.join("data/cache", cache_path, 'cache.json')
        cache = {}
        kwargs_dict = copy.deepcopy(kwargs)
        messages = kwargs_dict["messages"]
        prompts = kwargs_dict['prompt']
        iprompt = 0

        for i in range(len(messages)):
            mes_dict = messages[i]
            if mes_dict["role"] == "system":
                mes_dict["content"] = prompts[iprompt]
                iprompt += 1
            elif mes_dict["role"] == "user":
                if type(mes_dict["content"]) == list:
                    for j in range(len(mes_dict["content"])):
                        user_dict = mes_dict["content"][j]
                        if user_dict["type"] == "image_url":
                            kwargs["messages"][i]["content"][j]["image_url"]["detail"] = "low"

        del kwargs_dict["use_cache"]
        del kwargs_dict["update_cache"]
        del kwargs_dict["cache_path"]
        del kwargs_dict['prompt']
        key = json.dumps((args, kwargs_dict))
        if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        if kwargs["use_cache"] == True:
            if key not in cache:
                print("noy key in cache")
                result = func(*args, **kwargs)
                try:
                    json.dumps(result)
                except (TypeError, OverflowError):
                    return result, key
                if kwargs["update_cache"] == True:
                    cache[key] = result
                    if not os.path.exists(cache_file):
                        directory = os.path.dirname(cache_file)
                        if not os.path.exists(directory):
                            os.makedirs(directory)
                    with open(cache_file, 'w') as f:
                        json.dump(cache, f)
                return result, key

            else:
                print("read cache")
                return cache[key], key
        else:
            result = func(*args, **kwargs)
            try:
                json.dumps(result)
            except (TypeError, OverflowError):
                return result, key
            if kwargs["update_cache"] == True:
                cache[key] = result
                directory = os.path.dirname(cache_file)
                if not os.path.exists(directory):
                    os.makedirs(directory)
                with open(cache_file, 'w') as f:
                    json.dump(cache, f)
            return result, key
    return memoizer

def handle_no_stream_response(response):
    if(isinstance(response, openai.types.chat.chat_completion.ChatCompletion)):
        temp = response
        return temp.choices[0].message.content
    else:
        return "error"

def handle_response(response):
    if (isinstance(response, openai.Stream)):
        for chunk in response:
            if len(chunk.choices) > 0:
                choice = chunk.choices[0]
                #获取流对象的内容，可能在两个地方
                if hasattr(choice, "delta") and choice.delta != None:
                    chunk_content = choice.delta.content
                    if chunk_content != None:
                        yield chunk_content
                elif hasattr(choice, "messages") and choice.messages != None and len(choice.messages) > 0:
                    chunk_object = choice.messages[0]["delta"]
                    if "content" in chunk_object and chunk_object["content"] != None:
                        yield chunk_object["content"]
    else:
        return "error"

def local_image_to_data_url(image_path):
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'

    # Read and encode the image file
    with open(image_path, "rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read()).decode('utf-8')

    # Construct the data URL
    return f"data:{mime_type};base64,{base64_encoded_data}"

def save_to_cache(key, content, cache_path="test_cache", update_cache=True):
    if update_cache == False:
        return

    cache = {}
    cache_file = os.path.join("data/cache", cache_path, 'cache.json')
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
        with open(cache_file, 'r') as f:
            cache.update(json.load(f))
    else:
        directory = os.path.dirname(cache_file)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(cache_file, 'w') as f:
            json.dump({}, f)
    try:
        json.dumps(content)
    except (TypeError, OverflowError):
        return
    cache[key] = content
    with open(cache_file, 'w') as f:
        json.dump(cache, f)

def stream_response(function_result, function_key, cache_path="test_cache", update_cache = True):
    if inspect.isgenerator(function_result):
        gpt_result = ""
        accumulated = ""
        start_time = time.time()
        for chunk in function_result:
            accumulated += chunk
            if time.time() - start_time >= 0.1:
                yield {"generating": accumulated}
                accumulated = ""
                start_time = time.time()
            gpt_result = gpt_result + chunk
        if accumulated != "":
            yield {"generating": accumulated}
            time.sleep(0.2)
        save_to_cache(key=function_key, content=gpt_result, cache_path=cache_path, update_cache=update_cache)
        yield {"gpt_result": gpt_result}
    else:
        length = len(function_result)
        print_len = 0
        while print_len < length:
            time.sleep(0.2)
            random_num = random.uniform(0.5, 0.9)
            step_len = math.ceil(random_num * generate_step)
            yield {"generating": function_result[print_len:print_len+step_len]}
            print_len = print_len + step_len
        save_to_cache(key=function_key, content=function_result, cache_path=cache_path, update_cache=update_cache)
        time.sleep(0.2)
        yield {"gpt_result": function_result}

def local_image_to_data_url(image_path):
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'

    # Read and encode the image file
    with open(image_path, "rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read()).decode('utf-8')

    # Construct the data URL
    return f"data:{mime_type};base64,{base64_encoded_data}"


def handle_response(response):
    if (isinstance(response, openai.Stream)):
        for chunk in response:
            if len(chunk.choices) > 0:
                choice = chunk.choices[0]
                if hasattr(choice, "delta") and choice.delta != None:
                    chunk_content = choice.delta.content
                    if chunk_content != None:
                        yield chunk_content
                elif hasattr(choice, "messages") and choice.messages != None and len(choice.messages) > 0:
                    chunk_object = choice.messages[0]["delta"]
                    if "content" in chunk_object and chunk_object["content"] != None:
                        yield chunk_object["content"]
    else:
        return "error"

@custom_lru_cache
def gpt4_chat_request(messages, prompt,max_tokens=100, stream=False, cache_path="test_cache", use_cache=True,
                      update_cache=True):

    api_base = os.getenv("OPENAI_API_BASE")
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("OPENAI_API_GPT4_NAME")
    client = openai.OpenAI(api_key=api_key, base_url=api_base)
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=max_tokens,
        stream=stream
    )
    if stream == False:
        return handle_no_stream_response(response)
    else:
        return handle_response(response)


@custom_lru_cache
def gpt3_chat_request(messages, prompt, max_tokens=100, stream=False, cache_path="test_cache", use_cache=True,
                      update_cache=True):
    api_base = os.getenv("OPENAI_API_BASE")
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("OPENAI_API_GPT4_NAME")
    client = openai.OpenAI(api_key=api_key, base_url=api_base)
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=max_tokens,
        stream=stream
    )
    if stream == False:
        return handle_no_stream_response(response)
    else:
        return handle_response(response)
