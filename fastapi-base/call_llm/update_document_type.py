#!/usr/bin/env python3
"""
Script to add document_type support to all extraction scripts
"""

import os
import re

# List of files to update (scripts from important_posts)
EXTRACTION_SCRIPTS = [
    "/home/ai_team/lab/pipeline_mxh/fastapi-base/call_llm/extract_education.py",
    "/home/ai_team/lab/pipeline_mxh/fastapi-base/call_llm/extract_medical.py",
    "/home/ai_team/lab/pipeline_mxh/fastapi-base/call_llm/extract_security.py",
    "/home/ai_team/lab/pipeline_mxh/fastapi-base/call_llm/extract_society.py",
    "/home/ai_team/lab/pipeline_mxh/fastapi-base/call_llm/extract_digital_transformation.py",
    "/home/ai_team/lab/pipeline_mxh/fastapi-base/call_llm/extract_fdi.py",
    "/home/ai_team/lab/pipeline_mxh/fastapi-base/call_llm/extract_pii.py",
]

def update_query_add_document_type(content: str) -> str:
    """Add document_type to SELECT query"""
    # Pattern 1: SELECT without document_type
    pattern1 = r"(SELECT\s+(?:[\w,\s]+?))\s+(FROM important_posts)"
    
    def add_doc_type(match):
        select_clause = match.group(1)
        if 'document_type' not in select_clause:
            return f"{select_clause}, document_type FROM important_posts"
        return match.group(0)
    
    return re.sub(pattern1, add_doc_type, content, flags=re.IGNORECASE)


def update_row_dict_add_document_type(content: str) -> str:
    """Add document_type to post dict from row"""
    # Find pattern where we build dict from DB row
    pattern = r'(\"published_date\":\s*row\[\d+\])\s*\}'
    
    def add_doc_type_field(match):
        # Get the index number from previous field
        prev_indices = re.findall(r'row\[(\d+)\]', match.group(0))
        if prev_indices:
            next_idx = int(prev_indices[-1]) + 1
            return f'{match.group(1)},\n                "document_type": row[{next_idx}] or "external"\n            }}'
        return match.group(0)
    
    return re.sub(pattern, add_doc_type_field, content)


def update_process_function_extract_doc_type(content: str) -> str:
    """Add document_type extraction in process function"""
    # Pattern: province = article.get("province", ...)
    pattern = r'(province\s*=\s*article\.get\(\"province\",\s*[^)]+\))'
    
    replacement = r'\1\n    document_type = article.get("document_type", "external")'
    
    return re.sub(pattern, replacement, content)


def update_save_calls_add_document_type(content: str) -> str:
    """Add document_type to data before saving"""
    # Pattern: if data:\n        if save_to...
    # or: if data:\n        save_to...
    pattern = r'(if\s+(\w+):\s*\n\s+)(if\s+save_to|save_to)'
    
    replacement = r'\1\2["document_type"] = document_type\n        \3'
    
    return re.sub(pattern, replacement, content)


def process_file(filepath: str):
    """Process a single file"""
    print(f"Processing {os.path.basename(filepath)}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all transformations
        content = update_query_add_document_type(content)
        content = update_row_dict_add_document_type(content)
        content = update_process_function_extract_doc_type(content)
        content = update_save_calls_add_document_type(content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✅ Updated {os.path.basename(filepath)}")
            return True
        else:
            print(f"  ⏭️  No changes needed for {os.path.basename(filepath)}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error processing {os.path.basename(filepath)}: {e}")
        return False


def main():
    print("="*60)
    print("Adding document_type support to extraction scripts")
    print("="*60)
    
    updated = 0
    for script in EXTRACTION_SCRIPTS:
        if os.path.exists(script):
            if process_file(script):
                updated += 1
        else:
            print(f"⚠️  File not found: {script}")
    
    print(f"\n{'='*60}")
    print(f"✅ Updated {updated}/{len(EXTRACTION_SCRIPTS)} files")
    print("="*60)


if __name__ == "__main__":
    main()
