# UniScout AI

A professional college information assistant that provides accurate data by scouting official university websites and verified third-party aggregators in real-time.

## Core Capabilities

- Official Source Detection: Automatically identifies official university domains while filtering out unreliable sources.
- Dynamic Data Acquisition: Scrapes and analyzes college data on-demand to ensure the most current information.
- RAG-Enhanced Intelligence: Utilizes Retrieval-Augmented Generation (RAG) with Google Gemini or Groq (Llama 3) for grounded, factual responses.
- Targeted Information Retrieval: Specific focus on admissions, fee structures, placement statistics, and campus facilities.

## Technical Architecture

- **Frontend**: React 19, Tailwind CSS 4, Vite
- **Backend**: FastAPI (Python 3.12)
- **Database**: PostgreSQL / SQLite (SQLAlchemy)
- **Intelligence**: Google Gemini / Groq (Llama 3.3 70B)
- **Automation**: Playwright (Dynamic Scraping), Search Services

## Setup and Installation

### Prerequisites

- Node.js 18.0 or higher
- Python 3.12 or higher
- Playwright dependencies

### 1. Backend Configuration

Navigate to the backend directory and set up the Python environment:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

Create a `.env` file in the `backend/` directory:

```env
DATABASE_URL=sqlite:///./college_bot.db
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key (optional)
USE_GROQ=True (optional)
```

Start the backend server:

```bash
uvicorn app.main:app --reload
```

### 2. Frontend Configuration

Navigate to the frontend directory and install dependencies:

```bash
cd ../frontend
npm install
```

Start the development server:

```bash
npm run dev
```

The application will be accessible at `http://localhost:5173`.

## System Workflow

1. **Discovery**: Identify the correct university website from the user's query.
2. **Analysis**: Classify the intent (e.g., Placements, Fees) to target specific data points.
3. **Scouting**: Execute a dynamic scrape using Playwright for high-fidelity data extraction.
4. **Synthesis**: Combine official data with aggregator insights to provide a comprehensive analysis.
5. **Response**: Deliver an AI-generated answer grounded strictly in the acquired evidence.

## Maintenance

To clear the local knowledge base, delete the `college_bot.db` file in the backend directory. The system will automatically rebuild it on the next query.
