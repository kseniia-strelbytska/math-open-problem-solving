# Code Comparison Web Server

A fast, lightweight web server built with Python and FastAPI to compare code snippets and highlight differences.

## Quick Start

### Prerequisites
* Python 3.8+
* pip (Python package manager)

### Installation
Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd <repo-folder>
```
Install dependencies:

   ```bash
pip install -r requirements.txt
```
Running the Server
Start the server using Uvicorn:

   ```bash
uvicorn main:app --reload
```
The server will be available at: http://127.0.0.1:8000

###  Usage
Interactive API Documentation
Once the server is running, you can explore and test the API endpoints directly via the Swagger UI:
http://127.0.0.1:8000/docs

Example Request
You can test the comparison endpoint using curl:

```bash
curl -X 'POST' \
  http://127.0.0.1:8000/compare \
  -H 'Content-Type: application/json' \
  -d '{
  "code1": "print(\"hello\")",
  "code2": "print(\"hello world\")"
}'
```