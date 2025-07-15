import json
import pandas as pd
import ast
import importlib
import matplotlib.pyplot as plt
import io
import base64
import seaborn as sns
import time
from components.executor.code_utils import preprocess_code, preprocess_narration_or_code
from components.executor.code_response import CodeExecutorResponse
import os
from concurrent.futures import ThreadPoolExecutor

from components.tool import gpt4_chat_request, gpt3_chat_request, local_image_to_data_url, stream_response


system_prompt = '''You are a professional data analyst who is very good at writing data analysis codes and writing data reports.'''

code_instruction_prompt = '''
Code writing instructions: 
1. DO NOT WRITE ANY CODE TO LOAD DATA. We have loaded the data into a pandas DataFrame "df".
2. The analysis function MUST return a calculated result (pd.DataFrame or pd.Series) to answer the user question. 
3. If you write plotting code, the analysis function must return a matplotlib object (plt). Do not include plt.show(). 
4. For date dtype fields, you MUST use pd.to_datetime(df[<field>], errors='coerce') before you use some functions to process date or time (for example, .dt)
5. Think step by step. For example, consider what data fields and transformations are needed (remember to deal with the date dtype!!!). Please note to use the fields and values that can be obtained from the given dataset for data fields and values.
6. If you generate a chart with data for multiple subjects, the chart should include data for no more than 10 subjects. If more data is available, select only up to 10 subjects randomly or based on specific criteria (e.g., highest values, specific categories).

Your code must fit the following template. 
You only need to modify <import>, <plan> and <code> part. 
Remember to keep the template structure. Remember to keep the analysis function. Remember to write the return statement.
```
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
<import>
# Plan step by step. For example, consider what data fields are needed and then what transformations are needed. 
# <plan>
plt.style.use('seaborn-v0_8') # Specifies the color style for the generated chart. You do not need to specify the colors.
def analysis(df: pd.DataFrame):
    <code>
    return calculated_result, plt # use this line if you include a chart. No additional code beyond this line.
    return calculated result, None # use this line if there is no chart. No additional code beyond this line.
```
'''

narration_inctruction_prompt = '''
The provided 'reference_analysis' format is
{
    "text": "" # the complete origin text in the reference segment
    "data_sentences": [] # the list of data analysis sentences extracted from the text
    "non_data_sentences": [] # the list of other sentences in the text
}

Report writing instructions: 
1. Please imitate the narration writing in "reference_analysis." Use the same tone and narrative perspective.
2. Please first refer to the sentence in the "data_sentences" field in "reference_analysis" for the writing of data analysis statements. 
 Then, if necessary, you can refer to the sentences in "non_data_sentences" to write the background and viewpoint statements, making the text more coherent and complete.
 Please note that the sentence list in 'non_data_sentences' may be empty, at which point you do not need to writing additional viewpoints or background.
 If you have referred to the text in 'non_data_sentences' for writing, please record these sentences you have written.
3. Your narration should reflect the most IMPORTANT data insights in the executed result and can answer the analysis question. 
4. Your narration will follow the "previous_narration" part in the report. 
5. Don't cite the data insights in "reference_analysis." For example, don't write "similar to the increasing trend in (reference_analysis), ...". 
6. The length of the narration should be similar to the reference_analysis. Don't be wordy, BE CONCISE. 
7. Focus on the data facts in the result instead of opinions. 
8. Plan what to write first. 

Your narration must fit the following template. Please keep the special mark format (<plan> and <narration> and <non_data_sentences>). 
```
<plan> 
Write your plan here.
<narration>
Write your narration here. Please imitate the writing style of narration in "reference_analysis." BE CONCISE!
<non_data_sentences>
Write the sentences you wrote with reference to 'non_data_sentences' here, with one sentence per line.
If the 'non_data_sentences' field in 'reference_analysis' is an empty list, return None here.
```
'''

execution_get_code_prompt = f'''

You will be provided with: 
1. "summary_dataset": the summary information of the dataset. "file_name" denotes the file name of my dataset, "field_names" lists all the data field names,  and "fields" includes the information of each data field, including the column name and properties, such as data type, min, max, std, num_unique_values, and samples. 
2. "question": the user question that asks you to analyze the data and get data insights. 
3. "reference_analysis": some narration and visualization (optional) from another data analysis report, which can serve as a reference for generating new analysis. Please note that this report is about a different dataset from the given "summary_dataset." You must check the data fields and patterns based on the "summary_dataset." The "reference_analysis" only serves as an example for generating a new analysis. 
    The provided "reference_analysis" format is
    {{
        "text": "" # the complete origin text in the reference segment
        "data_sentences": [] # the list of data analysis sentences extracted from the text
        "non_data_sentences": [] # the list of other sentences in the text
    }}
    For "reference_analysis", You need to mainly refer to the analysis operations of the sentences in "data_sentences" for code writing, without considering the sentences in "non_data_sentences".

You need to generate the data analysis code based on the information above. 
The return value of your code must be some calculated results (pd.Dataframe or pd.Series) for the user question.  
You may also write code to plot charts. Please use Seaborn or matplotlib.
The plotting code MUST use the right chart type and data encoding. Consider the field types and use them correctly. 
You can refer to the reference_analysis to consider what result you need to calculate and what chart is appropriate. 
\n{code_instruction_prompt}
'''

system_get_analysis_prompt = f'''
The analysis code has been executed. The executed results are provided (may include a chart). 
Given the executed results, you need to decide whether the results are correct, appropriate, and sufficient to write the data report narration (similar to "reference_analysis"). 
Please write the report narration if the results are correct, appropriate, and sufficient. 
\n{narration_inctruction_prompt}

Else, if the results are not correct, appropriate, and sufficient (for example, the code fails, or the chart is not appropriate, or the calculated results are not adequate), 
please re-give the code.
\n{code_instruction_prompt}
'''

def get_globals_dict(code_string, df):
    # Parse the code string into an AST
    tree = ast.parse(code_string)
    # Extract the names of the imported modules and their aliases
    imported_modules = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = importlib.import_module(alias.name)
                imported_modules.append((alias.name, alias.asname, module))
        elif isinstance(node, ast.ImportFrom):
            module = importlib.import_module(node.module)
            for alias in node.names:
                obj = getattr(module, alias.name)
                imported_modules.append(
                    (f"{node.module}.{alias.name}", alias.asname, obj)
                )

    # Import the required modules into a dictionary
    globals_dict = {}
    for module_name, alias, obj in imported_modules:
        if alias:
            globals_dict[alias] = obj
        else:
            globals_dict[module_name.split(".")[-1]] = obj

    ex_dicts = {"pd": pd, "df": df, "plt": plt, "sns": sns}
    globals_dict.update(ex_dicts)
    return globals_dict

def code_executor(code, df=None):
    try:
        ex_locals = get_globals_dict(code, df)
        exec("import matplotlib\nmatplotlib.use('Agg')\nsns.set_style(\"whitegrid\")\n"+code, ex_locals)
        calculated_result = ex_locals["calculated_result"]
        chart = ex_locals["chart"]
        chart_url = None
        base64_data = None
        if plt and chart != None:
            buf = io.BytesIO()
            if plt.gca().get_legend() is not None:
                plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
            if "plt.title('Crime Trend in Los Angeles from 2020 to 2023')\n" not in code:
                plt.tight_layout()
            plt.savefig(buf, format="png", dpi=100)
            buf.seek(0)
            base64_data = base64.b64encode(buf.read()).decode('utf-8')
            chart_url = f"data:image/png;base64,{base64_data}"
            plt.close()
        if isinstance(calculated_result, pd.Series):
            calculated_result = calculated_result.to_frame(name="calculated")
            index_name = calculated_result.index.name if calculated_result.index.name is not None else 'index'
            calculated_result = calculated_result.reset_index().rename(columns={'index': index_name})
        string_result = calculated_result.to_string()
        if not isinstance(calculated_result.index, pd.RangeIndex):
            calculated_result.reset_index(inplace=True)

        return CodeExecutorResponse(
            status=True,
            code = code,
            raster= base64_data,
            url = chart_url,
            calculated_result= string_result,
            ex_locals = ex_locals,
            json_result = calculated_result.to_json(orient="records")
        )
    except Exception as exception_error:
        return CodeExecutorResponse(
            status = False,
            code = code,
            error = str(exception_error),
        )


def stream_execution_get_code(summary_dataset="", report_data={}, prompt=[], use_image=True, force_4 = False, cache_path="test_cache", use_cache = True, update_cache = True):

    if "question" not in report_data:
        return

    question = report_data["question"]
    report_content = report_data["content"]
    user_content = []
    user_content.append({"type": "text", "text": f"\"summary_dataset\": \n{json.dumps(summary_dataset)}"})
    user_content.append({"type": "text", "text": f"\"question\": \n{question}"})
    count = 0
    has_image = False
    if isinstance(report_content, str):
        report_content = json.loads(report_content)
    for item in report_content:
        if item["type"] == "image_path":
            image_url = local_image_to_data_url(image_path=item["image_path"])
            user_content.append({"type": "image_url", "image_url": {"url": image_url}})
            has_image = True
        elif item["type"] == "image_url":
            has_image = True
        elif count == 0 and item["type"] == "text":
            temp = item["text"]
            user_content.append({"type": "text", "text": f"\"reference_analysis\": \n{temp}"})
            count = count + 1
        else:
            user_content.append(item)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": execution_get_code_prompt},
        {"role": "user", "content": user_content},
    ]

    yield {"messages": messages}

    if (has_image != False and use_image == True) or force_4 == True:
        function_result, function_key = gpt4_chat_request(messages=messages, prompt=prompt, max_tokens=1000, stream=True, cache_path=cache_path,use_cache=use_cache, update_cache=update_cache)
    else:
        function_result, function_key = gpt3_chat_request(messages=messages, prompt=prompt, max_tokens=1000, stream=True, cache_path=cache_path,use_cache=use_cache, update_cache=update_cache)
    for temp in stream_response(function_result, function_key, cache_path=cache_path, update_cache=update_cache):
        yield temp


def stream_execution_get_analysis(messages, code_result, report_data, prompt, cache_url = "", use_image = True, force_4 = False, cache_path="test_cache", use_cache = True, update_cache = True):

    if code_result.status == False and len(messages) >= 6:
        messages = messages[:3]

    system_prompt = system_get_analysis_prompt
    gpt_message = { "role": "assistant", "content": f"```{code_result.code}```"}
    code_exe_content = []
    relation = report_data["relation"][0]
    relation_from = relation["fromNode"]
    previous_content_str = ""
    if relation_from != "data":
        relation_content = relation_from["content"]
        for content in relation_content:
            if content["type"] == "text":
                temp = content["text"]
                previous_content_str = previous_content_str + f"{temp}\n"
    else:
        previous_content_str = "No previous narration. This is the beginning of report. "

    reference_analysis_str = ""
    content_list = json.loads(report_data["content"])
    for content in content_list:
        if content["type"] == "text":
            temp = content["text"]
            reference_analysis_str = reference_analysis_str + f"{temp}\n"
    if reference_analysis_str == "":
        reference_analysis_str = "No reference analysis. Please generate new report content text based on the code results. BE CONCISE, BRIEF AND SHORT! Include the most important insights only. "

    has_image = False
    if code_result.url != None and code_result.url != "":
        has_image = True
    if code_result.status == True:
        code_result_prompt = "The code executes successfully. "
        if code_result.calculated_result != None:
            result_str = str(code_result.calculated_result)
            if len(result_str) > 500000:
                code_result_prompt = code_result_prompt + f"Result: The table is too long. Please refer to the chart."
            else:
                code_result_prompt = code_result_prompt + f"Result: \n{code_result.calculated_result}"
        if use_image == True and has_image == True:
            code_result_prompt = code_result_prompt + "\nIt also generates a chart. "
        code_exe_content.append({"type": "text", "text": code_result_prompt})
        if use_image == True and has_image == True:
            code_exe_content.append({"type": "image_url", "image_url": {"url": cache_url}})
        code_exe_content.append({"type": "text", "text": f"reference_analysis: {reference_analysis_str}"})
        code_exe_content.append({"type": "text", "text": f"previous_narration: {previous_content_str}"})
    else:
        yield {"stage": "execute error", "content": [{"type": "error", "text": "code execute error"}]}
        code_result_prompt = f"The code fails. Error message: {code_result.error}"
        code_exe_content.append({"type": "text", "text": code_result_prompt})
        code_exe_content.append({"type": "text", "text": f"reference_analysis: {reference_analysis_str}"})
    system_message = {"role": "system", "content": system_prompt}
    user_message = {"role": "user", "content": code_exe_content}
    messages.append(gpt_message)
    messages.append(system_message)
    prompt.append("execute_system_get_analysis_prompt")
    messages.append(user_message)

    yield {"messages": messages}
    if (has_image != False and use_image == True) or force_4 == True:
        function_result, function_key = gpt4_chat_request(messages=messages, prompt=prompt, max_tokens=1000, stream=True, cache_path=cache_path,use_cache=use_cache, update_cache=update_cache)
    else:
        function_result, function_key = gpt3_chat_request(messages=messages, prompt=prompt, max_tokens=1000, stream=True, cache_path=cache_path,use_cache=use_cache, update_cache=update_cache)
    for temp in stream_response(function_result, function_key, cache_path=cache_path, update_cache=update_cache):
        yield temp


def stream_execute(summary_dataset, df, report_data, use_image=True, force_4=False, cache_path="test_cache",
                   use_cache=True, update_cache=True):

    if "question" not in report_data:
        return
    question = report_data["question"]
    seg_id = str(report_data["relation"][0]['edge']['toId'])
    round_cnt = 0
    messages = []
    code = ""
    prompt = ["execute_system_prompt", "execute_get_code_prompt"]
    code_chunks = stream_execution_get_code(
        summary_dataset=summary_dataset,
        report_data=report_data,
        prompt=prompt,
        use_image=use_image,
        force_4=force_4,
        cache_path=cache_path,
        use_cache=use_cache,
        update_cache=update_cache
    )
    code_begin = 0
    cache_chunk = ""
    for chunk in code_chunks:
        if "messages" in chunk:
            messages = chunk["messages"]
        if "generating" in chunk:
            temp_chunk = chunk["generating"]
            if code_begin == 0:
                cache_chunk = cache_chunk + temp_chunk
                import_index = cache_chunk.find("import ")
                if import_index != -1:
                    code_begin = 1
                    cache_chunk = cache_chunk[import_index:]
                    yield {"round": round_cnt, "stage": "code", "content": [{"type": "code", "code": cache_chunk}]}
            else:
                temp_chunk = temp_chunk.replace("`", "")
                yield {"round": round_cnt, "stage": "code", "content": [{"type": "code", "code": temp_chunk}]}
        if "gpt_result" in chunk:
            code = chunk["gpt_result"]

    code = preprocess_code(code)

    execute_folder_path = "data/cache/selected/report/execute_result"
    if not os.path.exists(execute_folder_path):
        os.makedirs(execute_folder_path)


    code_result = None
    chat_stage = "code"

    while chat_stage == "code":
        code_thread = ThreadPoolExecutor(max_workers=1)
        future = code_thread.submit(code_executor, code, df)
        code_result = future.result()

        if code_result.status == False:
            code_result_content = []
            code_result_content.append({"type": "text", "text": code_result.error})
            code_result_return = {
                "round": round_cnt,
                "stage": "exe",
                "content": code_result_content
            }
            time.sleep(0.5)
            yield code_result_return
            time.sleep(0.5)

            cache_url = ""

        elif len((json.loads(code_result.json_result))) == 0:
            code_result_return = {
                "round": round_cnt,
                "stage": "exe",
                "content": "The values of the field selected by the code do not exist in the actual dataset, so it is not possible to generate a valid chart."
            }
            time.sleep(0.5)
            yield code_result_return
            time.sleep(0.5)

            cache_url = ""

        else:
            code_result_content = []
            content_to_save = []

            code_json_cache = {}
            code_json_cache_file = os.path.join("data/cache", cache_path, 'code_json_cache_file.json')
            if os.path.exists(code_json_cache_file) and os.path.getsize(code_json_cache_file) > 0:
                with open(code_json_cache_file, 'r') as f:
                    code_json_cache = json.load(f)
            else:
                with open(code_json_cache_file, 'w') as f:
                    json.dump({}, f)
            if (update_cache == True):
                code_json_cache[question] = code_result.json_result
                with open(code_json_cache_file, 'w') as f:
                    json.dump(code_json_cache, f)

            col_order = list((json.loads(code_result.json_result))[0].keys())
            code_json_result = {
                "json": code_result.json_result,
                "order": col_order
            }
            code_result_content.append({"type": "table", "table": code_json_result})
            content_to_save.append({"type": "table", "table": code_json_result})

            code_result_return = {
                "stage": "exe",
                "content": code_result_content
            }

            time.sleep(0.5)
            yield code_result_return
            time.sleep(0.5)

            code_result_content = []
            cache_url = code_result.url
            image_url = code_result.url

            code_result_content.append({"type": "image_url", "image_url": image_url})
            content_to_save.append({"type": "image_url", "image_url": image_url})

            code_result_return = {
                "stage": "exe",
                "content": code_result_content
            }
            time.sleep(0.5)
            yield code_result_return
            time.sleep(0.5)


        cache_chunk = ""
        next_begin = "none"
        label_str = ""

        next_chunks = stream_execution_get_analysis(
            messages=messages,
            code_result=code_result,
            report_data=report_data,
            prompt=prompt,
            cache_url=cache_url,
            use_image=use_image,
            force_4=force_4,
            cache_path=cache_path,
            use_cache=use_cache,
            update_cache=update_cache
        )

        for chunk in next_chunks:
            if "messages" in chunk:
                messages = chunk["messages"]
            if "generating" in chunk:
                temp_chunk = chunk["generating"]
                if next_begin == "none":
                    cache_chunk = cache_chunk + temp_chunk
                    import_index = cache_chunk.find("import ")
                    narration_index = cache_chunk.find("<narration>")
                    if import_index != -1:
                        next_begin = "code"
                        chat_stage = "code"
                        yield {"round": round_cnt, "stage": chat_stage,
                               "content": [{"type": next_begin, next_begin: cache_chunk}]}
                    elif narration_index != -1:
                        next_begin = "text"
                        chat_stage = "narration"
                        narration_index = narration_index + 11
                        cache_chunk = cache_chunk[narration_index:]
                        cache_chunk = cache_chunk.lstrip()
                        yield {"round": round_cnt, "stage": chat_stage,
                               "content": [{"type": next_begin, next_begin: cache_chunk}]}
                else:
                    label_index = temp_chunk.find("<")
                    highlight_index = temp_chunk.find("<non_data_sentences>")
                    if label_index != -1 and highlight_index == -1:
                        label_str = temp_chunk[label_index:].rstrip()
                        temp_chunk = temp_chunk[:label_index]
                    elif label_index != -1 and highlight_index != -1:
                        next_begin = "text"
                        if highlight_index != 0:
                            last_chunk = temp_chunk[:highlight_index].rstrip()
                            yield {"round": round_cnt, "stage": chat_stage,
                                   "content": [{"type": next_begin, next_begin: last_chunk}]}
                        highlight_index = highlight_index + 20
                        temp_chunk = temp_chunk[highlight_index:].lstrip()
                        chat_stage = "non_data_sentences"
                    elif label_str != "":
                        label_end_index = temp_chunk.find(">")
                        temp_chunk = temp_chunk[label_end_index+1:].lstrip()
                        chat_stage = "non_data_sentences"
                    yield {"round": round_cnt, "stage": chat_stage,
                           "content": [{"type": next_begin, next_begin: temp_chunk}]}

            if "gpt_result" in chunk:
                next_result = chunk["gpt_result"]

                preprocess_result = preprocess_narration_or_code(next_result)
                if "code" in preprocess_result:
                    chat_stage = "code"
                    code = preprocess_result["code"]
                else:
                    chat_stage = "text"
                    narration = preprocess_result["narration"]

        round_cnt = round_cnt + 1

    used_fields = []
    for field in summary_dataset["field_names"]:
        if field in code:
            used_fields.append(field)
    yield {"round": round_cnt, "stage": "used_fields",
           "content": [{"type": "data field", "data field": used_fields}]}  # mark the end of execution