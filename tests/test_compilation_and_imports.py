import os
import sys
import glob
import py_compile
import subprocess
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestCompilationAndImports(unittest.TestCase):
    """
    Mandatory compilation and import smoke tests.
    Ensures that every Python script syntax-compiles cleanly
    and imports without missing module errors.
    """

    def test_all_python_files_compile(self):
        """Verify that every .py file compiles without syntax or indentation errors."""
        py_files = glob.glob(os.path.join(ROOT_DIR, "*.py")) + glob.glob(os.path.join(ROOT_DIR, "tests", "*.py"))
        self.assertGreater(len(py_files), 0, "No Python files found to compile.")

        for py_file in py_files:
            try:
                py_compile.compile(py_file, doraise=True)
            except py_compile.PyCompileError as e:
                self.fail(f"Compilation failed for {py_file}: {e}")

    def test_core_import_in_subprocess(self):
        """Verify core.py can be imported in a clean sub-process."""
        cmd = [sys.executable, "-c", "import core; print('core_ok')"]
        res = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Failed to import core: {res.stderr}")
        self.assertIn("core_ok", res.stdout)

    def test_cli_import_in_subprocess(self):
        """Verify cli.py can be imported in a clean sub-process."""
        cmd = [sys.executable, "-c", "import cli; print('cli_ok')"]
        res = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Failed to import cli: {res.stderr}")
        self.assertIn("cli_ok", res.stdout)

    def test_web_app_import_in_subprocess(self):
        """Verify web_app.py can be imported in a clean sub-process."""
        cmd = [sys.executable, "-c", "import web_app; print('web_ok')"]
        res = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Failed to import web_app: {res.stderr}")
        self.assertIn("web_ok", res.stdout)

    def test_cli_help_flag_runs(self):
        """Verify cli.py --help executes successfully."""
        cmd = [sys.executable, "cli.py", "--help"]
        res = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"cli.py --help failed: {res.stderr}")
        self.assertIn("Hyperliquid Direct DeFi Rescue", res.stdout)

    def test_cli_runs_without_rich_installed(self):
        """Verify cli.py gracefully falls back when rich is not available."""
        code = (
            "import sys; "
            "sys.modules['rich'] = None; "
            "sys.modules['rich.console'] = None; "
            "sys.modules['rich.panel'] = None; "
            "sys.modules['rich.table'] = None; "
            "sys.modules['rich.prompt'] = None; "
            "import cli; "
            "print('fallback_ok')"
        )
        cmd = [sys.executable, "-c", code]
        res = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"cli fallback failed: {res.stderr}")
        self.assertIn("fallback_ok", res.stdout)


if __name__ == "__main__":
    unittest.main()
