"""
AI Documentation Generator - Web UI
Production-ready Streamlit interface with advanced features
"""

import streamlit as st
import tempfile
import os
import logging
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

from src.parser import CodeParser
from src.llm_client import LLMClient
from src.rag_engine import RAGEngine
from src.doc_store import DocumentationStore


# -------------------------------------------------
# Logging Configuration
# -------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DocGenApp")


# -------------------------------------------------
# Constants
# -------------------------------------------------

MAX_FILE_SIZE_MB = 2
MAX_FUNCTIONS_PER_FILE = 30
STORAGE_FILE = "documentation.json"


# -------------------------------------------------
# Page Configuration
# -------------------------------------------------

st.set_page_config(
    page_title="AI Documentation Generator",
    layout="wide",
    page_icon="📚",
    initial_sidebar_state="expanded"
)


# -------------------------------------------------
# Custom CSS for Professional Look
# -------------------------------------------------

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        color: #6c757d;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .stAlert {
        border-radius: 10px;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    .success-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------
# Header
# -------------------------------------------------

st.markdown('<h1 class="main-header">🤖 AI Documentation Generator</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Transform your code into professional documentation instantly using AI</p>',
    unsafe_allow_html=True
)


# -------------------------------------------------
# Cached Resources (Singleton Pattern)
# -------------------------------------------------

@st.cache_resource
def load_tools():
    """Initialize and cache core tools."""
    try:
        return {
            "parser": CodeParser(),
            "rag": RAGEngine(),
            "doc_store": DocumentationStore(STORAGE_FILE)
        }
    except Exception as e:
        logger.error(f"Failed to initialize tools: {e}")
        st.error(f"Initialization error: {e}")
        st.stop()


tools = load_tools()
parser = tools["parser"]
rag = tools["rag"]
doc_store = tools["doc_store"]


# -------------------------------------------------
# Session State Management
# -------------------------------------------------

if "last_results" not in st.session_state:
    st.session_state.last_results = None

if "processing" not in st.session_state:
    st.session_state.processing = False

if "history" not in st.session_state:
    st.session_state.history = []


# -------------------------------------------------
# Helper Functions
# -------------------------------------------------

def safe_generate_doc(fn: Dict, context: Any) -> Dict:
    """
    Thread-safe documentation generation worker.
    Each call gets its own LLM client instance.
    """
    try:
        local_llm = LLMClient()
        docs = local_llm.generate_docs(fn, context)
        return {
            "function": fn["name"],
            "documentation": docs,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"LLM failure for {fn['name']}: {e}")
        return {
            "function": fn["name"],
            "documentation": {"error": str(e)},
            "status": "error"
        }

def format_file_size(size_bytes: int) -> str:
    """
    Convert bytes into human readable string.
    Always shows correct unit (B / KB / MB / GB).
    """
    if size_bytes == 0:
        return "0 B"

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024

    return f"{size_bytes:.2f} PB"


def process_file(file_path: str, filename: str, content: str, size: int) -> List[Dict]:
    """
    Main file processing pipeline.
    Returns list of documentation results.
    """
    
    # Step 1: Parse source code
    with st.status("📖 Parsing source code...", expanded=True) as status:
        functions = parser.parse_file(file_path)
        
        if not functions:
            st.warning("⚠️ No Python functions detected in this file.")
            status.update(label="Parsing complete - No functions found", state="complete")
            return []
        
        functions = functions[:MAX_FUNCTIONS_PER_FILE]
        st.write(f"✅ Found {len(functions)} functions")
        status.update(label=f"Parsing complete - {len(functions)} functions", state="complete")
    
    # Step 2: Build RAG context
    with st.status("🧠 Building RAG context...", expanded=True) as status:
        rag.reset()
        existing = [f["docstring"] for f in functions if f.get("docstring")]
        
        if existing:
            rag.add_documents(existing)
            st.write(f"✅ Added {len(existing)} existing docstrings to knowledge base")
        else:
            st.write("ℹ️ No existing docstrings found")
        
        # Pre-fetch RAG contexts
        contexts = [rag.query(f["source"], n_results=2) for f in functions]
        status.update(label="RAG context ready", state="complete")
    
    # Step 3: Generate documentation with AI
    with st.status("🤖 Generating documentation with AI...", expanded=True) as status:
        results = []
        progress_bar = st.progress(0)
        progress_text = st.empty()
        
        max_workers = min(4, os.cpu_count() or 1)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(safe_generate_doc, fn, contexts[i])
                for i, fn in enumerate(functions)
            ]
            
            for i, future in enumerate(as_completed(futures)):
                results.append(future.result())
                progress = (i + 1) / len(futures)
                progress_bar.progress(progress)
                progress_text.text(f"Generated {i + 1}/{len(functions)} functions")
        
        success_count = sum(1 for r in results if r.get("status") == "success")
        status.update(
            label=f"Documentation generated - {success_count}/{len(functions)} successful",
            state="complete"
        )
    
    # Step 4: Save to store
    with st.status("💾 Saving documentation...", expanded=True) as status:
        # Clean results for storage (remove "status" field)
        clean_results = [
            {"function": r["function"], "documentation": r["documentation"]}
            for r in results
        ]
        
        save_result = doc_store.add_documentation(
            filename=filename,
            file_content=content,
            file_size_bytes=size,
            documentation=clean_results
        )
        
        if save_result.get("status") == "success":
            st.success(f"✅ Saved to documentation store ({save_result.get('files')} total files)")
            status.update(label="Documentation saved successfully", state="complete")
        else:
            st.error(f"❌ Save failed: {save_result.get('message')}")
            status.update(label="Save failed", state="error")
    
    return results


def render_results(docs: List[Dict]):
    """
    Render documentation results with enhanced UI.
    """
    
    # Success/Error Summary
    success = sum(1 for d in docs if d.get("status") == "success")
    errors = len(docs) - success
    
    st.markdown(
        f'<div class="success-banner">'
        f'<h3>✅ Documentation Generated Successfully!</h3>'
        f'<p>{success} functions documented • {errors} errors</p>'
        f'</div>',
        unsafe_allow_html=True
    )
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Total Functions", len(docs))
    col2.metric("✅ Successful", success, delta=None)
    col3.metric("❌ Errors", errors, delta_color="inverse")
    
    st.divider()
    
    # Tabbed view for better organization
    tab1, tab2 = st.tabs(["📝 Detailed View", "📄 Markdown Export"])
    
    with tab1:
        render_detailed_view(docs)
    
    with tab2:
        render_markdown_export(docs)


def render_detailed_view(docs: List[Dict]):
    """Render detailed expandable view of each function."""
    
    for item in docs:
        icon = "✅" if item["status"] == "success" else "❌"
        
        with st.expander(f"{icon} **{item['function']}**", expanded=False):
            d = item["documentation"]
            
            if isinstance(d, dict) and "error" not in d:
                # Description
                if d.get("description"):
                    st.markdown("### 📝 Description")
                    st.write(d["description"])
                
                # Parameters
                if d.get("parameters"):
                    st.markdown("### 🔧 Parameters")
                    for p in d["parameters"]:
                        if isinstance(p, dict):
                            name = p.get("name", "")
                            ptype = p.get("type", "")
                            desc = p.get("description", "")
                        else:
                            name = str(p)
                            ptype = ""
                            desc = ""
                        
                        if ptype:
                            st.markdown(f"- **`{name}`** `({ptype})` — {desc}")
                        else:
                            st.markdown(f"- **`{name}`** — {desc}")
                
                # Returns
                if d.get("returns"):
                    st.markdown("### ↩️ Returns")
                    st.write(d["returns"])
                
                # Example
                if d.get("example"):
                    st.markdown("### 💡 Example Usage")
                    st.code(d["example"], language="python")
                
                # Notes (if available)
                if d.get("notes"):
                    st.markdown("### 📌 Notes")
                    st.info(d["notes"])
            
            else:
                st.error("⚠️ Documentation generation failed for this function")
                if isinstance(d, dict):
                    st.json(d)
                else:
                    st.write(d)


def render_markdown_export(docs: List[Dict]):
    """Generate and display markdown export."""
    
    md = generate_markdown(docs)
    
    st.markdown("### Preview")
    st.markdown(md)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="⬇️ Download Markdown",
            data=md,
            file_name=f"documentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    with col2:
        # Generate JSON export
        json_data = json.dumps(docs, indent=2)
        st.download_button(
            label="⬇️ Download JSON",
            data=json_data,
            file_name=f"documentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )


def generate_markdown(docs: List[Dict]) -> str:
    """Generate formatted markdown documentation."""
    
    md = f"# API Documentation\n\n"
    md += f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    md += "---\n\n"
    
    for item in docs:
        d = item["documentation"]
        
        if isinstance(d, dict) and "error" not in d:
            md += f"## `{item['function']}`\n\n"
            
            if d.get("description"):
                md += f"{d['description']}\n\n"
            
            if d.get("parameters"):
                md += "**Parameters:**\n\n"
                for p in d.get("parameters", []):
                    if isinstance(p, dict):
                        name = p.get("name", "")
                        ptype = p.get("type", "")
                        desc = p.get("description", "")
                        md += f"- `{name}`"
                        if ptype:
                            md += f" *({ptype})*"
                        if desc:
                            md += f": {desc}"
                        md += "\n"
                    else:
                        md += f"- `{p}`\n"
                md += "\n"
            
            if d.get("returns"):
                md += f"**Returns:** {d['returns']}\n\n"
            
            if d.get("example"):
                md += "**Example:**\n\n"
                md += f"```python\n{d['example']}\n```\n\n"
            
            if d.get("notes"):
                md += f"**Notes:** {d['notes']}\n\n"
            
            md += "---\n\n"
    
    return md


# -------------------------------------------------
# Sidebar - Enhanced Stats & Controls
# -------------------------------------------------

with st.sidebar:
    st.header("📊 Documentation Store")
    
    try:
        stats = doc_store.get_stats()
        
        st.metric("📁 Total Files", stats.get("total_files", 0))
        st.metric("📚 Total Functions", stats.get("total_functions", 0))
        
        # Language breakdown
        if stats.get("languages"):
            st.subheader("💻 Languages")
            for lang, count in stats["languages"].items():
                st.write(f"- {lang}: {count} files")
        
        # Recent files
        if stats.get("recent_files"):
            st.subheader("🕒 Recent Files")
            for rf in stats["recent_files"][:3]:
                with st.expander(f"{rf['language_icon'] if 'language_icon' in rf else '📄'} {rf['filename']}", expanded=False):
                    st.caption(f"Functions: {rf['functions']}")
                    st.caption(f"Updated: {rf['timestamp'][:10]}")
        
    except Exception as e:
        st.warning("⚠️ Stats unavailable")
        logger.error(f"Stats error: {e}")
    
    st.divider()
    
    # Clear store button
    if st.button("🗑️ Clear All Documentation", type="secondary", use_container_width=True):
        if st.session_state.get("confirm_clear"):
            doc_store.clear()
            st.success("✅ Store cleared!")
            st.session_state.confirm_clear = False
            st.rerun()
        else:
            st.session_state.confirm_clear = True
            st.warning("⚠️ Click again to confirm")
    
    st.divider()
    
    # About section
    st.caption("**Powered by:**")
    st.caption("🤖 Groq AI")
    st.caption("🧠 RAG Engine")
    st.caption("⚡ Streamlit")
    
    st.divider()
    st.caption("Built by **Koushik Yadagiri**")
    st.caption("v2.0 - Production Ready")


# -------------------------------------------------
# Main UI - File Upload & Processing
# -------------------------------------------------

st.subheader("📤 Upload Your Code")

uploaded = st.file_uploader(
    "Choose a Python file to generate documentation",
    type=["py"],
    help="Maximum file size: 2MB"
)

if uploaded:
    # File info
    size_mb = uploaded.size / (1024 * 1024)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📄 Filename", uploaded.name)
    col2.metric("💾 Size", format_file_size(uploaded.size))
    col3.metric("🔧 Functions", "Analyzing...")
    
    # Validate file size
    if size_mb > MAX_FILE_SIZE_MB:
        st.error(f"❌ File too large! Maximum size is {MAX_FILE_SIZE_MB}MB")
    else:
        # Generate button
        if st.button("🚀 Generate Documentation", type="primary", use_container_width=True):
            st.session_state.processing = True
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = tmp.name
            
            try:
                content = uploaded.getvalue().decode("utf-8", errors="ignore")
                
                # Process file
                results = process_file(tmp_path, uploaded.name, content, uploaded.size)
                
                if results:
                    st.session_state.last_results = results
                    st.session_state.history.append({
                        "filename": uploaded.name,
                        "timestamp": datetime.now().isoformat(),
                        "functions": len(results)
                    })
                    
                    # Render results
                    render_results(results)
                
            except Exception as e:
                st.error(f"❌ Processing failed: {e}")
                logger.error(f"Processing error: {e}", exc_info=True)
            
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                
                st.session_state.processing = False

# Show previous results if available
elif st.session_state.last_results:
    st.info("ℹ️ Showing results from last generation")
    render_results(st.session_state.last_results)


# -------------------------------------------------
# Feature Highlights
# -------------------------------------------------

if not uploaded and not st.session_state.last_results:
    st.markdown("---")
    st.subheader("✨ Key Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🤖 AI-Powered")
        st.write("Uses advanced language models to generate comprehensive, accurate documentation")
    
    with col2:
        st.markdown("### 🧠 RAG Enhanced")
        st.write("Leverages existing code context for better, more relevant documentation")
    
    with col3:
        st.markdown("### ⚡ Fast & Parallel")
        st.write("Multi-threaded processing for rapid documentation generation")
    
    st.markdown("---")
    
    # Usage instructions
    with st.expander("📖 How to Use", expanded=True):
        st.markdown("""
        1. **Upload** your Python file using the file uploader above
        2. **Click** the "Generate Documentation" button
        3. **Review** the AI-generated documentation
        4. **Download** the documentation in Markdown or JSON format
        
        **Supported:**
        - Python (.py) files up to 2MB
        - Functions, classes, and methods
        - Existing docstrings (used for better context)
        """)


# -------------------------------------------------
# Footer
# -------------------------------------------------

st.divider()
st.caption("🚀 AI Documentation Generator | Transforming code into professional docs")