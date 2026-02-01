"""
AI Documentation Generator - CLI Mode
Production-ready command-line interface

Usage:
    python src/main.py sample_app.py
    python src/main.py path/to/code.py
"""

import sys
import json
import logging
from pathlib import Path

from parser import CodeParser
from llm_client import LLMClient
from rag_engine import RAGEngine
from doc_store import DocumentationStore


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DocGenCLI")


STORAGE_FILE = "documentation.json"


def main():
    """
    Main CLI entry point for documentation generation.
    """
    
    # Validate arguments
    if len(sys.argv) < 2:
        print("❌ Error: No file provided")
        print("\nUsage:")
        print("  python src/main.py <file.py>")
        print("\nExample:")
        print("  python src/main.py sample_app.py")
        print("  python src/main.py path/to/code.py")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Validate file exists
    if not Path(file_path).exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
    
    logger.info(f"📁 Processing: {file_path}")
    
    try:
        # Initialize tools
        parser = CodeParser()
        llm = LLMClient()
        rag = RAGEngine()
        doc_store = DocumentationStore(STORAGE_FILE)
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        file_size = len(file_content.encode('utf-8'))
        filename = Path(file_path).name
        
        # Parse functions
        logger.info("🔍 Parsing source code...")
        functions = parser.parse_file(file_path)
        
        if not functions:
            logger.warning("No Python functions detected in this file.")
            return
        
        logger.info(f"Found {len(functions)} functions")
        
        # Build RAG context
        logger.info("🧠 Building RAG context...")
        existing_docs = []
        for fn in functions:
            if fn.get("docstring"):
                existing_docs.append(fn["docstring"])
        
        if existing_docs:
            rag.add_documents(existing_docs)
            logger.info(f"Added {len(existing_docs)} existing docstrings to RAG")
        
        # Generate documentation
        logger.info("🤖 Generating documentation with AI...")
        results = []
        
        for i, fn in enumerate(functions, 1):
            logger.info(f"  [{i}/{len(functions)}] Generating docs for: {fn['name']}")
            
            context = rag.query(fn["source"])
            docs = llm.generate_docs(fn, context)
            
            # CRITICAL: Format correctly for DocumentationStore
            results.append({
                "function": fn["name"],
                "documentation": docs
            })
        
        # Save to documentation store (CORRECT WAY)
        logger.info("💾 Saving documentation...")
        save_result = doc_store.add_documentation(
            filename=filename,
            file_content=file_content,
            file_size_bytes=file_size,
            documentation=results  # List of {function, documentation} dicts
        )
        
        if save_result.get("status") == "success":
            logger.info(f"✅ Successfully saved documentation for {len(results)} functions")
            logger.info(f"📊 Total files in store: {save_result.get('files', 0)}")
            
            # Also save a readable JSON for debugging (optional)
            debug_file = f"{Path(filename).stem}_debug.json"
            with open(debug_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            logger.info(f"📄 Debug output saved to: {debug_file}")
            
        else:
            logger.error(f"❌ Failed to save documentation: {save_result.get('message')}")
            sys.exit(1)
        
        # Display summary
        print("\n" + "="*70)
        print("✅ Documentation Generation Complete!")
        print("="*70)
        print(f"File: {filename}")
        print(f"Functions documented: {len(results)}")
        print(f"Storage file: {STORAGE_FILE}")
        print("="*70)
        
    except Exception as e:
        logger.error(f"❌ Error during processing: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()