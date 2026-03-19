# Terminal Rules

- **Every single terminal command** must always activate the virtual environment first, regardless of what the command is (Python, npm, git, pip, or any other command).
- The `venv` is located inside the `backend` folder: `backend/venv`
- Always prepend `backend\venv\Scripts\activate;` before any command.
- Example: `backend\venv\Scripts\activate; <any_command_here>`
- If the `venv` directory does not exist, create it first using `python -m venv backend/.venv` before proceeding.

