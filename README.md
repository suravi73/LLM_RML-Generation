# RML-Generator

![Static Badge](https://img.shields.io/badge/RMLGenerator-purple) ![Static Badge](https://img.shields.io/badge/python-3.8-yellow?logo=python&logoColor=white&labelColor=blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

### How to Run the Project 
Now this application runs as two separate processes.

 **Terminal 1: Run the Tool Server**
In the project's root directory (rml-generator/), run:

```bash
python src/api_server.py
```

The output will be from uvicorn and the UniversalToolServer says it's connected and listening on http://127.0.0.1:8000.

 **Terminal 2: Run the Client**
While the server is running, open a second terminal in the same directory and run:

```Bash
python main.py
```

