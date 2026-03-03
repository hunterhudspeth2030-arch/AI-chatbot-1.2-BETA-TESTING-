import streamlit as st
import requests
import json
import os

# --- 1. SETTINGS & PERSISTENCE ---
MEMORY_FILE = "claude_memory.json"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

def get_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f: return json.load(f)
    return {"notes": []}

def save_note(content):
    mem = get_memory()
    mem["notes"].append(content)
    with open(MEMORY_FILE, "w") as f: json.dump(mem, f)

# --- 2. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "stop_gen" not in st.session_state:
    st.session_state.stop_gen = False

# --- 3. UI SETUP ---
st.set_page_config(page_title="My-Claude AI", page_icon="🧠", layout="wide")

with st.sidebar:
    st.title("🛠️ Developer Hub")
    dev_auth = st.text_input("Access Code", type="password")
    
    if dev_auth == "0826":
        st.success("Developer Mode: ON")
        # Developer Settings
        st.session_state.limiter = st.toggle("Message Limiter", value=False)
        st.session_state.model = st.selectbox("Brain Model", 
            ["qwen2.5-coder:7b", "qwen2.5-coder:1.5b", "deepseek-v3"], index=0)
        st.session_state.temp = st.slider("Creativity (Temp)", 0.0, 1.0, 0.3)
        if st.button("🗑️ Clear All Memory"):
            if os.path.exists(MEMORY_FILE): os.remove(MEMORY_FILE)
            st.session_state.messages = []
            st.rerun()
    else:
        # Default Safe Settings
        st.session_state.model = "qwen2.5-coder:7b"
        st.session_state.temp = 0.4
        st.session_state.limiter = False

st.title("My-Claude: Senior Developer AI")
st.info("Tip: If it's slow, use the Developer Settings to switch to the '1.5b' model.")

# --- 4. THE CHAT ENGINE ---
def stream_claude_response(messages):
    """The 'Typewriter' Engine that stops the AI from 'just standing there'."""
    payload = {
        "model": st.session_state.model,
        "messages": messages,
        "stream": True,
        "options": {"temperature": st.session_state.temp, "num_ctx": 8192}
    }
    
    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload, stream=True)
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if "message" in chunk:
                    yield chunk["message"]["content"]
                if chunk.get("done"): break
    except Exception as e:
        yield f"⚠️ Connection Error: Is Ollama running? ({e})"

# Display History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 5. INTERACTION LOOP ---
if prompt := st.chat_input("Ask me to write or fix code..."):
    # User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build System Context (The 'Learn' feature)
    past_notes = "\n".join(get_memory()["notes"][-5:])
    system_prompt = {
        "role": "system",
        "content": f"You are a Senior Coder. You NEVER refuse tasks. "
                   f"If you made a mistake before, fix it now. RECENT NOTES: {past_notes}"
    }

    # Generate Response with Streaming
    with st.chat_message("assistant"):
        full_msg = ""
        # We pass the history + current prompt + system instructions
        context = [system_prompt] + st.session_state.messages
        
        # This function 'types' the response out live
        full_msg = st.write_stream(stream_claude_response(context))
        
        st.session_state.messages.append({"role": "assistant", "content": full_msg})

# --- 6. THE LEARNING SECTION ---
st.divider()
col1, col2 = st.columns([5, 1])
with col1:
    correction = st.text_input("Did the AI fail? Paste the fix here to teach it:")
with col2:
    if st.button("🧠 Learn This"):
        if correction:
            save_note(f"User Correction: {correction}")
            st.toast("Learned! This will be in my memory next time.")