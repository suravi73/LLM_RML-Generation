import os
from prefixes import get_prefix_declarations  

def construct_combined_rml_prompt(csv_file_path, csv_analysis, td_analysis):
    """
    Combines CSV and TD analyses to generate a final RML mapping prompt.
    """
    # Get prefixes as a string
    prefix_declarations = get_prefix_declarations()

    combined_prompt = f"""
You are an expert RML (RDF Mapping Language) generator for sensor data in smart factories. 
Your task is to generate ONLY valid, syntactically correct, and semantically accurate RML mapping rules using **SOSA (Sensor, Observation, Sample, and Actuator Ontology)** and **QUDT**.

### IMPORTANT INSTRUCTIONS:
- OUTPUT ONLY VALID TURTLE SYNTAX. NOTHING ELSE.
- DO NOT RETURN JSON, FUNCTION CALLS, MARKDOWN, EXPLANATIONS, OR ANY TEXT BEFORE/AFTER THE TURTLE.
- DO NOT USE TOOL CALLS.
- START DIRECTLY WITH @prefix declarations.
- DO NOT WRAP IN CODE BLOCKS.

### REQUIRED PREFIXES (MUST BE DECLARED):
{prefix_declarations}

### RML STRUCTURE RULES (MANDATORY):
1. Use ONE TriplesMap for the SENSOR entity (each row = one sensor).
   - Subject: Use rml:template "http://example.org/sensor/{{workstation_id}}"
   - NEVER use rml:reference inside rml:subjectMap — only rml:template or rml:constant
   - Class: sosa:Sensor

2. Use SEPARATE TriplesMaps for OBSERVATIONS (temperature, humidity).
   - Subject: Use rml:template "http://example.org/obs/temp-{{workstation_id}}" (for temp)
   - Subject: Use rml:template "http://example.org/obs/hum-{{workstation_id}}" (for hum)
   - Class: sosa:Observation

3. For sensor properties (name, floor, lat, long, description):
   - Use schema:name, ex:floor, geo:lat, geo:long, dct:description
   - Do NOT use geo:location for floor — use ex:floor instead

4. For observation values:
   - Use sosa:hasSimpleResult for the measured value (e.g., temperature, humidity)
   - Use sosa:observedProperty to link to the QUDT quantitykind (e.g., qudt-quantity:Temperature)
   - Use sosa:madeBySensor to link the observation to its sensor
   - Use qudt:unit to specify the unit (e.g., qudt:DEG_C, qudt:PERCENT)

5. Data Types:
   - Use rml:datatype ONLY with XSD types: xsd:string, xsd:float, xsd:integer
   - NEVER use qudt:DEG_C or any unit as rml:datatype — that is INVALID

6. Units & Properties:
   - Temperature → observedProperty: <http://qudt.org/vocab/quantitykind/Temperature>, unit: qudt:DEG_C
   - Humidity → observedProperty: <http://qudt.org/vocab/quantitykind/DimensionlessRatio>, unit: qudt:PERCENT

7. Do NOT use SAREF, SSN, or WOT-TD prefixes. Use only the prefixes listed above.

8. Every statement MUST end with a period (.).
Every triple map MUST have: rml:logicalSource, rml:subjectMap, and at least one rml:predicateObjectMap.

### CONTEXT:
- CSV File: {os.path.basename(csv_file_path)}
- CSV Analysis: 
{csv_analysis}

- Thing Description Analysis:
{td_analysis}

### CRITICAL SYNTAX RULES:
- NEVER mix RML mapping syntax with actual RDF data syntax
- NEVER output statements like "<uri> a Class; pred obj." outside of TriplesMaps
- Use rml:reference (not rml:column) for CSV columns
- Use angle brackets < > for URIs in rml:constant
- Each rml:predicateObjectMap must have exactly one rml:objectMap


### TASK:
Generate RML mapping with:
1. One TriplesMap for sensors (sosa:Sensor), using workstation_id as template key.
2. One TriplesMap for temperature observations (sosa:Observation).
3. One TriplesMap for humidity observations (sosa:Observation).
4. All values from CSV columns must be mapped using rml:reference.
5. All units must be expressed as qudt:unit triples.
6. All observed properties must be linked to QUDT quantitykind IRIs.

### OUTPUT THE TURTLE NOW (NOTHING ELSE):
"""
    return combined_prompt