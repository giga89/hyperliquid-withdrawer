# Script Compilation and Import Testing Rule

Whenever creating, modifying, or refactoring executable scripts (Python, Shell, JavaScript, etc.):

1. **Mandatory Syntax / Compilation Verification**:
   - For Python: Always run `python3 -m py_compile <file.py>` on all created or edited files before reporting completion.
   - Ensure zero syntax, indentation, or parsing errors.

2. **Mandatory Isolated Subprocess Import Smoke Tests**:
   - Always verify that the script can be imported in a clean sub-process: `python3 -c "import <module>"`
   - Ensure all third-party dependencies are either guaranteed present or have graceful pure-Python fallbacks.

3. **Graceful Fallbacks for Terminal / Optional Libraries**:
   - Never let a script crash on optional terminal libraries (e.g., `rich`, `colorama`, `dotenv`).
   - Implement pure Python standard library fallbacks (plain `print`, `input`, basic text tables) whenever optional packages are not installed.

4. **Robust Path Resolution**:
   - Ensure `sys.path` contains both user site-packages (`~/.local/lib/python.../site-packages`) and system dist-packages (`/usr/lib/python3/dist-packages`), ensuring reliability even in stripped virtual environments.

5. **Automated Test Suite Execution**:
   - Always run the test suite (`pytest` or `python3 -m unittest`) and ensure 100% of tests pass before completing the turn.
