import base64
from mimetypes import guess_type
import re


def local_image_to_data_url(image_path):
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'

        # Read and encode the image file
    with open(image_path, "rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read()).decode('utf-8')

    # Construct the data URL
    return f"data:{mime_type};base64,{base64_encoded_data}"


def preprocess_code(code: str) -> str:
    code = code.replace("<imports>", "")
    code = code.replace("<plan>", "")
    code = code.replace("<code>", "")

    if "```" in code:
        pattern = r"```(?:\w+\n)?([\s\S]+?)```"
        matches = re.findall(pattern, code)
        if matches:
            code = matches[0]
    return_pattern = r'^.*?^\s*return.*$'
    match = re.search(return_pattern, code, re.S | re.M)
    if match:
        code1 = match.group(0)
        code1 = code1.rstrip()
    code = code1

    code = code.replace("```", "")
    code = code + "\ncalculated_result, chart = analysis(df)"
    return code


def preprocess_narration(narration: str) -> str:
    start = narration.find("<narration>")
    if start != -1:
        start += len("<narration>")
        narration = narration[start:]

    narration = narration.replace("<plan>", "")
    narration = narration.replace("<narration>", "")

    if "```" in narration:
        pattern = r"```(?:\w+\n)?([\s\S]+?)```"
        matches = re.findall(pattern, narration)
        if matches:
            narration = matches[0]

    narration = narration.replace("```", "")
    narration = narration.strip()
    return narration


def preprocess_narration_or_code(return_string: str) -> str:
    if "import " in return_string:
        code = preprocess_code(return_string)
        return {"code": code}
    else:
        narration = preprocess_narration(return_string)
        return {"narration": narration}