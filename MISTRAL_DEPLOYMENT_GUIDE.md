

## 🟢 BEGINNER FRIENDLY: Using HuggingFace API {#method-0-api-beginner}

This is the **EASIEST way** - no downloading, no installation hassles!

### Step 1: Create a HuggingFace Account

1. Go to: https://huggingface.co/
2. Click **"Sign Up"**
3. Fill in your details (email, password)
4. Verify your email
5. Done! ✅

### Step 2: Get Your API Token

1. Go to: https://huggingface.co/settings/tokens
2. Click **"New Token"**
3. Fill in:
   - **Name**: `mistral-api-token` (or any name)
   - **Role**: Select **"Read"**
4. Click **"Generate"**
5. **Copy the token** (it looks like: `hf_xxxxxxxxxxxxxxxxxxxxxxxxxx`)
6. Save it somewhere safe! ⚠️

### Step 3: Install the HuggingFace Library

Open terminal and run:

```bash
pip install huggingface-hub requests
```

### Step 4: Create Your First Script

Create a file called `mistral_api_demo.py`:

```python
from huggingface_hub import InferenceClient
import os

# Your HuggingFace token
HF_TOKEN = "hf_YOUR_TOKEN_HERE"  # Replace with your token

# Create client
client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.3",
    token=HF_TOKEN
)

# Ask a question
message = "What is machine learning?"

print(f"You: {message}")
print("Mistral: ", end="", flush=True)

# Get response
response = client.text_generation(message, max_new_tokens=200)
print(response)
```

### Step 5: Run the Script

```bash
python mistral_api_demo.py
```

**Output** (example):
```
You: What is machine learning?
Mistral: Machine learning is a subset of artificial intelligence (AI) that enables 
computers to learn and improve their performance on tasks without being explicitly 
programmed. Instead of following pre-written instructions, ML systems learn patterns 
from data...
```

### Step 6: Create a Chat Application

Create `mistral_api_chat.py`:

```python
from huggingface_hub import InferenceClient

# Your HuggingFace token
HF_TOKEN = "hf_YOUR_TOKEN_HERE"  # Replace with your token!

# Create client
client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.3",
    token=HF_TOKEN
)

# Chat loop
print("=" * 60)
print("Chat with Mistral (Type 'quit' to exit)")
print("=" * 60)

conversation_history = []

while True:
    user_input = input("\nYou: ").strip()
    
    if user_input.lower() == 'quit':
        print("Goodbye!")
        break
    
    if not user_input:
        continue
    
    # Add user message to history
    conversation_history.append({"role": "user", "content": user_input})
    
    # Format for Mistral
    messages = conversation_history
    
    try:
        # Get response
        response = client.text_generation(
            user_input,
            max_new_tokens=256
        )
        
        print(f"\nMistral: {response}")
        
        # Add assistant response to history
        conversation_history.append({"role": "assistant", "content": response})
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure your token is correct and you have internet connection")
```

### Step 7: Using Environment Variables (Safer)

Instead of hardcoding your token, use environment variables:

**On Windows (PowerShell)**:
```powershell
$env:HF_TOKEN = "hf_YOUR_TOKEN_HERE"
```

**On Windows (Command Prompt)**:
```cmd
set HF_TOKEN=hf_YOUR_TOKEN_HERE
```

**On Mac/Linux**:
```bash
export HF_TOKEN=hf_YOUR_TOKEN_HERE
```

Then in your Python script:

```python
import os
from huggingface_hub import InferenceClient

# Get token from environment
HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    print("ERROR: HF_TOKEN environment variable not set!")
    exit(1)

# Create client
client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.3",
    token=HF_TOKEN
)

# Rest of your code...
```

### Step 8: Use in Your Django Application

For your Room Booking system, add to `requirements.txt`:

```txt
huggingface-hub>=0.16.0
requests>=2.28.0
```

Create `booking/mistral_utils.py`:

```python
import os
from huggingface_hub import InferenceClient

class MistralHelper:
    def __init__(self):
        self.token = os.getenv("HF_TOKEN")
        if not self.token:
            raise ValueError("HF_TOKEN environment variable not set")
        
        self.client = InferenceClient(
            model="mistralai/Mistral-7B-Instruct-v0.3",
            token=self.token
        )
    
    def answer_booking_question(self, question):
        """Answer questions about room bookings"""
        prompt = f"""You are a helpful assistant for room booking.
        
User question: {question}

Provide a helpful, concise answer."""
        
        response = self.client.text_generation(
            prompt,
            max_new_tokens=200
        )
        return response
    
    def generate_email_subject(self, room_name, date):
        """Generate booking confirmation subject"""
        prompt = f"Generate a professional email subject for a room booking confirmation for {room_name} on {date}"
        
        response = self.client.text_generation(prompt, max_new_tokens=50)
        return response.strip()

# Usage in Django view:
# from booking.mistral_utils import MistralHelper
# 
# mistral = MistralHelper()
# answer = mistral.answer_booking_question("Can I book the lab for a group presentation?")
```

### API Free Tier Limits

| Feature | Free Tier |
|---------|-----------|
| Requests per month | 30,000 |
| Rate limit | 9 requests/minute |
| Max tokens | 1,000 per request |
| Cost | Free |

### When to Use API Approach

✅ Use API if:
- You're learning
- You want quick setup
- You don't mind internet requirement
- You have light usage

❌ Don't use if:
- You need offline capability
- You have heavy usage needs
- You need instant responses

---

### Minimum Requirements:
- **RAM**: 16GB (8GB minimum, but 16GB recommended)
- **VRAM (GPU Memory)**: 8GB+ for GPU acceleration (optional but recommended)
- **Disk Space**: 20GB free (for model + dependencies)
- **Python**: 3.8 or higher
- **Internet**: Required for first download only

### Recommended Setup:
- **RAM**: 32GB
- **GPU**: NVIDIA card with 8GB+ VRAM (RTX 3060, RTX 4060, A100, etc.)
- **Disk**: SSD with 30GB free space
- **Python**: 3.10 or 3.11

### GPU Support:
- **NVIDIA**: Full support via CUDA
- **AMD**: Partial support via ROCm
- **Mac**: CPU-only (Apple Silicon not optimized)
- **CPU-only**: Works but slower (not recommended for production)

---

## System Requirements (For Local Deployment) {#system-requirements}

This is the **easiest method for beginners** who want to run Mistral **locally** on their machine. It requires the least setup and works cross-platform.

## Deployment Method 1: Using HuggingFace Transformers (Local - Easiest) {#method-1-huggingface-transformers}

Open your terminal and run:

```bash
pip install transformers torch
```

Or if you have a GPU (NVIDIA):
```bash
pip install transformers torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Step 2: Create a Python Script

Create a file called `mistral_demo.py`:

```python
from transformers import pipeline

# Initialize the pipeline (downloads model on first run)
chatbot = pipeline("text-generation", model="mistralai/Mistral-7B-Instruct-v0.3")

# Define your conversation
messages = [
    {"role": "user", "content": "What is machine learning?"}
]

# Generate response
response = chatbot(messages)

# Print the response
print(response[0]['generated_text'])
```

### Step 3: Run the Script

```bash
python mistral_demo.py
```

**First run**: The model will be downloaded (~14GB) - this takes 5-10 minutes.

**Subsequent runs**: Uses cached model - much faster!

### Step 4: Create a Simple Chat Application

```python
from transformers import pipeline

# Initialize chatbot
chatbot = pipeline("text-generation", model="mistralai/Mistral-7B-Instruct-v0.3")

# Simple chat loop
print("Chat with Mistral (type 'quit' to exit)")
print("-" * 50)

while True:
    user_input = input("You: ")
    
    if user_input.lower() == 'quit':
        print("Goodbye!")
        break
    
    # Create message format
    messages = [
        {"role": "user", "content": user_input}
    ]
    
    # Generate response
    response = chatbot(messages, max_length=256)
    
    print(f"Mistral: {response[0]['generated_text']}")
    print("-" * 50)
```

### Advantages:
✅ Easiest to set up
✅ Works on all platforms
✅ Automatically handles model downloading
✅ Good for learning and experimentation

### Disadvantages:
❌ Slower than optimized inference
❌ Higher memory usage
❌ Limited customization options

---

## Deployment Method 2: Using Mistral Inference (Local - Faster) {#method-2-mistral-inference}

This is the **official Mistral method** - faster and more optimized for local deployment.

### Step 1: Install Mistral Inference

```bash
pip install mistral_inference
```

### Step 2: Download the Model

Create a file called `download_model.py`:

```python
from huggingface_hub import snapshot_download
from pathlib import Path

# Create directory for model
mistral_models_path = Path.home().joinpath('mistral_models', '7B-Instruct-v0.3')
mistral_models_path.mkdir(parents=True, exist_ok=True)

# Download model
print("Downloading Mistral-7B-Instruct-v0.3...")
snapshot_download(
    repo_id="mistralai/Mistral-7B-Instruct-v0.3",
    allow_patterns=["params.json", "consolidated.safetensors", "tokenizer.model.v3"],
    local_dir=mistral_models_path
)

print(f"Model downloaded to: {mistral_models_path}")
```

Run it:
```bash
python download_model.py
```

### Step 3: Use the Chat CLI

Once downloaded, use the command-line interface:

```bash
mistral-chat $HOME/mistral_models/7B-Instruct-v0.3 --instruct --max_tokens 256
```

Then type your prompts and press Enter to get responses!

### Step 4: Use Programmatically

Create `mistral_inference_demo.py`:

```python
from mistral_inference.transformer import Transformer
from mistral_inference.generate import generate

from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
from mistral_common.protocol.instruct.messages import UserMessage
from mistral_common.protocol.instruct.request import ChatCompletionRequest

from pathlib import Path

# Path to model
mistral_models_path = Path.home().joinpath('mistral_models', '7B-Instruct-v0.3')

# Load tokenizer and model
print("Loading model...")
tokenizer = MistralTokenizer.from_file(f"{mistral_models_path}/tokenizer.model.v3")
model = Transformer.from_folder(mistral_models_path)

# Create request
completion_request = ChatCompletionRequest(
    messages=[UserMessage(content="Explain Machine Learning to me in a nutshell.")]
)

# Generate tokens
tokens = tokenizer.encode_chat_completion(completion_request).tokens

# Generate response
out_tokens, _ = generate(
    [tokens],
    model,
    max_tokens=64,
    temperature=0.0,
    eos_id=tokenizer.instruct_tokenizer.tokenizer.eos_id
)

# Decode and print
result = tokenizer.instruct_tokenizer.tokenizer.decode(out_tokens[0])
print(result)
```

### Advantages:
✅ Official method - optimized by Mistral
✅ Faster inference speed
✅ CLI tool included
✅ Better control and customization

### Disadvantages:
❌ More setup required
❌ Manual model downloading
❌ Steeper learning curve

---

## Deployment Method 3: Using Ollama (Local - Desktop) {#method-3-ollama}

**Ollama** is the easiest way to run Mistral locally with a simple interface.

### Step 1: Download and Install Ollama

Visit: https://ollama.ai/

- **Windows**: Download and run the installer
- **Mac**: Download and run the installer
- **Linux**: Run the installation script

### Step 2: Pull Mistral Model

Open terminal and run:

```bash
ollama pull mistral
```

This downloads the Mistral-7B model (~4GB quantized version).

### Step 3: Run the Model

```bash
ollama run mistral
```

You can now chat with Mistral in the terminal!

### Step 4: API Access

Ollama exposes a REST API on `localhost:11434`:

```python
import requests
import json

def chat_with_ollama(prompt):
    response = requests.post(
        'http://localhost:11434/api/generate',
        json={
            'model': 'mistral',
            'prompt': prompt,
            'stream': False,
        }
    )
    
    if response.status_code == 200:
        return response.json()['response']
    else:
        return "Error: Could not generate response"

# Test it
result = chat_with_ollama("What is Python?")
print(result)
```

### Advantages:
✅ One-click installation
✅ Simplest to use
✅ Great for beginners
✅ GUI available
✅ Local-first (privacy)

### Disadvantages:
❌ Quantized version (smaller but lower quality)
❌ Limited customization
❌ Less suitable for production

---

## Quick Comparison Table

| Feature | **API (Easiest)** | Transformers | Mistral Inference | Ollama |
|---------|-------------------|--------------|-------------------|--------|
| **Setup Time** | 5 min ⭐⭐⭐⭐⭐ | 15 min ⭐⭐⭐ | 20 min ⭐⭐ | 10 min ⭐⭐⭐⭐ |
| **Downloads** | None ✅ | ~14GB | ~14GB | ~4GB |
| **Easiness** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Speed** | Fast (cloud) | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Memory** | None needed | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Offline** | ❌ | ✅ | ✅ | ✅ |
| **GPU Required** | ❌ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Cost** | Free (limited) | Free | Free | Free |
| **Best For** | **BEGINNERS** | Learning | Production | Desktop |

---

## Quick Comparison Table

| Feature | Transformers | Mistral Inference | Ollama |
|---------|--------------|-------------------|--------|
| Easiness | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Speed | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Memory | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Customization | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Best For | Learning | Production | Desktop |

---

## Integration with Your Room Booking System

Once you have Mistral running, you can integrate it into your system:

### Option A: Chat Assistance
Add an AI chatbot to help users with room booking questions.

### Option B: Natural Language Queries
Allow users to ask for rooms in natural language:
- "I need a meeting room for 5 people tomorrow at 2 PM"
- "Show me available labs with projectors"

### Option C: Policy Assistant
Use it with your policy documents to answer FAQs automatically.

### Option D: Email Automation
Generate booking confirmation emails using Mistral.

---

## Troubleshooting {#troubleshooting}

### Problem: "Out of Memory" Error

**Solution**:
1. Use Ollama (smallest memory footprint)
2. Use smaller model: `mistralai/Mistral-7B`
3. Add more RAM to your system
4. Use quantized model (8-bit or 4-bit)

### Problem: Model Download is Very Slow

**Solution**:
1. Check internet connection
2. Use a download manager with resume capability
3. Try downloading at off-peak hours
4. Consider downloading on a different machine

### Problem: GPU Not Being Used

**Solution for HuggingFace Transformers**:
```python
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")
```

### Problem: "Could not connect to CUDA device"

**Solution**:
1. Install NVIDIA CUDA Toolkit
2. Install cuDNN
3. Verify NVIDIA drivers are up-to-date
4. Run: `pip install torch --upgrade`

### Problem: Model Gives Bad Responses

**Solution**:
1. Adjust temperature (lower = more focused, higher = more creative)
2. Adjust max_tokens
3. Try rephrasing your prompt
4. Use system prompts to guide behavior

---

## Next Steps

### After Installation:

1. **Experiment**: Try different prompts and parameters
2. **Integrate**: Connect to your Django application
3. **Fine-tune**: Train on your custom data if needed
4. **Deploy**: Set up on a server for production use
5. **Monitor**: Track performance and optimize

### Resources:

- Mistral Documentation: https://docs.mistral.ai/
- HuggingFace Transformers: https://huggingface.co/docs/transformers/
- Ollama: https://ollama.ai/
- Model Card: https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3

---

## Important Notes

⚠️ **Model Size**: The full model is ~14GB in memory
⚠️ **First Run**: First execution downloads the model (~5-10 minutes)
⚠️ **GPU Recommended**: CPU-only is slow for production
⚠️ **License**: Apache 2.0 - Free for commercial use

---

## Quick Start Summary

**For Learning (5 minutes) - RECOMMENDED FOR BEGINNERS:**
```bash
# Just install one library
pip install huggingface-hub

# Then copy the API script from Method 0
# No downloads, no GPU needed!
```

**For Local Desktop (10 minutes)**:
```bash
# Download Ollama from ollama.ai
ollama run mistral
```

**For Learning Locally (15 minutes)**:
```bash
pip install transformers torch
# Then run the simple Python script from Method 1
```

**For Production (20 minutes)**:
```bash
pip install mistral_inference huggingface_hub
# Then run download and inference scripts from Method 2
