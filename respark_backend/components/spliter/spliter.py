import copy
import json
import os.path

from components.tool import gpt4_chat_request, gpt3_chat_request, parse_single_stage, parse_final_result, find_outer_braces
import re

match_prompt = """
You are a renowned expert in data analysis and chart-text correlation tasks.
Your task is to determine whether the given text is related to either of the given charts, or none.
The input includes (1) a paragraph of text and (2) one or two charts (provided as images).

# Task Details
- The text may contain data analysis statements (e.g., statistical results, trends) and non-analytical statements (eg. background, opinions). Focus only on the data analysis statements.
- Data analysis statements are sentences that describe specific data, statistical information, or results derived from data analysis operations.
- Your goal is to determine which chart the data analysis statements in the text are related to or confirm that none are related. Provide corresponding reasons.

# Guidelines
- Relationships between text and charts may include direct reference to information in the charts or implicit connections (e.g., calculated metrics like "death rate" derived from "number of deaths").
- Pay attention to the analysis of the chart's title, axis labels, scales, and specific content.

# Output Format
Return the result in the following JSON format:
{
   "chart_relied_on": "chart_1" or "chart_2" or "", # "chart_1" if the text is related to the first chart, "chart_2" if the text is related to the second chart, "" if  the text is not related to any chart. Note: the sequence number of the returned chart cannot be greater than the number of charts.
   "reason": "", # the reason why the data analysis statements in the text is related to the chart
}
"""

classify_prompt = '''
You are a renowned expert in data analysis and text classification.
Your task is to distinguish whether a given text segment contains **data analysis**. 

# Definitions: What Qualifies as Data Analysis
A text segment is classified as containing **data analysis** if it meets **any** of the following criteria:
1. Specific Data Reference: The segment includes specific data, figures or metrics (e.g., statistical values, percentages) and describes data processing steps or calculatons.
2. Analysis Methods and Outcomes: The segment explicitly describes analytical operations performed on the data, including methods and results.

# Exclusions: What Does Not Qualify as Data Analysis
The following types of text segments are **not** classified as containing data analysis if it:
1. Lacks Data Details: Focuses on background context, opinions, or methods without specific data, figure, statistical values or data processing steps (e.g., "sales growth was driven by policy support", "we used regression analysis to predict future trends").


# Task Instructions
1. Input: You will receive:
- A list of all text segments in a report.
- A subset of segments requiring classification (referred to as the "unmatched segments list").

2. Processing Steps:
- For each segment in the unmatched segments list, determine whether it contains data analysis based on the definitions and exclusions above.
- Provide a clear explanation for your classification.
- Create a concise summary of the segment (max 20 words) that serves as a title for its content.

3. Output Format:
Process the segments in the order they are provided and return the results in the following JSON format:
[
    {
        "text": "The original text segment",
        "has_data_analysis": true/false, 
        "reason": "Explanation of why the text is classified as containing or not containing data analysis",
        "summary": "A concise summary of the segment text (max 20 words)"
    }
]
'''

highlight_prompt = '''
You are a renowned expert in data analysis and report content categorization.
Your task is to classify each sentence in a data report segment as either:
- "data_analysis": Sentences related to data analysis, e.g., discussing data, statistics, or chart patterns.
- "non_data_analysis": Sentences unrelated to data analysis, e.g., providing background information. 

# Classification Rules
A sentence should be tagged as "data_analysis" if it meets any of the following conditions:
1. It mentions relevant information about the analyzed data (e.g., data fields, ranges, or dataset overview).
2. It mentions chart-specific details (e.g., chart titles, x-axis or y-axis labels, scales).
3. It contains data statistics, such as specific numbers or numerical summaries.
4. It describe patterns in the data or charts (e.g., trends, extremes, or correlations).
5. It includes conclusions or inferences drawn from the data analysis (e.g., what kind of movies increase the most). 

If a sentence does not meet any of the above conditions, classify it as "non_data_analysis".
Typically, "non_data_analysis" sentences provide contextual or background information, such as descriptions of regional policies in a report analyzing COVID-19 infection rates.

# Input and Output
You will process a report segment and classify each sentence. 
Please note that a segment may not contain "non_data_analysis" sentences. 
Return the results in the following JSON format:
[
    {
        "text": "The original text of the sentence",
        "tag": "non_data_analysis" | "data_analysis",
        "reason": "The reason for assigning this tag"
    }
]
'''

logic_prompt = '''
# Background
A data report consists of multiple report segments, each presenting the results of one round of data analysis. A segment typically contains textual narrations and charts.

Each report segment revolves around an analytical objective, which is derived from:
1. An initial analysis objective: Posed directly from the dataset or
2. A logical relationship with a prior segment: The current segment logically connects to a prior segment (Note: The logical relationship pertains to the connection between segments, not the internal analysis process within a segment). 

## Types of Logical Relationships Between Segments
Specifically, The analytical objective of a new segment can be formed based on one of the following logical relationships:
1. initial: An independent analytical objective directly derived from the dataset.
2. similarity: Explores a logically parallel objective by modifying some conditions. Example: The prior segment analyzes the trend of Product A, and this segment analyzes the trend of Product B.
3. contrast: Investigates contradictions or differences. Example: The prior segment finds increasing sales for Product A, and this segment explores, "Which products have decreasing sales?"
4. elaboration: Narrows down to a smaller scope of the prior segment. Typically, it adds conditions for more detailed analysis. Example: the prior segment provides an overview, this one analyzes specific details.
5. generalization: Broadens the scope by expanding to a wider range of data. Typically, it changes to a wider time period or reduce some conditions to conduct a more general analysis. This is the opposite of elaboration.
6. temporal: Focuses on the same question as the prior segment but shifts the analysis to a different time period.
7. cause: Investigates the cause of the findings in the prior segment.
8. effect: Explores the effects or consequences of the findings in the prior segment.

# Task
Your task is to analyze a given segment and determine the following:
1. Analytical operation: The data processing steps or computations performed in this segment.
2. Analytical objective: The main question this segment aims to address.
3. Logical relationships: How the analytical objective relates to the prior segment, or whether it is an initial objective directly derived from the dataset. Provide all plausible relationships with their strengths. 

## Instructions
1. Pay attention to the data analysis sentences and the chart image (if present) in the given segment. 
2. Follow these steps: 
- Step 1. Identify the analytical operations performed in this segment.
- Step 2. Formulate the analytical objective based on these operations.
  - Write the analytical objective as a concise question that covers the entire report segment. 
  - Include necessary details like time ranges or conditions relevant to the analysis.
- Step 3. Evaluate the logical relationship between this segment's analytical objective and the prior segments, or classify it as an "initial" segment.
  - Assess whether the segment logically builds on prior segments.
  - If no strong relationship exists with prior segments, classify it as an initial segment.

## Input Format
You will receive:
- Prior Segments List: A list of previously analyzed segments, formatted as follows:
[
    {
        "id": , // Segment ID
        "text": "", // Text content of the segment
        "data_sentences": [], // Data analysis sentences in the segment
        "analysis question": "", // Analytical objective of this segment
        "analysis operation": "",  // Analytical operations performed (e.g., "calculate the number of movies each year")
        "logic": "", // Logical relationship type (e.g., "initial", "cause")
        "formed from": , // ID of the prior segment forming the basis for this segment, or -1 if "initial"
        "logic description": "" // Explanation of the logical relationship
    },
    ...
]
- Segment to Be Analyzed: Details of the segment to be analyzed, formatted as follows:
{
    "id": , // Segment ID
    "text": "", // Text content of the segment
    "data_sentences": [], // Data analysis sentences in the segment
    "image": True/False, // Indicates whether the segment contains a chart image. If the segment includes a chart, the chart image will be provided below. 
}

## Output Format
Your result should follow this JSON JSON format:
{
    "id": , // Segment ID
    "analysis operation": "", // Analytical operations performed (e.g., "calculate the number of movies each year")
    "analysis operation reason": "", # Reason for identifying the analytical operations
    "analysis question": "", // the analysis objective of this segment (e.g., "How the number of movies has changed over time?")
    "analysis question reason": "", # Reason for identifying the analytical objective
    "logic candidates": [ 
        {
            "logic": "", // Logical relationship type (e.g., "initial", "cause")
            "formed from": , // ID of the related prior segment, or -1 if "initial"
            "strength": "", // Relationship strength: "strong", "moderate", or "weak"
            "reason": "" // Explanation for the relationship
        },
        ...
    ]
}

### Input and Output Example:
Prior Segments List: 
[
    {
        "id": 0,
        "text": "The number of movies has increased from 2021 to 2023. Specifically, 2023 has had the most movies released, a 10% increase over 2022. ",
        "data_sentences": ["The number of movies has increased from 2021 to 2023. Specifically, 2023 has had the most movies released, a 10% increase over 2022. "]
        "analysis question": "How the number of movies has changed from 2021 to 2023?",
        "analysis operation": "calculate the number of movies each year",
        "logic": "initial",
        "formed from": "-1",
        "logic description": "This segment is the first one and focuses on an independent objective derived directly from the data."
    },
],
The given segment to be analysed:
{
    "id": 1,
    "text": "This is mainly due to the surge in the number of action movies in 2023. Action movies increased 40% in 2023, making the number of movies a big increase.",
    "data_sentences": ["This is mainly due to the surge in the number of action movies in 2023. Action movies increased 40% in 2023, making the number of movies a big increase."],
    "image": true // a line chart showing the trend of the number of each movie over time
}

Output:
{
    "id": "1",
    "analysis operation": "calculate the number of movies for each genre each year",
    "analysis operation reason": "The text and data sentences imply an analysis of genre-based contributions to the total number of movies, and a line chart showing the trend of the number of each movie over time is drawn in the chart image.",
    "analysis question": "What movie genres cause the highest number of movies in 2023?",
    "analysis question reason": "The text and data sentences suggest an inquiry into the drivers of the trend identified in the prior segment.",
    "logic candidates": [
        {
            "logic": "cause",
            "formed from": 0,
            "strength": "strong",
            "reason": "The segment explores the cause of the trend identified in the previous segment."
        },
        {
            "logic": "initial",
            "formed from": -1,
            "strength": "moderate",
            "reason": "The focus on genres could also be seen as an independent analysis objective."
        }
    ]
}
'''

get_fields_prompt = """
You are a renowned expert in data analysis.
Based on the content of a given report, your task is to infer the structure of the underlying dataset that was analyzed. Identify only the most essential and relevant data fields used for the analysis, without including unnecessary details. Focus on providing the most accurate and concise fields that directly correspond to the report's content.
For example, in a report analyzing average sleep time across different genders and age groups, the dataset may include only the following fields: gender, age, and sleep time.
Output Format:
{
   "data_description": "",  # A brief description of the dataset based on the report's content
   "data_fields": [  # List of essential and relevant data fields
      {
         "field_name": "",  # The name of the data field
         "description": ""  # A brief description of what this field represents
      }
   ]
}
"""


def get_match(report_data, has_image, prompt=['split_match_prompt'], use_image=True, force_4=False, cache_path="case1_cache", use_cache=True,
              update_cache=True):
    '''

    input: report_data: {
        'report_content':[
            {
                'type': 'header'/'image'/'paragraph',
                'content':,
                'children':[],
            }
        ],
        ...
    }
    output:segments: [
            {
                'id':
                'match_type': 'matched'/'unmatched',
                'image_url':
                'text':[]
            }
        ]
    '''

    def gpt_get_match(paragraph, images, prompt, has_image, use_image=True, force_4=False, cache_path="case1_cache", use_cache=True, update_cache=True):
        '''
        output:img_url
        '''
        user_content = []
        user_content.append({"type": "text", "text": "paragraph and images to be matched:"})
        user_content.append({"type": "text", "text": paragraph})
        img_urls = []
        if images['up'] != '':
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{images['up']}"}})
            img_urls.append(images['up'])
        if images['down'] != '':
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{images['down']}"}})
            img_urls.append(images['down'])
        messages = [
            {"role": "system", "content": match_prompt},
            {"role": "user", "content": user_content},
        ]
        if (has_image != False and use_image == True) or force_4 == True:
            function_result = gpt4_chat_request(messages=messages, prompt=prompt, max_tokens=4000, stream=False,
                                                cache_path=cache_path, use_cache=use_cache,
                                                update_cache=update_cache)
        else:
            function_result = gpt3_chat_request(messages=messages, prompt=prompt, max_tokens=4000, stream=False,
                                                cache_path=cache_path, use_cache=use_cache,
                                                update_cache=update_cache)

        function_result = function_result[0]
        match_pos = ""
        result = parse_final_result(function_result, 'chart_relied_on')
        if "chart_relied_on" not in result:
            result = parse_final_result(function_result, 'image_relied_on')
            match_pos = result['image_relied_on']
        else:
            match_pos = result['chart_relied_on']
        if match_pos != "":
            match_index = int(match_pos.split("_")[1]) - 1
            return img_urls[match_index]
        else:
            return ""

    report_content = report_data["report_content"]
    segments = {}
    images = {'up': '', 'down': ''}
    id = 0

    i = 0
    level = 0
    child_lists = []
    while i < len(report_content):
        type = report_content[i]['type']
        content = report_content[i]['content']

        if type == 'paragraph':
            accu_para = []
            accu_para.append(content)
            for j in range(i + 1, len(report_content)):
                type_2 = report_content[j]['type']
                content_2 = report_content[j]['content']
                if type_2 == 'image':
                    images['down'] = content_2
                    break
                elif type_2 == 'paragraph':
                    accu_para.append(content_2)
                elif type_2 == 'header':
                    break

            images_copy = copy.deepcopy(images)

            if len(accu_para) != 0:
                i += len(accu_para) - 1

            if images['up'] != '' or images['down'] != '':
                up_match_list = []
                down_match_list = []
                unmatch_list = []
                for para_item in accu_para:
                    if images['up'] == '' and images['down'] == '':
                        unmatch_list.append(para_item)
                    else:
                        match_url = gpt_get_match(para_item, images, prompt=prompt, has_image=has_image, use_image=use_image,
                                                  force_4=force_4, cache_path=cache_path, use_cache=use_cache,
                                                  update_cache=update_cache)
                        if match_url != '':

                            if match_url == images['down']:
                                down_match_list.append(para_item)
                                if images['up'] != '':
                                    images['up'] = ''
                            elif match_url == images['up']:
                                up_match_list.append(para_item)

                        else:
                            if images['up'] == '':
                                for wrong_item in down_match_list:
                                    unmatch_list.append(wrong_item)
                                down_match_list = []
                            unmatch_list.append(para_item)
                            images['up'] = ''

                if len(up_match_list) != 0:
                    segments[images_copy['up']]['text'] += up_match_list

                if (len(unmatch_list) != 0):
                    for para_item in unmatch_list:
                        if para_item in segments:
                            segments[para_item]['id'].append(id)
                        else:
                            segments[para_item] = {"id": [id], "match_type": 'unmatched', }
                        for l in range(level):
                            child_lists[l].append(id)
                        id += 1

                if images_copy['down'] != '' and images_copy['down'] not in segments:
                    segments[images_copy['down']] = {
                        "id": id,
                        "match_type": 'matched',
                        'text': []
                    }
                    for l in range(level):
                        child_lists[l].append(id)
                    id += 1
                if len(down_match_list) != 0:
                    segments[images_copy['down']]['text'] += down_match_list


            else:
                for para_item in accu_para:
                    if para_item in segments:
                        segments[para_item]['id'].append(id)
                    else:
                        segments[para_item] = {"id": [id], "match_type": 'unmatched', }
                    for l in range(level):
                        child_lists[l].append(id)
                    id += 1

        elif type == 'image':
            images['up'] = content
            if content not in segments:
                segments[content] = {
                    "id": id,
                    "match_type": 'matched',
                }
                segments[content]['text'] = []
                for l in range(level):
                    child_lists[l].append(id)
                id += 1

        elif type == 'header':
            now_level = report_content[i]['level']
            if (now_level <= level):
                for l in range(now_level - 1, level):
                    child_lists.pop()
            child_lists.append([])
            level = now_level

            if content in segments:
                segments[content]['id'].append(id)
            else:
                segments[content] = {
                    "id": [id],
                    "match_type": 'header',
                    'children_nodes': child_lists[level - 1]
                }
            for l in range(level - 1):
                child_lists[l].append(id)
            id += 1
            images = {'up': '', 'down': ''}

        i += 1

    match_result = [0] * id
    for key, value in segments.items():
        if value['match_type'] == 'matched':
            i = value['id']
            match_result[i] = {'id': i, 'match_type': 'matched', 'image_url': key, 'text': value['text']}
        elif value['match_type'] == 'unmatched':
            ilist = value['id']
            for i in ilist:
                match_result[i] = {'id': i, 'match_type': "unmatched", 'text': [key]}
        else:
            ilist = value['id']
            for i in ilist:
                match_result[i] = {'id': i, 'match_type': "header", 'text': [key],'children_nodes': value['children_nodes']}
    return match_result

def get_classify(all_segments, unmatched_data, has_image, prompt=['split_classify_prompt'], use_image=True, force_4=False,
                 cache_path="case1_cache", use_cache=True, update_cache=True):

    user_content = []
    user_content.append({"type": "text", "text": f"\"all segments in the report\": \n{json.dumps(all_segments)}"})
    user_content.append({"type": "text", "text": f"\"unmatched segments list\": \n{json.dumps(unmatched_data)}"})
    messages = [
        {"role": "system", "content": classify_prompt},
        {"role": "user", "content": user_content}
    ]

    if (has_image != False and use_image == True) or force_4 == True:
        function_result = gpt4_chat_request(messages=messages, prompt=prompt, max_tokens=4000, stream=False,
                                            cache_path=cache_path, use_cache=use_cache,
                                            update_cache=update_cache)
    else:
        function_result = gpt3_chat_request(messages=messages, prompt=prompt, max_tokens=4000, stream=False,
                                            cache_path=cache_path, use_cache=use_cache,
                                            update_cache=update_cache)

    function_result = function_result[0]

    pattern = re.compile(r'\[[^]]*\]')
    match = pattern.search(function_result)
    if match:
        result = json.loads(match.group())
    else:
        result = ""

    return result

def get_highlight(data_segments, has_image, prompt=['split_highlight_prompt'], use_image=True, force_4=False,
                  cache_path="case1_cache", use_cache=True, update_cache=True):
    def gpt_highlight(text, has_image, prompt, use_image=True, force_4=False,
                  cache_path="case1_cache", use_cache=True, update_cache=True):
        user_content = []
        user_content.append({"type": "text", "text": f"\"the report paragraph\": \n{json.dumps(text)}"})

        messages = [
            {"role": "system", "content": highlight_prompt},
            {"role": "user", "content": user_content}
        ]
        function_result = gpt4_chat_request(messages=messages, prompt=prompt, max_tokens=2000, stream=False,
                                                cache_path=cache_path, use_cache=use_cache,
                                                update_cache=update_cache)

        function_result = function_result[0]
        pattern = re.compile(r'\[[^]]*\]')
        match = pattern.search(function_result)
        if match:
            result = json.loads(match.group())
        else:
            result = ""

        return result

    for seg in data_segments:
        text = ""
        for t in seg['text']:
            text += t

        highlight_result = gpt_highlight(text, has_image=has_image, prompt=prompt, use_image=use_image,
                                                  force_4=force_4, cache_path=cache_path, use_cache=use_cache,
                                                  update_cache=update_cache)

        non_data_sentences = []
        data_sentences = []
        for s in highlight_result:
            if s["tag"] == "data_analysis":
                data_sentences.append({
                    "text": s["text"],
                    "reason": s["reason"]
                })
            elif s["tag"] == "non_data_analysis":
                non_data_sentences.append({
                    "text": s["text"],
                    "reason": s["reason"]
                })
        seg['non_data_sentences'] = non_data_sentences
        seg['data_sentences'] = data_sentences

    return data_segments


def get_logic(report_data, segments_data, has_image, prompt=['split_logic_prompt'], use_image=True, force_4=False, cache_path="test_cache",
                use_cache=True, update_cache=True):
    summary_dataset = report_data["summary_data"]

    for i in range(len(segments_data)):
        if segments_data[i]['match_type'] == 'header':
            continue

        segments_to_send = []
        seg_list = segments_data[:i]
        image_url = ""

        for seg in seg_list:
            if (seg['match_type'] == 'header'):
                continue
            obj = copy.deepcopy(seg)
            del obj["match_type"]
            del obj["non_data_sentences"]
            if 'image_url' in seg:
                del obj["image_url"]
            segments_to_send.append(obj)

        segment_todo = {
            "id": segments_data[i]['id'],
            "text": segments_data[i]['text'],
        }
        if 'image_url' in segments_data[i]:
            segment_todo['image'] = True
            image_url = segments_data[i]['image_url']
        else:
            segment_todo['image'] = False

        messages = [
            {"role": "system", "content": logic_prompt},
        ]


        user_content = []
        user_content.append({"type": "text",
                             "text": f"\"the segments before that segment in the report\": \n{json.dumps(segments_to_send)}"})
        user_content.append(
            {"type": "text", "text": f"\"the segment that needs to be analysed\": \n{json.dumps(segment_todo)}"})

        if image_url != "":
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_url}"}})

        messages.append({"role": "user", "content": user_content})

        if (has_image != False and use_image == True) or force_4 == True:
            function_result = gpt4_chat_request(messages=messages, prompt=prompt, max_tokens=4000, stream=False,
                                                cache_path=cache_path, use_cache=use_cache,
                                                update_cache=update_cache)
        else:
            function_result = gpt3_chat_request(messages=messages, prompt=prompt, max_tokens=4000, stream=False,
                                                cache_path=cache_path, use_cache=use_cache,
                                                update_cache=update_cache)

        function_result = function_result[0]
        result = json.loads(find_outer_braces(function_result))

        segments_data[i]['analysis question'] = result['analysis question']
        segments_data[i]['analysis operation'] = result['analysis operation']
        segments_data[i]['analysis question description'] = result['analysis question reason']
        segments_data[i]['analysis operation description'] = result['analysis operation reason']

        if "formed from" not in result:
            logic_candidates = result['logic candidates']
            strength_mapping = {"weak": 1, "moderate": 2, "strong": 3}
            best_candidate = max(
                logic_candidates,
                key=lambda candidate: (strength_mapping[candidate["strength"]], int(candidate["formed from"]))
            )
            segments_data[i]['logic'] = best_candidate['logic']
            segments_data[i]['formed from'] = int(best_candidate['formed from'])
            segments_data[i]['logic description'] = best_candidate['reason']
            segments_data[i]['logic strength'] = best_candidate['strength']
        else:
            segments_data[i]['logic'] = result['logic']
            segments_data[i]['formed from'] = int(result['formed from'])
            segments_data[i]['logic description'] = result['logic reason']
            segments_data[i]['logic strength'] = "moderate"
    return segments_data

def get_fields(all_segments, has_image, prompt=['get_fields_prompt'], use_image=True, force_4=False,
                 cache_path="case1_cache", use_cache=True, update_cache=True):
    '''

    input: report_data
    output:
        [
            {
                'id':
                'match_type': 'matched'/'analysis_without_img'/'background'/'opinion',
                'image_url':
                'text':[]
            }
        ]
    '''
    user_content = []
    user_content.append({"type": "text", "text": f"\"The report\": \n{json.dumps(all_segments)}"})
    messages = [
        {"role": "system", "content": get_fields_prompt},
        {"role": "user", "content": user_content}
    ]
    function_result = gpt3_chat_request(messages=messages, prompt=prompt, max_tokens=4000, stream=False,
                                        cache_path=cache_path, use_cache=use_cache,
                                        update_cache=update_cache)

    function_result = function_result[0]

    pattern = re.compile(r'\[[^]]*\]')
    match = pattern.search(function_result)
    if match:
        result = json.loads(match.group())
    else:
        result = ""

    return result

def split(report_data, folder_path, first_upload=True, use_image=True, force_4=False, cache_path="test_cache", use_cache=True, update_cache=True):
    '''
    report_data: {
        'summary_data':
        'report_content':[
            {
                'type': 'header'/'image'/'paragraph',
                'content':,
                'children':,
            }
        ],
        ...
    }
    '''

    has_image = True
    if first_upload:
        match_result = get_match(report_data=report_data, has_image=has_image, use_image=use_image, force_4=force_4,
                                            cache_path=cache_path, use_cache=use_cache, update_cache=update_cache)
        segments_data = match_result

        unmatched_data = []
        unmatched_id = []
        for item in segments_data:
            if (item['match_type'] == 'unmatched'):
                unmatched_data += item['text']
                unmatched_id.append(item['id'])

        unmatched_data_list = [unmatched_data[i:i + 10] for i in range(0, len(unmatched_data), 10)]

        if len(unmatched_id) > 0:
            all_segments = []
            for segment in segments_data:
                all_segments += segment['text']
            classify_result = []
            for ud in unmatched_data_list:
                classify_middle_result = get_classify(all_segments=all_segments, unmatched_data=ud, has_image=has_image, use_image=use_image, force_4=force_4,
                                         cache_path=cache_path, use_cache=use_cache, update_cache=update_cache)
                classify_result += classify_middle_result

            for i in range(len(classify_result)):
                if classify_result[i]['has_data_analysis'] == True:
                    segments_data[unmatched_id[i]]['match_type'] = "data analysis"
                else:
                    segments_data[unmatched_id[i]]['summary'] = [classify_result[i]['summary']]
                segments_data[unmatched_id[i]]['match description'] = classify_result[i]['reason']


        segment_logic = []
        logic_id = []
        for item in segments_data:
            if (item['match_type'] == 'matched' or item['match_type'] == 'data analysis'):
                segment_logic.append(item)
                logic_id.append(item['id'])
        get_highlight(data_segments=segment_logic, has_image=has_image, use_image=use_image, force_4=force_4,
                      cache_path=cache_path, use_cache=use_cache, update_cache=update_cache)

        get_logic(report_data=report_data, segments_data=segment_logic, has_image=has_image, use_image=use_image,
                  force_4=force_4,
                  cache_path=cache_path, use_cache=use_cache, update_cache=update_cache)

        with open(os.path.join(folder_path, "split_result.json"), "w") as file:
            json.dump(segments_data, file, indent=4)


        with open(os.path.join(folder_path, "structure_list.json"), "r", encoding="utf-8") as f:
            reports_list = json.load(f)

        segments_without_image = []
        for seg in reports_list:
            if seg["type"] != "image":
                segments_without_image.append(seg)
        get_fields_result = get_fields(segments_without_image, has_image=False)
        with open(os.path.join(folder_path, "predict_fields.json"), "w", encoding="utf-8") as f:
            json.dump(get_fields_result, f, ensure_ascii=False, indent=4)

    else:
        with open(os.path.join(folder_path, "split_result.json"), "r") as file:
            segments_data = json.load(file)


    return {"stage": "split_result", "content": [{"type": "text", "text": json.dumps(segments_data)}]}