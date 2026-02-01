#!/usr/bin/env python3
"""
Emergency Repair for AI Documentation Generator
Fixes corrupted documentation.json from multi-file uploads
"""

import json
import shutil
from pathlib import Path
from datetime import datetime


def repair_documentation_store():
    """
    Comprehensive repair for documentation.json corruption.
    """
    print("=" * 70)
    print("🔧 AI Documentation Generator - Emergency Repair Tool")
    print("=" * 70)
    
    filepath = Path("documentation.json")
    
    # Step 1: Check file existence
    if not filepath.exists():
        print("\n✅ No documentation.json found - this is fine!")
        print("   A fresh file will be created on next upload.")
        return
    
    print(f"\n📁 Found: {filepath}")
    
    # Step 2: Backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(f"documentation.backup.{timestamp}.json")
    
    try:
        shutil.copy2(filepath, backup_path)
        print(f"💾 Backup created: {backup_path}")
    except Exception as e:
        print(f"⚠️  Backup failed: {e}")
        response = input("Continue without backup? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Step 3: Load and analyze
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("✅ Valid JSON syntax")
    except json.JSONDecodeError as e:
        print(f"\n❌ FATAL: Corrupted JSON - {e}")
        print("\n🔧 SOLUTION:")
        print(f"   1. Delete {filepath}")
        print("   2. Restart application")
        print(f"   3. Original backed up as: {backup_path}")
        return
    
    # Step 4: Detailed diagnosis
    print("\n" + "=" * 70)
    print("📊 DIAGNOSIS")
    print("=" * 70)
    
    issues_found = []
    
    print(f"\n🔍 Root type: {type(data).__name__}")
    
    if isinstance(data, list):
        print(f"⚠️  WARNING: Root is a LIST (legacy format)")
        print(f"   Entries: {len(data)}")
        
        # Check each entry
        file_entries = 0
        function_entries = 0
        invalid_entries = 0
        
        for idx, entry in enumerate(data):
            if not isinstance(entry, dict):
                invalid_entries += 1
                continue
            
            keys = set(entry.keys())
            
            # Is it a file entry?
            if {"id", "filename", "language", "file_hash"}.issubset(keys):
                file_entries += 1
            # Is it a function entry? (THE BUG!)
            elif {"function", "documentation"}.issubset(keys):
                function_entries += 1
                print(f"   ❌ Entry {idx}: FUNCTION (should be nested in file!)")
                issues_found.append(("function_at_root", idx, entry))
            else:
                invalid_entries += 1
                print(f"   ❌ Entry {idx}: Unknown structure - {list(keys)}")
        
        print(f"\n📈 Summary:")
        print(f"   ✅ Valid files: {file_entries}")
        print(f"   ❌ Misplaced functions: {function_entries}")
        print(f"   ❌ Invalid entries: {invalid_entries}")
        
        if function_entries > 0:
            issues_found.append(("legacy_list_with_functions", None, None))
    
    elif isinstance(data, dict):
        if "files" not in data:
            print("❌ Missing 'files' key!")
            issues_found.append(("missing_files_key", None, None))
        else:
            files = data["files"]
            print(f"✅ Has 'files' array: {len(files)} entries")
            
            # Validate each file
            print("\n🔍 Validating file entries...")
            valid = 0
            invalid = 0
            
            required_fields = {
                "id", "filename", "language", "language_icon",
                "timestamp", "file_size_bytes", "file_hash", "function_count"
            }
            
            for idx, entry in enumerate(files):
                if not isinstance(entry, dict):
                    print(f"   ❌ Entry {idx}: Not a dict")
                    invalid += 1
                    issues_found.append(("non_dict_file", idx, entry))
                    continue
                
                keys = set(entry.keys())
                missing = required_fields - keys
                
                # Check if it's a FUNCTION not a FILE (common bug!)
                if {"function", "documentation"}.issubset(keys):
                    print(f"   ❌ Entry {idx}: FUNCTION in files array!")
                    print(f"      Function name: {entry.get('function', 'unknown')}")
                    invalid += 1
                    issues_found.append(("function_in_files", idx, entry))
                elif missing:
                    print(f"   ❌ Entry {idx}: Missing {missing}")
                    invalid += 1
                    issues_found.append(("missing_fields", idx, entry))
                else:
                    valid += 1
            
            print(f"\n📈 Results: {valid} valid, {invalid} invalid")
        
        if "metadata" in data:
            print(f"\n✅ Has metadata")
            meta = data["metadata"]
            print(f"   Total files: {meta.get('total_files', 'N/A')}")
            print(f"   Total functions: {meta.get('total_functions', 'N/A')}")
    
    else:
        print(f"❌ Unexpected root type: {type(data).__name__}")
        issues_found.append(("wrong_root_type", None, None))
    
    # Step 5: Repair
    if not issues_found:
        print("\n" + "=" * 70)
        print("✅ NO ISSUES FOUND - File is healthy!")
        print("=" * 70)
        return
    
    print("\n" + "=" * 70)
    print("🔧 ATTEMPTING REPAIR")
    print("=" * 70)
    
    repaired_data = repair_data(data, issues_found)
    
    if repaired_data:
        # Write repaired file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(repaired_data, f, indent=2)
            
            print("\n✅ REPAIR SUCCESSFUL!")
            print(f"   Repaired file saved: {filepath}")
            print(f"   Original backed up: {backup_path}")
            
            # Show stats
            if "files" in repaired_data:
                print(f"\n📊 Repaired data:")
                print(f"   Files: {len(repaired_data['files'])}")
                print(f"   Functions: {repaired_data.get('metadata', {}).get('total_functions', 'N/A')}")
        
        except Exception as e:
            print(f"\n❌ Failed to write repaired file: {e}")
    else:
        print("\n❌ REPAIR FAILED - Could not fix corruption")
        print("\n🔧 MANUAL FIX REQUIRED:")
        print(f"   1. Delete {filepath}")
        print("   2. Restart application and re-upload files")
        print(f"   3. Original backed up: {backup_path}")
    
    print("\n" + "=" * 70)


def repair_data(data, issues):
    """
    Attempt to repair corrupted data based on identified issues.
    """
    issue_types = {i[0] for i in issues}
    
    # CASE 1: Legacy list format
    if "legacy_list_with_functions" in issue_types or isinstance(data, list):
        print("🔧 Converting legacy list to new format...")
        
        valid_files = []
        required = {"id", "filename", "language", "file_hash"}
        
        for entry in data:
            if isinstance(entry, dict) and required.issubset(entry.keys()):
                valid_files.append(entry)
        
        if valid_files:
            return {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "total_files": len(valid_files),
                    "total_functions": sum(e.get("function_count", 0) for e in valid_files),
                    "languages": list(set(e.get("language", "Unknown") for e in valid_files))
                },
                "files": valid_files
            }
    
    # CASE 2: Functions in files array
    if "function_in_files" in issue_types:
        print("🔧 Removing misplaced function entries...")
        
        if isinstance(data, dict) and "files" in data:
            required = {"id", "filename", "language", "file_hash"}
            
            # Keep only valid file entries
            clean_files = []
            for entry in data["files"]:
                if isinstance(entry, dict):
                    # Is it a file entry?
                    if required.issubset(entry.keys()):
                        clean_files.append(entry)
                    # Skip if it's a function entry
                    elif {"function", "documentation"}.issubset(entry.keys()):
                        print(f"   Removing function: {entry.get('function', 'unknown')}")
            
            if clean_files:
                data["files"] = clean_files
                
                # Update metadata
                if "metadata" not in data:
                    data["metadata"] = {}
                
                data["metadata"]["last_updated"] = datetime.now().isoformat()
                data["metadata"]["total_files"] = len(clean_files)
                data["metadata"]["total_functions"] = sum(
                    f.get("function_count", 0) for f in clean_files
                )
                
                return data
    
    # CASE 3: Missing files key
    if "missing_files_key" in issue_types and isinstance(data, dict):
        print("🔧 Adding missing 'files' key...")
        data["files"] = []
        return data
    
    return None


if __name__ == "__main__":
    try:
        repair_documentation_store()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()