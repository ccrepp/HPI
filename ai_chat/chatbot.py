from llama_cpp import Llama
import os
os.environ["LLAMA_CPP_LOG_LEVEL"] = "ERROR"

# Load the model
llm = Llama(
    model_path="/home/pi/Desktop/ai_chat/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
    n_ctx=128,
    n_threads=1,
    n_batch=16
)

# Plant-based system prompt
def plant_prompt(user_input):
    return (
        "<|system|>You are a friendly assistant who gives helpful plant based knowledge.<|end|>\n"
        f"<|user|>{user_input}<|end|>\n"
        "<|assistant|>"
    )

# REPL loop
while True:
    question = input("You: ")
    if question.lower() in ['exit', 'quit']:
        break

    prompt = plant_prompt(question)
    response = llm(prompt, max_tokens=60)
    print("PlantAssist:", response["choices"][0]["text"].strip())
