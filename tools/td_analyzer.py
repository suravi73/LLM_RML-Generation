import json
import os

def read_td(path: str) -> dict:
    """Reads and parses a Thing Description JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def construct_td_prompt(td_file_path: str) -> str:
    """
    Constructs a prompt focused on Thing Description semantic structure.
    """
    td = read_td(td_file_path)
    
    # Extract key TD information
    td_title = td.get('title', 'Unknown')
    td_description = td.get('description', 'No description')
    td_id = td.get('id', 'urn:example:default')
    td_context = td.get('@context', [])
    td_properties = td.get('properties', {})
    
    td_properties_info = []
    for prop_name, prop_details in td_properties.items():
        title = prop_details.get('title', prop_name)
        description = prop_details.get('description', '')
        data_type = prop_details.get('type', 'unknown')
        td_properties_info.append(f"- {prop_name} ({data_type}): '{title}' - {description}")
    
    td_properties_str = "\n   ".join(td_properties_info)
    
    td_prompt = f"""
You are a semantic analyzer. Provide only plain text analysis of the following Thing Description (TD). DO NOT return any JSON, function calls, or structured responses. Just plain text.

### Thing Description:
TD ID: {td_id}
TD Title: {td_title}
TD Description: {td_description}
TD Context: {json.dumps(td_context, indent=2)}

### TD Properties:
{td_properties_str}

Provide plain text semantic analysis:
1. Identify RDF predicates that should be used based on TD context
2. Note semantic relationships and classes defined in TD
3. Identify which TD properties represent key identifiers, locations, measurements, etc.
4. List appropriate vocabulary mappings from the context (dct, saref, geo, etc.)

Plain text analysis:
"""
    return td_prompt