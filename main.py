# main.py (refactored with three-prompt approach and self-correction)

import asyncio
import os
import re
import csv
import sys
from xml.etree import ElementTree as ET
from dotenv import load_dotenv
from rdflib import Graph, RDF
from rdflib.exceptions import ParserError
from rdflib.namespace import SH
from pyshacl import validate  
from src.llm_client import ToolLLM

from tools.data_analyzer import construct_data_prompt
from tools.td_analyzer import construct_td_prompt
from tools.rml_generator import construct_combined_rml_prompt
from tools.error_handler import create_refinement_prompt, detect_rml_syntax_errors
'''
from prompt_samples import construct_data_prompt  # Import the prompt function
from prompt_samples import construct_td_prompt  # Import the prompt function
from prompt_samples import create_refinement_prompt  # Import the refinement prompt function
from prompt_samples import construct_combined_rml_prompt  # Import the prompt function

# from prompt import construct_rml_generation_prompt # Import the prompt function'''


# --- Configuration ---
'''TOOL_SERVER_URL = os.getenv("TOOL_SERVER_URL")
if not TOOL_SERVER_URL:
    raise ValueError("TOOL_SERVER_URL environment variable must be set.")
TOOL_SERVER_URL = TOOL_SERVER_URL.strip()'''

TOOL_SERVER_URL = "http://127.0.0.1:8000"

MAX_RETRIES = 3
  

# --- Enhanced Sanitization ---
def extract_turtle(text: str) -> str:
    if not text:
        return ""
    # Remove Python byte-string artifacts: b'...', b"..."
    text = re.sub(r"^b[\"'](.*)[\"']$", r"\1", text.strip(), flags=re.DOTALL)
    text = re.sub(r"\\n", "\n", text)  # unescape newlines
    text = re.sub(r"\\\"", "\"", text)  # unescape quotes
    # Remove markdown fences
    m = re.search(r"```(?:turtle|ttl)?\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Find Turtle start
    m2 = re.search(r"(@prefix|@base|rml:|ql:|ex:|dct:|saref:)", text, re.IGNORECASE)
    if m2:
        return text[m2.start():].strip()
    return text.strip()

def is_valid_prefix_usage(turtle_str: str) -> bool:
    allowed_prefixes = { "rml", "ql", "ex", "dct", "saref"}
    # Find all qnames like dct:title
    qnames = re.findall(r"\b([a-z]+):[a-zA-Z_][a-zA-Z0-9_]*", turtle_str)
    return all(prefix in allowed_prefixes for prefix in qnames)

def is_function_call_response(text: str) -> bool:
    """Check if LLM returned a function call JSON instead of plain text."""
    text = text.strip()
    if text.startswith("{") and '"name":' in text and '"parameters":' in text:
        try:
            import json
            obj = json.loads(text)
            # Check if it's a function call
            return "name" in obj and "parameters" in obj
        except:
            return False
    return False

def extract_content_from_function_call(text: str) -> str:
    """Try to extract meaningful content from function call response."""
    if is_function_call_response(text):
        try:
            import json
            obj = json.loads(text)
            params = obj.get("parameters", {})
            
            # If it's a CSV analysis call, try to extract the CSV file info
            if obj.get("name") == "csv_structure_analysis":
                csv_file = params.get("csv_file", "unknown.csv")
                # Return a plain text summary
                return f"CSV file: {csv_file}\nColumns: {read_csv_headers(csv_file)}"
            
            # If it's a TD analysis call
            elif obj.get("name") == "semantic_analysis":
                return f"TD ID: {params.get('td_id', 'unknown')}\nTD Title: {params.get('td_title', 'unknown')}\nProperties: {params.get('td_properties', 'unknown')}"
            
            # Otherwise, return the original text
            return str(params)
        except:
            return text
    return text

def extract_plain_text_from_llm_response(text: str) -> str:
    """Extract plain text from LLM response, handling function calls."""
    if is_function_call_response(text):
        return extract_content_from_function_call(text)
    return text

def read_csv_headers(path):
    """Reads the first row of a CSV file to get column headers."""
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader) # Get the first row (headers)
    return headers 

# --- Validate Turtle Syntax ---
def validate_turtle_syntax(content: str) -> tuple[bool, str]:
    try:
        g = Graph()
        g.parse(data=content, format="turtle")
        return True, ""
    except ParserError as e:
        return False, f"Turtle syntax error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


# --- Validate RML Semantics with SHACL ---
def validate_rml_shacl(rml_content: str, shacl_path: str) -> tuple[bool, str]:
    try:
        data_graph = Graph()
        data_graph.parse(data=rml_content, format="turtle")

        shacl_graph = Graph()
        shacl_graph.parse(shacl_path, format="turtle")

        conforms, report_graph, _ = validate(
            data_graph,
            shacl_graph=shacl_graph,
            inference="rdfs",
            debug=False
        )

        if conforms:
            return True, ""
        else:
            report_str = ""
            for result in report_graph.subjects(RDF.type, SH.ValidationResult):
                for message in report_graph.objects(result, SH.resultMessage):
                    report_str += f"- {message}\n"
            return False, report_str.strip()

    except Exception as e:
        return False, f"SHACL validation failed: {e}"

async def robust_llm_call(tool_llm, prompt: str, step_name: str, max_retries: int = 3, allow_function_calls: bool = True) -> str:
    """Call LLM with retries and better error handling."""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"   🔄 {step_name} – Attempt {attempt}/{max_retries}")
            response = await tool_llm.ask(prompt)
            response = extract_plain_text_from_llm_response(response)
            
            if not response or "Error:" in response or "LLM API call timed out" in response:
                print(f"   ❌ {step_name} failed: {response[:100]}...")
                if attempt == max_retries:
                    raise RuntimeError(f"{step_name} failed after {max_retries} attempts")
                await asyncio.sleep(1)  # Brief backoff
                continue
            
            # Only check for function calls if not allowed
            if not allow_function_calls and is_function_call_response(response):
                print(f"   ❌ {step_name} returned function call instead of plain text.")
                if attempt == max_retries:
                    raise RuntimeError(f"{step_name} returned invalid format")
                await asyncio.sleep(1)
                continue

            print(f"   ✅ {step_name} succeeded.")
            return response

        except Exception as e:
            print(f"   ❌ {step_name} exception: {e}")
            if attempt == max_retries:
                raise RuntimeError(f"{step_name} failed after {max_retries} attempts: {e}")
            await asyncio.sleep(1)
    
    raise RuntimeError(f"{step_name} failed after {max_retries} attempts")



async def generate_and_refine_rml(tool_llm, csv_file_path, csv_analysis, td_analysis, max_refinement_attempts=3):
    """Generate RML and refine it based on validation errors."""
    current_prompt = construct_combined_rml_prompt(csv_file_path, csv_analysis, td_analysis)
    
    for attempt in range(1, max_refinement_attempts + 1):
        print(f"   🔄 RML Generation – Attempt {attempt}/{max_refinement_attempts}")
        
        try:
            rml_output = await tool_llm.ask(current_prompt)
            rml_output = extract_plain_text_from_llm_response(rml_output)
            
            if is_function_call_response(rml_output):
                raise ValueError("RML generation returned function call instead of Turtle")
            
            # Check for common RML semantic errors first
            if "parentTriplesMap" in rml_output and "childTriplesMap" in rml_output:
                # Check if they're in objectMap (which is wrong)
                import re
                pattern = r'rml:objectMap\s*\[\s*[^]]*rml:parentTriplesMap\s*[^]]*rml:childTriplesMap'
                if re.search(pattern, rml_output, re.DOTALL):
                    error_msg = "Invalid RML: rml:parentTriplesMap and rml:childTriplesMap used in rml:objectMap. This is incorrect syntax for linking resources."
                    print(f"   ❌ RML semantic error: {error_msg[:200]}")
                    if attempt == max_refinement_attempts:
                        raise RuntimeError(f"RML semantic error after {max_refinement_attempts} attempts: {error_msg}")
                    current_prompt = create_refinement_prompt(rml_output, error_msg, "rml_semantic")
                    continue
            
            # Validate syntax
            is_syntax_valid, syntax_error = validate_turtle_syntax(rml_output)
            if not is_syntax_valid:
                error_msg = f"Turtle syntax error: {syntax_error}"
                print(f"   ❌ Syntax error: {error_msg[:200]}")
                if attempt == max_refinement_attempts:
                    raise RuntimeError(f"RML syntax failed after {max_refinement_attempts} attempts: {error_msg}")
                current_prompt = create_refinement_prompt(rml_output, error_msg, "syntax")
                continue

            return rml_output

        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ RML generation error: {error_msg}")
            if attempt == max_refinement_attempts:
                raise RuntimeError(f"RML generation failed after {max_refinement_attempts} attempts: {error_msg}")
            current_prompt = create_refinement_prompt("", error_msg, "generation")
            await asyncio.sleep(1)

    raise RuntimeError("RML refinement failed")


async def main():
    load_dotenv()
    
    # Config
    LLM_BASE_URL = os.getenv("LLM_BASE_URL").strip()
    LLM_API_KEY = os.getenv("OPENAI_API_KEY").strip()
    MODEL = os.getenv("model").strip()
    DATA_FILE = os.getenv("DATA_FILE").strip() # Should be CSV
    TD_FILE = os.getenv("TD_FILE").strip() # Should be JSON
    SHACL_SHAPE_PATH = os.getenv("SHACL_SHAPE_PATH").strip()
    output_mapping_filename = os.getenv("OUTPUT_MAPPING_FILE").strip()
    
    if not os.path.exists(TD_FILE):
        print(f"❌ TD file not found: {TD_FILE}")
        sys.exit(1)
    if not os.path.exists(DATA_FILE):
        print(f"❌ Data file (CSV) not found: {DATA_FILE}")
        sys.exit(1)
    if not os.path.exists(SHACL_SHAPE_PATH):
        print(f"❌ SHACL shape file not found: {SHACL_SHAPE_PATH}")
        sys.exit(1)

    async with ToolLLM(LLM_BASE_URL, LLM_API_KEY, MODEL, TOOL_SERVER_URL) as tool_llm:
        # Perform robust CSV and TD analysis (will exit if either fails)
        try:
            # Step 1: Get analyses
            data_prompt = construct_data_prompt(DATA_FILE)
            csv_analysis = await robust_llm_call(tool_llm, data_prompt, "CSV Analysis", 3, allow_function_calls=True)
            print("data_Analysis:", csv_analysis)

            td_prompt = construct_td_prompt(TD_FILE)
            td_analysis = await robust_llm_call(tool_llm, td_prompt, "TD Analysis", 3, allow_function_calls=True)
            print("td_Analysis:", td_analysis)

            print("✅ Both analyses completed successfully.")

            # Step 2: Generate and refine RML with feedback
            raw_response = await generate_and_refine_rml(tool_llm, DATA_FILE, csv_analysis, td_analysis, 3)

        except Exception as e:
            print(f"\n💥 Analysis or RML generation failed: {e}")
            sys.exit(1)

        # Step 3: Final validation (SHACL only, since syntax should be fixed)
        final_rml = None
        clean_rml = extract_turtle(raw_response)
        if not clean_rml:
            print("❌ Empty RML output after refinement.")
            sys.exit(1)

        # Now validate SHACL (no retry needed unless you want RML semantic refinement too)
        is_shacl_valid, shacl_errors = validate_rml_shacl(clean_rml, SHACL_SHAPE_PATH)
        if not is_shacl_valid:
            print(f"❌ SHACL validation failed:\n{shacl_errors}")
            # Optionally: add another refinement loop for SHACL errors too
            sys.exit(1)

        final_rml = clean_rml

        # Save result
        os.makedirs(os.path.dirname(output_mapping_filename), exist_ok=True)
        with open(output_mapping_filename, "w", encoding="utf-8") as f:
            f.write(final_rml)
        print(f"\n✨ SUCCESS! Valid RML saved to: {output_mapping_filename}")

if __name__ == "__main__":
    asyncio.run(main())