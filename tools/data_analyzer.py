import csv
import os

def read_csv_headers(path: str) -> list[str]:
    """Reads the first row of a CSV file to get column headers."""
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)  # Get the first row (headers)
    return headers

def construct_data_prompt(csv_file_path: str) -> str:
    """
    Constructs a prompt focused on CSV data structure analysis.
    """
    csv_headers = read_csv_headers(csv_file_path)
    
    data_prompt = f"""
You are a data structure analyzer. Provide only plain text analysis of the following CSV file. DO NOT return any JSON, function calls, or structured responses. Just plain text.

### CSV File: {os.path.basename(csv_file_path)}
### Column Headers: {csv_headers}

Analyze the CSV structure and provide:
1. A list of each column with its likely semantic meaning
2. Identification of potential key columns (IDs, names, etc.)
3. Notes on data types and potential mapping candidates
4. Any special data types like geospatial or temporal

Plain text analysis:
"""
    return data_prompt