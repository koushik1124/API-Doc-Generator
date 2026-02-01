import json
import os
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from pathlib import Path
from threading import Lock
from pydantic import BaseModel, Field, ValidationError


# ---------------- Logging ----------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DocumentationStore")


# ---------------- Schemas ----------------

class FunctionDoc(BaseModel):
    function: str
    documentation: Union[Dict[str, Any], str]


class FileEntry(BaseModel):
    id: str
    filename: str
    language: str
    language_icon: str
    timestamp: str
    file_size_bytes: int
    file_hash: str
    function_count: int
    functions: List[FunctionDoc] = Field(default_factory=list)


class StoreMetadata(BaseModel):
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_updated: Optional[str] = None
    total_files: int = 0
    total_functions: int = 0
    languages: List[str] = Field(default_factory=list)


class FullStoreSchema(BaseModel):
    metadata: StoreMetadata = Field(default_factory=StoreMetadata)
    files: List[FileEntry] = Field(default_factory=list)


# ---------------- Store ----------------

class DocumentationStore:
    """
    Portable, thread-safe, crash-safe documentation store.
    
    Handles multiple file uploads safely with proper validation.

    Works on:
    - Windows / Linux / Mac
    - Local / Render / Streamlit Cloud
    """

    LANGUAGE_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".java": "Java",
        ".cpp": "C++",
        ".c": "C",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
    }

    LANGUAGE_ICONS = {
        "Python": "🐍",
        "JavaScript": "🟨",
        "TypeScript": "🔷",
        "Java": "☕",
        "C++": "⚙️",
        "C": "🔧",
        "Go": "🐹",
        "Rust": "🦀",
        "Ruby": "💎",
        "PHP": "🐘",
        "Unknown": "📄"
    }

    def __init__(self, storage_path: str = "documentation.json"):
        self.storage_path = Path(storage_path).resolve()
        self._lock = Lock()
        logger.info(f"📁 DocumentationStore initialized: {self.storage_path}")
        self._ensure_storage_exists()

    # ------------------------------------------------

    def _ensure_storage_exists(self):
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.storage_path.exists():
                logger.info("Creating new empty store")
                self._save_data(FullStoreSchema())
        except Exception as e:
            logger.error(f"Storage init failed: {e}")

    # ------------------------------------------------

    def _load_data(self) -> FullStoreSchema:
        """Load with comprehensive error recovery."""
        with self._lock:
            try:
                if not self.storage_path.exists():
                    logger.warning("Storage file missing, creating new")
                    return FullStoreSchema()

                with open(self.storage_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)

                # CASE 1: Legacy list format (old data)
                if isinstance(raw, list):
                    logger.warning("⚠️  Detected legacy list format, migrating...")
                    return self._migrate_legacy_list(raw)

                # CASE 2: Standard schema format
                if isinstance(raw, dict):
                    # Has proper structure?
                    if "files" in raw:
                        try:
                            return FullStoreSchema(**raw)
                        except ValidationError as ve:
                            logger.error(f"Validation failed: {ve}")
                            # Attempt partial recovery
                            return self._recover_partial_data(raw)
                    else:
                        logger.error("❌ Missing 'files' key in JSON")
                        return FullStoreSchema()

                logger.error(f"❌ Unexpected root type: {type(raw)}")
                return FullStoreSchema()

            except json.JSONDecodeError as e:
                logger.error(f"❌ Corrupted JSON: {e}")
                self._backup_and_reset()
                return FullStoreSchema()
            
            except Exception as e:
                logger.error(f"❌ Unexpected load error: {e}", exc_info=True)
                return FullStoreSchema()

    # ------------------------------------------------

    def _migrate_legacy_list(self, raw_list: list) -> FullStoreSchema:
        """Safely migrate old list format to new schema."""
        valid_files = []
        required_fields = {"id", "filename", "language", "file_hash"}
        
        for idx, item in enumerate(raw_list):
            if not isinstance(item, dict):
                logger.warning(f"Skipping non-dict at index {idx}")
                continue
            
            # Check if it's a FILE entry (not a function entry!)
            if not required_fields.issubset(item.keys()):
                logger.warning(
                    f"❌ Skipping entry {idx}: looks like a function, not a file"
                    f"\n   Has keys: {list(item.keys())}"
                )
                continue
            
            try:
                valid_files.append(FileEntry(**item))
                logger.debug(f"✅ Migrated: {item.get('filename', 'unknown')}")
            except ValidationError as e:
                logger.warning(f"Skipping invalid entry {idx}: {e}")
        
        logger.info(f"✅ Migrated {len(valid_files)}/{len(raw_list)} files")
        return FullStoreSchema(files=valid_files)

    # ------------------------------------------------

    def _recover_partial_data(self, raw_data: dict) -> FullStoreSchema:
        """Attempt to recover valid files from corrupted data."""
        logger.warning("🔧 Attempting partial data recovery...")
        
        valid_files = []
        files_array = raw_data.get("files", [])
        
        for idx, file_data in enumerate(files_array):
            if not isinstance(file_data, dict):
                logger.warning(f"Skipping non-dict file at {idx}")
                continue
            
            # Validate it has file entry fields (not function fields)
            required = {"id", "filename", "language", "file_hash"}
            if not required.issubset(file_data.keys()):
                logger.warning(
                    f"Skipping index {idx}: not a valid file entry"
                    f"\n   Has: {list(file_data.keys())}"
                )
                continue
            
            try:
                valid_files.append(FileEntry(**file_data))
            except ValidationError as e:
                logger.warning(f"Skipping corrupted file {idx}: {str(e)[:100]}")
        
        if valid_files:
            logger.info(f"✅ Recovered {len(valid_files)} valid files")
            return FullStoreSchema(
                metadata=raw_data.get("metadata", {}),
                files=valid_files
            )
        
        logger.error("❌ No valid files recovered")
        return FullStoreSchema()

    # ------------------------------------------------

    def _backup_and_reset(self):
        """Backup corrupted file and reset."""
        try:
            if self.storage_path.exists():
                backup = self.storage_path.with_suffix(
                    f".corrupted.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                )
                self.storage_path.rename(backup)
                logger.info(f"💾 Corrupted file backed up: {backup.name}")
        except Exception as e:
            logger.error(f"Backup failed: {e}")

    # ------------------------------------------------

    def _save_data(self, store: FullStoreSchema):
        """Atomic save with metadata update."""
        with self._lock:
            tmp = self.storage_path.with_suffix(".tmp")

            try:
                # Update metadata
                store.metadata.last_updated = datetime.utcnow().isoformat()
                store.metadata.total_files = len(store.files)
                store.metadata.total_functions = sum(f.function_count for f in store.files)
                store.metadata.languages = sorted({f.language for f in store.files})

                # Write to temp file first
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(store.model_dump_json(indent=2))

                # Atomic replace
                os.replace(tmp, self.storage_path)
                logger.debug(f"💾 Saved {len(store.files)} files")

            except Exception as e:
                logger.error(f"❌ Save failed: {e}")
                try:
                    tmp.unlink(missing_ok=True)
                except Exception:
                    pass

    # ------------------------------------------------
    # Public API
    # ------------------------------------------------

    def clear(self):
        """Reset store safely."""
        logger.info("🗑️  Clearing all documentation")
        self._save_data(FullStoreSchema())

    def get_all_docs(self) -> Dict:
        """Never throws - always returns valid dict."""
        try:
            return self._load_data().model_dump()
        except Exception as e:
            logger.error(f"get_all_docs error: {e}")
            return {"metadata": {}, "files": []}

    def get_stats(self) -> Dict:
        """Get store statistics."""
        store = self._load_data()

        lang_count = {}
        for f in store.files:
            lang_count[f.language] = lang_count.get(f.language, 0) + 1

        return {
            "total_files": len(store.files),
            "total_functions": store.metadata.total_functions,
            "languages": lang_count,
            "recent_files": [
                {
                    "filename": f.filename,
                    "language": f.language,
                    "timestamp": f.timestamp,
                    "functions": f.function_count
                }
                for f in sorted(store.files, key=lambda x: x.timestamp, reverse=True)[:5]
            ]
        }

    # ------------------------------------------------

    def _language(self, filename: str):
        return self.LANGUAGE_MAP.get(Path(filename).suffix.lower(), "Unknown")

    def _icon(self, lang: str):
        return self.LANGUAGE_ICONS.get(lang, "📄")

    # ------------------------------------------------

    def add_documentation(
        self,
        filename: str,
        file_content: str,
        file_size_bytes: int,
        documentation: List[Dict],
    ) -> Dict:
        """
        Add or update file documentation.
        
        CRITICAL: documentation must be a list of dicts with structure:
        [
            {
                "function": "func_name",
                "documentation": {...}
            },
            ...
        ]
        """
        try:
            # INPUT VALIDATION
            if not isinstance(documentation, list):
                raise ValueError(
                    f"documentation must be a list, got {type(documentation).__name__}"
                )
            
            # Check if it's a list of functions (not file entries!)
            for idx, doc in enumerate(documentation):
                if not isinstance(doc, dict):
                    raise ValueError(f"documentation[{idx}] must be dict")
                if "function" not in doc:
                    raise ValueError(
                        f"documentation[{idx}] missing 'function' key. "
                        f"Has keys: {list(doc.keys())}"
                    )
            
            logger.info(f"📝 Adding documentation for: {filename} ({len(documentation)} functions)")
            
            store = self._load_data()

            file_hash = hashlib.md5(file_content.encode("utf-8")).hexdigest()
            language = self._language(filename)

            entry = FileEntry(
                id=file_hash[:12],
                filename=filename,
                language=language,
                language_icon=self._icon(language),
                timestamp=datetime.utcnow().isoformat(),
                file_size_bytes=file_size_bytes,
                file_hash=file_hash,
                function_count=len(documentation),
                functions=[FunctionDoc(**d) for d in documentation],
            )

            # Replace if exists, else append
            existing = next(
                (i for i, f in enumerate(store.files) if f.file_hash == file_hash), 
                None
            )

            if existing is not None:
                store.files[existing] = entry
                logger.info(f"✅ Updated existing file: {filename}")
            else:
                store.files.append(entry)
                logger.info(f"✅ Added new file: {filename}")

            self._save_data(store)

            return {
                "status": "success",
                "files": len(store.files),
                "message": f"Documented {len(documentation)} functions in {filename}"
            }

        except Exception as e:
            logger.error(f"❌ Add documentation failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------

    def get_file_docs(self, filename: str) -> Optional[Dict]:
        """Get documentation for a specific file."""
        store = self._load_data()
        for file_entry in store.files:
            if file_entry.filename == filename:
                return file_entry.model_dump()
        return None

    def search_functions(self, query: str) -> List[Dict]:
        """Search for functions across all files."""
        store = self._load_data()
        results = []
        query_lower = query.lower()
        
        for file_entry in store.files:
            for func in file_entry.functions:
                if query_lower in func.function.lower():
                    results.append({
                        "file": file_entry.filename,
                        "function": func.function,
                        "documentation": func.documentation
                    })
        
        return results


# ------------------------------------------------
# CLI for testing/debugging
# ------------------------------------------------

if __name__ == "__main__":
    import sys
    
    store = DocumentationStore()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "stats":
            print(json.dumps(store.get_stats(), indent=2))
        
        elif cmd == "clear":
            store.clear()
            print("✅ Store cleared")
        
        elif cmd == "dump":
            print(json.dumps(store.get_all_docs(), indent=2))
        
        else:
            print("Usage: python doc_store.py [stats|clear|dump]")
    else:
        stats = store.get_stats()
        print(f"📊 Total files: {stats['total_files']}")
        print(f"📚 Total functions: {stats['total_functions']}")
        print(f"🌐 Languages: {stats['languages']}")