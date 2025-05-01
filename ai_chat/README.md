
# Instructions
0. **Download** this model from this link https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF

   ```
      tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf 
   ```

   place it in "ai_chat/" or the same directory as chatbot.py

1. **Open Terminal**

2. **Navigate to the project folder:**
    ```
      cd ~/Desktop/ai_chat/
    ```
3. **Activate the virtual enviroment:**

We must activate the virtual enviroment which contains the neccessary libraries to run chatbot.py.


Enter

    
    cd ~/~/ai_chat/
    

3. **Check virtual enviroment activation:**
Your terminal command line should look like this after
activating the virtual enviroment

```
(ai_chat) pi@raspberrypi:~/Desktop/ai_chat/bin $ 
```

4. **Return to previous directory**

```
cd ..
```

5. **Run the .py file**

```
python3 chatbot.py
```

6. **Enter your desired prompt** and patiently wait for response

# Troubleshooting

In case you are unable to activate the virtual enviroment:

Ensure you are in the directory of your choice, preferably in the same one as the ai_chat

In your terminal, enter:

```
python3 -m venv venv_name --system-site-packages
source venv_name/bin/activate
pip install llama-cpp-python
```
After that, proceed to run chatbot.py
```
python3 chatbot.py
```
