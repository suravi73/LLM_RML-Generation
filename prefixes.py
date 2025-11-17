
PREFIXES = {
    "rml": "http://www.w3.org/ns/rml#",
    "ql": "http://www.w3.org/ns/rml/ql#",
    "ex": "http://example.org/",
    "dct": "http://purl.org/dc/terms/",
    "sosa": "http://www.w3.org/ns/sosa/",            
    "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "schema": "https://schema.org/",
    "qudt": "http://qudt.org/vocab/unit/",
    "qudt-quantity": "http://qudt.org/vocab/quantity#"  # for observable properties
}

def get_prefix_declarations():
    """Returns a string of all prefix declarations in Turtle syntax."""
    return "\n".join(f"@prefix {prefix}: <{uri}> ." for prefix, uri in PREFIXES.items())

def get_prefix_dict():
    """Returns the raw prefix dictionary."""
    return PREFIXES.copy()