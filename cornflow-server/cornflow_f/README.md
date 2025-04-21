# Cornflow FastAPI Hello World

A minimal FastAPI application for Cornflow.

## Setup

1. Create a virtual environment:

```bash
python -m venv venv
```

2. Activate the virtual environment:

- Windows:

```bash
.\venv\Scripts\activate
```

- Unix/MacOS:

```bash
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

Start the server with:

```bash
uvicorn main:app --reload
```

The other form to run the application (from the cornflow-server folder):

```bash
fastapi dev cornflow_f/main.py
```

The application will be available at http://localhost:8000

## API Endpoints

- GET `/`: Returns a hello world message
- GET `/hello/{name}`: Returns a personalized hello message

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Run the tests

To run the unit tests you have to execute the following command from the cornflow-server folder:

```bash
pytest cornflow_f/tests/unit/ -v --cov=cornflow_f --cov-report=term-missing

```
