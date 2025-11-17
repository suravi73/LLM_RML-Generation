import json
import os
from typing import List, Dict, Any
from pathlib import Path

class UniversalToolServer:
    """
    This class defines available tools for semantic web operations
    and handles the logic for calling them.
    """
    
    # We keep the root_path in case future tools need it
    def __init__(self, root_path: Path):
        self.root_path = root_path
        print(f"Tool server initialized with root: {self.root_path}")

    async def __aenter__(self):
        print("Connecting to backend services (Semantic Tools)...")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        print("Disconnecting from backend services...")

    async def get_mcp_tools(self) -> List[dict]:
        """Defines the functions the LLM can use for RML generation."""
        return [
        {
            "type": "function",
            "function": {
                "name": "analyze_csv_structure",
                "description": "Analyzes the structure of a CSV file to identify columns, data types, and semantic meanings.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "csv_file_path": {"type": "string", "description": "Path to the CSV file to analyze"}
                    },
                    "required": ["csv_file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_thing_description",
                "description": "Analyzes a Thing Description JSON to extract semantic context, properties, and vocabulary mappings.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "td_file_path": {"type": "string", "description": "Path to the TD JSON file to analyze"}
                    },
                    "required": ["td_file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_rml_prefixes",
                "description": "Returns standard RML prefixes for Turtle files.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "generate_rml_mapping",
                "description": "Generates RML mapping based on CSV analysis and TD analysis.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "csv_analysis": {"type": "string", "description": "Analysis of CSV structure"},
                        "td_analysis": {"type": "string", "description": "Analysis of Thing Description"},
                        "csv_file_path": {"type": "string", "description": "Path to the original CSV file"}
                    },
                    "required": ["csv_analysis", "td_analysis", "csv_file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "validate_rml_syntax",
                "description": "Validates the syntax of RML Turtle content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rml_content": {"type": "string", "description": "The RML Turtle content to validate"}
                    },
                    "required": ["rml_content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "refine_rml_with_error",
                "description": "Refines RML content based on an error message.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "previous_rml": {"type": "string", "description": "The RML content that had errors"},
                        "error_message": {"type": "string", "description": "The error message to fix"},
                        "error_type": {"type": "string", "description": "Type of error: 'syntax', 'rml_semantic', 'rml_syntax'"}
                    },
                    "required": ["previous_rml", "error_message", "error_type"],
                },
            },
        },
    ]

    async def call_tool(self, tool_name: str, args: dict) -> Dict:
        """Executes the actual command."""
        print(f"Executing tool '{tool_name}' with arguments: {args}")
        
        # --- 1. TOOL: analyze_csv_structure ---
        if tool_name == "analyze_csv_structure":
            csv_file_path = args.get("csv_file_path")
            if not csv_file_path or not os.path.exists(csv_file_path):
                return {"error": f"CSV file not found: {csv_file_path}"}
            
            try:
                from tools.data_analyzer import construct_data_prompt
                prompt = construct_data_prompt(csv_file_path)
                # If you want to execute the analysis immediately:
                # response = await self.ask(prompt)  # Assuming you have self.ask method
                # return {"status": "success", "result": response}
                # OR return the prompt for the LLM to see:
                return {"status": "success", "result": prompt}
            except Exception as e:
                return {"error": f"Failed to analyze CSV: {str(e)}"}

        # --- 2. TOOL: analyze_thing_description ---
        if tool_name == "analyze_thing_description":
            td_file_path = args.get("td_file_path")
            if not td_file_path or not os.path.exists(td_file_path):
                return {"error": f"TD file not found: {td_file_path}"}
            
            try:
                from tools.td_analyzer import construct_td_prompt
                prompt = construct_td_prompt(td_file_path)
                return {"status": "success", "result": prompt}
            except Exception as e:
                return {"error": f"Failed to analyze TD: {str(e)}"}

        # --- 3. TOOL: get_rml_prefixes ---
        if tool_name == "get_rml_prefixes":
            prefixes = """
    @prefix rml: <http://www.w3.org/ns/rml#> .
    @prefix ql: <http://www.w3.org/ns/rml/ql#> .
    @prefix ex: <http://example.org/> .
    @prefix dct: <http://purl.org/dc/terms/> .
    @prefix saref: <http://www.w3.org/ns/saref#> .
    @prefix geo: <http://www.w3.org/2003/01/geo/wgs84_pos#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix schema: <https://schema.org/> .
    """
            return {"status": "success", "result": prefixes.strip()}

        # --- 4. TOOL: generate_rml_mapping ---
        if tool_name == "generate_rml_mapping":
            csv_analysis = args.get("csv_analysis", "")
            td_analysis = args.get("td_analysis", "")
            csv_file_path = args.get("csv_file_path", "")
            
            if not csv_analysis or not td_analysis or not csv_file_path:
                return {"error": "Missing required arguments: csv_analysis, td_analysis, csv_file_path"}
            
            try:
                from tools.rml_generator import construct_combined_rml_prompt
                prompt = construct_combined_rml_prompt(csv_file_path, csv_analysis, td_analysis)
                return {"status": "success", "result": prompt}
            except Exception as e:
                return {"error": f"Failed to generate RML mapping prompt: {str(e)}"}

        # --- 5. TOOL: validate_rml_syntax ---
        if tool_name == "validate_rml_syntax":
            rml_content = args.get("rml_content", "")
            if not rml_content.strip():
                return {"error": "RML content is empty."}
            
            try:
                from rdflib import Graph
                g = Graph()
                g.parse(data=rml_content, format="turtle")
                return {"status": "success", "message": "RML syntax is valid."}
            except Exception as e:
                return {"status": "error", "message": f"RML syntax error: {str(e)}"}

        # --- 6. TOOL: refine_rml_with_error ---
        if tool_name == "refine_rml_with_error":
            previous_rml = args.get("previous_rml", "")
            error_message = args.get("error_message", "")
            error_type = args.get("error_type", "syntax")
            
            if not previous_rml or not error_message:
                return {"error": "Missing required arguments: previous_rml, error_message"}
            
            try:
                from tools.error_handler import create_refinement_prompt
                prompt = create_refinement_prompt(previous_rml, error_message, error_type)
                return {"status": "success", "result": prompt}
            except Exception as e:
                return {"error": f"Failed to create refinement prompt: {str(e)}"}

        return {"error": f"Unknown tool: {tool_name}"}