# 🤖 AI Documentation Generator (RAG-Powered)

A production-ready **multi-language AI documentation generator** built with **Retrieval Augmented Generation (RAG)**.

Upload source code and instantly get structured API documentation with examples — powered by Groq LLM + vector embeddings.

---

## 🚀 Features

✅ Multi-language support  
(Python, JavaScript, TypeScript, Java, C++, Go)

✅ RAG Context Engine (ChromaDB)

✅ Parallel LLM execution

✅ Structured JSON output

✅ Markdown + JSON export

✅ Streamlit Web UI

✅ Production-safe architecture

---

## 🧠 Architecture

```mermaid
Flowchart TD 
Code → Parser → RAG → Groq LLM → Structured Docs → UI Export
```


### Components

- **Parser** – Extracts functions from multiple languages  
- **RAG Engine** – Builds embeddings + retrieves contextual docs  
- **Groq LLM** – Generates structured documentation  
- **Streamlit UI** – Frontend interface  
- **Doc Store** – Persistent documentation archive  

---

## 📸 Demo

Upload a file → Generate → Review → Export.

---

## ⚙️ Tech Stack

- Python 3.10+
- Streamlit
- Groq (Llama-3.3-70B)
- ChromaDB
- Sentence Transformers
- Concurrent Futures
- Pydantic

---

## 🛠 Installation

### 1️⃣ Clone

```bash
git clone https://github.com/YOUR_USERNAME/ai-doc-generator.git
cd ai-doc-generator


2️⃣ Create Virtual Environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Environment Variables

Create .env:

GROQ_API_KEY=your_key_here

5️⃣ Run App
streamlit run app.py

📄 Output Example

Each function produces:

{
  "description": "...",
  "parameters": [],
  "returns": "",
  "example": "",
  "notes": ""
}