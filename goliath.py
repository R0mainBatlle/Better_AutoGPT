from openai import OpenAI
import os
from dotenv import load_dotenv
# Initialize the client with your API key and MakeHub base URL
load_dotenv()

client = OpenAI(
    api_key=os.getenv("MAKEHUB_API_KEY"),
    base_url="https://api.makehub.ai/v1"
)

# Use the API as you would with OpenAI
completion = client.chat.completions.create(
    model="meta/Llama-3.3-70B-Instruct-fp16",
    messages=[
        {"role": "user", "content": "Hello!"},
        {"role": "system", "content": "You are a helpful assistant"},
    ]
)

print(completion.choices[0].message.content)