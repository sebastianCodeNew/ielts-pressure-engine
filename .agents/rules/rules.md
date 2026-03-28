---
trigger: always_on
glob:
description:
---

# Terminal Rules

- **Every single terminal command** must always activate the virtual environment first, regardless of what the command is (Python, npm, git, pip, or any other command).
- The `venv` is located inside the `backend` folder: `backend/venv`
- Always prepend `backend\venv\Scripts\activate;` before any command.
- Example: `backend\venv\Scripts\activate; <any_command_here>`
- If the `venv` directory does not exist, create it first using `python -m venv backend/.venv` before proceeding.
- use uv

## Project Rules

- This project is for single user only, so no need to worry about multi-user access.
- This project is only for me that i use to run in my local machine and using chrome browser.
- No need to add more fitures we focus on the current features and make it better by fixing bugs and improving performance.
- when i say check bug and error possibilities, dont add anything focus on find the bug and error dont add more features
- the target band is always 9
