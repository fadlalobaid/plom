# Backend

This directory contains the backend services of the Intelligent Lung Disease Diagnosis System, developed using FastAPI.

The backend is responsible for managing business logic, user authentication, patient and doctor data, communication with the AI module, and providing RESTful APIs for the mobile application and administrative dashboard.

## Project structure

```
backend/
├── app/
│   ├── main.py          # FastAPI application entry point
│   ├── core/            # Configuration and shared settings
│   ├── db/              # Database engine and session management
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── api/             # API route handlers
│   ├── services/        # Business logic
│   └── utils/           # Shared utilities
├── venv/
├── requirements.txt
└── README.md
```

## Setup

1. Create and activate a virtual environment (if not already done):

   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment variables as needed (optional):

   ```bash
   # Create a .env file in the backend directory
   ```

## Run the server

From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

- `GET /` — welcome message
- `GET /health` — health check
- `GET /docs` — interactive API documentation
