# IELTS Pressure Engine

A smart IELTS Speaking practice application that adapts specifically to your stress levels and fluency. It uses AI to act as a dynamic examiner, increasing pressure when you are comfortable and scaffolding when you struggle.

## Project Structure
- **/backend**: FastAPI server with AI Agents (LangChain, Whisper, Llama-3).
- **/frontend**: Next.js 16 application with Real-time Audio processing and Glassmorphism UI.

## Getting Started

### 1. Backend Setup (Python)

It is recommended to use a virtual environment (`venv`) to keep dependencies clean.

1.  **Navigate to backend:**
    ```bash
    cd backend
    ```

2.  **Create Virtual Environment:**
    ```powershell
    # Windows
    python -m venv venv
    ```

3.  **Activate Virtual Environment:**
    ```powershell
    # Windows (PowerShell)
    .\venv\Scripts\Activate
    
    # Windows (Command Prompt)
    .\venv\Scripts\activate.bat
    
    # Mac/Linux
    source venv/bin/activate
    ```

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run Server:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

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
