#!/bin/bash
echo "Testing network connectivity before starting..."
ping -c 2 8.8.8.8 > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: No internet connection."
    exit 1
fi

echo "Network connected. Starting pull for qwen2.5:7b..."
until ollama pull qwen2.5:7b; do
    echo "Connection dropped or interrupted. Retrying in 3 seconds..."
    sleep 3
done

echo "qwen2.5:7b downloaded successfully!"
echo "Creating qwen2.5-7b-ctx8k..."
ollama create qwen2.5-7b-ctx8k -f modelfiles/qwen2.5-7b-ctx8k.Modelfile

echo "Updating config.py to use qwen2.5-7b-ctx8k..."
python3 -c '
with open("config.py", "r") as f:
    content = f.read()
content = content.replace("DEFAULT_MODEL = \"qwen2.5:0.5b\"", "DEFAULT_MODEL = \"qwen2.5-7b-ctx8k\"")
with open("config.py", "w") as f:
    f.write(content)
'

echo "Setup complete! qwen2.5-7b-ctx8k is ready."
