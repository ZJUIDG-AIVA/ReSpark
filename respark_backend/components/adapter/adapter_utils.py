import re

def preprocess_json_result(narration: str) -> str:    
    if "```" in narration:
        pattern = r"```(?:\w+\n)?([\s\S]+?)```"
        matches = re.findall(pattern, narration)
        if matches:
            narration = matches[0]

    narration = narration.replace("```", "")
    narration = narration.strip()
    return narration