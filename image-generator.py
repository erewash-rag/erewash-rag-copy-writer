from openai import OpenAI
import base64
import os

def get_from_file(line_num):
    fp = open("local-creds.txt")
    for i, line in enumerate(fp):
        if i == line_num:
            return line.strip('\n')

org_id = os.environ.get('open_ai_org') or get_from_file(0)
project_id = os.environ.get('open_ai_project') or get_from_file(1)
api_key = os.environ.get('open_ai_api_key') or get_from_file(2)

client = OpenAI(
    organization=org_id,
    project=project_id,
    api_key=api_key
)

prompt = """
Create an absurdist satirical cartoon for a news article with the title "Ilkeston Brass Band Resurrected from the Brink of Extinction"
"""

result = client.images.generate(
    model="gpt-image-2",
    prompt=prompt
)

image_base64 = result.data[0].b64_json
image_bytes = base64.b64decode(image_base64)

# Save the image to a file
with open("otter.png", "wb") as f:
    f.write(image_bytes)