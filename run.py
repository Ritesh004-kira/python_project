"""
run.py  —  Project entrypoint
Run from the python_project/ root with:
    venv\\Scripts\\python.exe run.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
