# Personal AI Finance

## Project Overview
This project is an AI-powered personal finance management system.

## Local Development URLs

Here are the local addresses for the various services running in the development environment:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | [http://localhost:3000](http://localhost:3000) | Main user interface (Next.js) |
| **Backend API** | [http://localhost:8000](http://localhost:8000) | FastAPI backend server |
| **API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive API documentation |
| **Inngest Dev Server** | [http://localhost:8288](http://localhost:8288) | Dashboard for viewing and testing workflows |

## Getting Started

### Prerequisites
- Node.js & npm
- Python 3.10+

### Installation

1. **Install Node.js dependencies:**
   ```bash
   npm install
   # This installs root dependencies (like concurrently) and workspace dependencies
   ```

2. **Setup Python Environment:**
   ```bash
   # Create a virtual environment (if not already created)
   python3 -m venv .venv

   # Activate the virtual environment
   source .venv/bin/activate

   # Install backend requirements
   pip install -r backend/requirements.txt
   ```

### Running the Project

To start all services (Frontend, Backend, and Inngest) simultaneously:

```bash
npm run dev
```

This command runs `concurrently` to launch:
- `npm:dev:frontend`
- `npm:dev:backend`
- `npm:dev:inngest`
