import json
import base64
import os.path
import re

def convert(md_path: str, folder_path: str) -> dict:
    def encode_image(image_path: str) -> str:
        with open(image_path, 'rb') as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    
    li = []

    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    li.append({
        'type': 'header',
        'level': 1,
        'content': lines[0][2:].strip(),
    })
    i = 2

    paragraph = []

    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('#'):
            level = len(line.split(' ')[0])
            if paragraph:
                li.append({
                    'type': 'paragraph',
                    'content': ' '.join(paragraph),
                })
                paragraph = []
            level = len(line.split(' ')[0])
            content = line[level+1:].strip()
            li.append({
                'type': 'header',
                'level': level,
                'content': content,
            })

        elif line.startswith('!['):
            if paragraph:
                li.append({
                    'type': 'paragraph',
                    'content': ' '.join(paragraph),
                })
                paragraph = []
            image_path = re.search(r'\((.*?)\)', line).group(1)[2:]
            full_image_path = os.path.join(folder_path, image_path)
            encoded_image = encode_image(full_image_path)
            li.append({
                'type': 'image',
                'content': encoded_image,
            })

        elif line:
            if len(paragraph) != 0:
                paragraph.append('\n')
            paragraph.append(line)
        
        else:
            if paragraph:
                li.append({
                    'type': 'paragraph',
                    'content': ' '.join(paragraph),
                })
                paragraph = []

        i += 1

    if paragraph:
        li.append({
            'type': 'paragraph',
            'content': ' '.join(paragraph),
        })

    return li
