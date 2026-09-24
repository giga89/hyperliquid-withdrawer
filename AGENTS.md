# Hyperliquid Withdrawer - Agent Guidelines & Mandatory Rules

## Mandatory Script Verification Rules
1. **Compilation & Syntax Testing**:
   - Always run `python3 -m py_compile` on all modified or newly created `.py` files.
2. **Subprocess Import Testing**:
   - Always test importing every module via `python3 -c "import <module>"` in an isolated subprocess.
3. **Resilience & Graceful Fallbacks**:
   - Terminal styling (like `rich`) and config loaders (like `python-dotenv`) must NEVER cause crashes if missing. Always provide pure standard-library fallbacks.
4. **Environment Isolation Protection**:
   - Always inject system `dist-packages` and user `site-packages` into `sys.path` to prevent failures when invoked inside minimal virtualenvs.
5. **Always Run Tests**:
   - Always execute `pytest -v` or `python3 -m unittest` before delivering results to the user.
