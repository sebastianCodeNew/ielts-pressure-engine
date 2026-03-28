# IELTS Pressure Engine

A smart IELTS Speaking practice application that adapts specifically to your stress levels and fluency. It uses AI to act as a dynamic examiner, increasing pressure when you are comfortable and scaffolding when you struggle.

## Project Structure

- **/backend**: FastAPI server with AI Agents (LangChain, Whisper, Llama-3).
- **/frontend**: Next.js 16 application with Real-time Audio processing and Glassmorphism UI.

## Getting Started

### 1. Backend Setup (using `uv` - recommended)

This project uses `uv` for ultra-fast dependency management and environment isolation.

1.  **Install `uv` (if not installed):**
    ```powershell
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

2.  **Navigate to backend and sync:**
    ```bash
    cd backend
    uv sync
    ```

3.  **Run Server through `uv`:**
    ```bash
    uv run uvicorn app.main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

### Alternative Backend Setup (Legacy `venv`)

1.  **Navigate to backend:**
    ```bash
    cd backend
    ```

2.  **Create and Activate Virtual Environment:**
    ```powershell
    python -m venv venv
    # PowerShell
    .\venv\Scripts\Activate
    # CMD
    .\venv\Scripts\activate.bat
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run Server:**
    ```bash
    uvicorn app.main:app --reload
    ```

### 2. Frontend Setup (Node.js)

1.  **Navigate to frontend:**
    ```bash
    cd frontend
    ```

2.  **Install Dependencies:**
    ```bash
    npm install
    ```

3.  **Run Development Server:**
    ```bash
    npm run dev
    ```
    Open [http://localhost:3000](http://localhost:3000) in your browser.

## Features

- **Adaptive Pressure**: AI scales difficulty based on your WPM and hesitation.
- **Educational Mode**:
    - **Keyword Chips**: Context-aware vocabulary suggestions.
    - **Model Answers**: Instant Band 7.0+ sample responses.
    - **Feedback**: Detailed examiner notes on your performance.
    - **Indonesian Translation**: Real-time translations for prompts and feedback.
    - **Error Gym**: Targeted remediation drills for chronic grammar errors.
