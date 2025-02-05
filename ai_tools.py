import openai
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate

from base64 import b64decode
from pathlib import Path
from PIL import Image
from io import BytesIO
import requests
import hashlib
import uuid
import json
from keys import OPENAI_API_KEY, ANTHROPIC_API_KEY, GEN_IMAGES_FOLDER


openai_client = openai.OpenAI(
    api_key=OPENAI_API_KEY
)

gpt_4o_model = ChatOpenAI(
    model="gpt-4o",
    api_key=OPENAI_API_KEY
)

# does not exist
# gpt_o3_mini_model = ChatOpenAI(
#     model="o3-mini",
#     api_key=OPENAI_API_KEY
# )

claude_3_model = ChatAnthropic(
    model="claude-3-opus-20240229",
    api_key=ANTHROPIC_API_KEY
)

# The flashcard_template
flashcard_template = """
You will be provided with three inputs:
1. A "CONTENT_PROMPT".
2. A "HINT_PROMPT".
3. A "NOTES_PROMPT".

Generate a json with three keys: "content", "hint", and "notes".
The returned values of content, hint and notes must be a plain text strings.

- The "content" key should be generated using CONTENT_PROMPT. Make it detailed and informative.
- The "hint" key should be generated using HINT_PROMPT taking your response to CONTENT_PROMPT as context. Make it short, concise and helpful.
- The "notes" key should be generated using NOTES_PROMPT taking your response to CONTENT_PROMPT and HINT_PROMPT as context. Always suggest the relation to other topics or concepts.

Example output:
```json{{
  "content": "useful generated content here",
  "hint": "useful generated hint here",
  "notes": "useful generated notes here"
}}```

Now, use the following inputs and produce the dictionary:
CONTENT_PROMPT: {content_prompt}
HINT_PROMPT: {hint_prompt}
NOTES_PROMPT: {notes_prompt}
"""

# Create the PromptTemplate object
flashcard_prompt_template = PromptTemplate(
    input_variables=["content_prompt", "hint_prompt", "notes_prompt"],
    template=flashcard_template,
)

def generate_card(model=gpt_4o_model, content_prompt="", hint_prompt="", notes_prompt=""):
    prompt = flashcard_prompt_template.invoke({'content_prompt':content_prompt, 'hint_prompt':hint_prompt, 'notes_prompt':notes_prompt})
    response = model.invoke(prompt)
    content = response.content
    content = content.replace("```json\n", "").replace("```", "")
    return json.loads(content)

# Define a template for generating the image prompt
image_prompt_template = """
You are creating an image. The image should visually represent the essence of the following concepts:

- TITLE: {title_prompt}
- CONTENT: {content_prompt}
- HINT: {hint_prompt}
- NOTES: {notes_prompt}
- DESCRIPTION: {description_prompt}

Meta characteristics of the image:
- Image Style: The style (e.g., watercolor, minimalistic, realistic, etc) should align with image details especially with 90% with the passed 'DESCRIPTION' component.
- Color Scheme: The color scheme should align with the content and the image style. Prefer using a color scheme that is visually appealing and engaging.
- Prefer vibrant, colorful images and when possible include a natural element like trees, birds, flowers or animals.
"""

# Create a PromptTemplate object with placeholders for dynamic content
image_prompt = PromptTemplate(
    input_variables=["title_prompt", "content_prompt", "hint_prompt", "notes_prompt", "description_prompt"],
    template=image_prompt_template
)

def prompt_to_filename(prompt, digest_size=16):
  return f"{uuid.uuid4()}-" + hashlib.blake2b(prompt.encode(), digest_size=digest_size).hexdigest() + ".png"

def generate_image(prompts_dict, images_dir=None, model="dall-e-3", response_format="b64_json", open_image=False): # url
  
  if not "description_prompt" in prompts_dict:
    raise ValueError("The 'description_prompt' key is required in the prompts_dict.")
  
  if len(prompts_dict) > 1:
    prompt = image_prompt.invoke(prompts_dict).text
  elif "description_prompt" in prompts_dict:
    prompt = prompts_dict.get("description_prompt")
  else:
    raise ValueError("The 'description_prompt' key is required in the prompts_dict.")
  
  if images_dir is None:
    images_dir = GEN_IMAGES_FOLDER
  
  if not isinstance(images_dir, Path):
    images_dir = Path(images_dir)
  
  images_dir.mkdir(parents=True, exist_ok=True)
  
  response = openai_client.images.generate(
    model=model,
    prompt=prompt,
    n=1,
    size="1024x1024",
    response_format=response_format
  )
  
  image_filename = prompt_to_filename(prompt)
  image_path = images_dir / image_filename
  
  if response_format == "b64_json":
    image_data = response.data[0].b64_json
    image = b64decode(image_data)
    image = Image.open(BytesIO(image))
    image.save(image_path)
  elif response_format == "url":
    image_url = response.data[0].url
    image_response = requests.get(image_url)
    if image_response.status_code == 200:
      with open(image_path, 'wb') as f:
        f.write(image_response.content)
  
  if open_image:
    image.show()
  else:
    return image_filename
  
def generate_action_image(person, action, images_dir=None, prompt_model=gpt_4o_model, open_image=False):
  
  prompt = prompt_model.invoke(f"Create an image-description prompt that combines a {person} doing the following: {action}").content
  return generate_image({'description_prompt':prompt}, images_dir=images_dir, open_image=open_image)
