"""Test which NVIDIA vision models accept image input."""
import base64, io
from openai import OpenAI
from PIL import Image

API_KEY = "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"
BASE_URL = "https://integrate.api.nvidia.com/v1"

# Create a tiny test image (red square)
img = Image.new("RGB", (64, 64), color="red")
buf = io.BytesIO()
img.save(buf, format="PNG")
b64 = base64.b64encode(buf.getvalue()).decode()
data_url = f"data:image/png;base64,{b64}"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

vision_models = [
    "microsoft/phi-3.5-vision-instruct",
    "meta/llama-3.2-11b-vision-instruct",
    "meta/llama-3.2-90b-vision-instruct",
    "microsoft/phi-3-vision-128k-instruct",
    "microsoft/phi-4-multimodal-instruct",
    "nvidia/vila",
    "nvidia/neva-22b",
    "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
    "nvidia/nemotron-nano-12b-v2-vl",
    "google/paligemma",
    "google/gemma-3-27b-it",
    "google/gemma-3-12b-it",
    "google/gemma-3-4b-it",
]

for model in vision_models:
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image briefly in one sentence."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }],
            max_tokens=80,
            timeout=30,
        )
        answer = r.choices[0].message.content.strip()[:100]
        print(f"OK   {model}")
        print(f"     → {answer}")
    except Exception as e:
        err = str(e)[:120]
        print(f"ERR  {model}: {err}")
    print()
