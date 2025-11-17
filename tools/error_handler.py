def create_refinement_prompt(previous_output: str, error_message: str, error_type: str) -> str:
    """Create a prompt that asks the LLM to fix its previous output based on an error."""
    if error_type == "syntax":
        return f"""
Your previous RML output had a Turtle syntax error:

ERROR: {error_message}

COMMON CAUSES:
- Using a prefix (like 'schema:', 'xsd:') without declaring it with @prefix
- Missing period (.) at the end of statements
- Unbalanced brackets or quotes
- Invalid Turtle syntax

REQUIREMENTS FOR CORRECT OUTPUT:
- You MUST declare ALL prefixes you use (rml, ql, ex, dct, saref, geo, xsd, schema, etc.)
- The schema prefix is: @prefix schema: <https://schema.org/> .
- The xsd prefix is: @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
- Every statement must end with a period (.)
- Output ONLY valid Turtle. NO explanations.

Fix the error and output the corrected RML now:
"""
    elif error_type == "rml_semantic":
        return f"""
Your previous RML output had a semantic error:

ERROR: {error_message}

CRITICAL RML SYNTAX RULES:
- NEVER use rml:parentTriplesMap and rml:childTriplesMap inside rml:objectMap
- rml:parentTriplesMap/rml:childTriplesMap are for JOINING data sources, not for linking subjects
- To link a subject to another resource, use rml:template or rml:constant in rml:objectMap
- Use rml:reference (not rml:column) for CSV column names
- Use angle brackets < > for URIs, not quotes " "
- Each rml:predicateObjectMap must have exactly one rml:objectMap

CORRECT SYNTAX:
# To link to another resource:
rml:objectMap [
    rml:template "uri-template";
    rml:termType rml:IRI
]

# For CSV column values:
rml:objectMap [
    rml:reference "column_name";
    rml:datatype xsd:float
]

# For constant values:
rml:objectMap [
    rml:constant <uri_value>
]
or
rml:objectMap [
    rml:constant "literal_value"
]

Fix the RML syntax and output the corrected version:
"""
    elif error_type == "rml_syntax":
        return f"""
Your RML output has syntax errors:

ERROR: {error_message}

CRITICAL RML SYNTAX RULES:
- NEVER use rml:iterator for CSV files (only use rml:referenceFormulation ql:CSV)
- NEVER use rml:object (always use rml:objectMap with nested properties)
- Use angle brackets < > for URIs in rml:constant
- Use proper SAREF units: saref:Celsius, saref:Percentage, saref:Temperature, saref:Humidity
- Use rml:reference (not rml:column) for CSV column names
- Each TriplesMap must have rml:logicalSource, rml:subjectMap, and rml:predicateObjectMap
- Always specify rml:class for your subjects when using SAREF (not rml:classifier)
- Use proper template syntax with double braces: {{timestamp}} → {{timestamp}}

CORRECT SYNTAX:
# Valid CSV source:
rml:logicalSource [
    rml:source "file.csv";
    rml:referenceFormulation ql:CSV
]

# Valid object mapping:
rml:objectMap [
    rml:constant "value"  # or rml:reference "column"
]

Fix the RML syntax and output the corrected version:
"""
    else:
        return f"""
Your previous output was invalid:

ERROR: {error_message}

Fix this and output ONLY valid Turtle RML with proper prefix declarations.
"""

def detect_rml_syntax_errors(rml_output: str) -> tuple[bool, str]:
    """Detect common RML syntax errors in LLM output."""
    
    # Check for rml:classifier
    if "rml:classifier" in rml_output:
        return False, "Invalid RML: rml:classifier should be rml:class"
    
    # Check for double object specification
    import re
    # Look for pattern: rml:predicate ... rml:object ... rml:objectMap
    double_object_pattern = r'rml:predicate\s+[^;]*rml:object\s+[^;]*rml:objectMap'
    if re.search(double_object_pattern, rml_output, re.DOTALL):
        return False, "Invalid RML: Cannot have both rml:object and rml:objectMap in same predicateObjectMap"
    
    # Check for wrong SAREF unit URIs
    if "skos-reference/skos.html#Celsius" in rml_output:
        return False, "Invalid URI: Use saref:Celsius instead of http://www.w3.org/2009/08/skos-reference/skos.html#Celsius"
    if "skos-reference/skos.html#Percent" in rml_output:
        return False, "Invalid URI: Use saref:Percentage instead of http://www.w3.org/2009/08/skos-reference/skos.html#Percent"
    
    # Check for invalid iterator
    if "rml:iterator" in rml_output:
        return False, "Invalid RML: Use rml:referenceFormulation ql:CSV for CSV files, not rml:iterator"
    
    return True, ""

