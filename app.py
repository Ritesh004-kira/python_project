"""
app.py — Project entrypoint for Vercel and Local Development
"""
import sys, os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app

# Create the application instance for WSGI servers (like Vercel)
app = create_app()

if __name__ == '__main__':
    # Used for local development
    app.run(debug=True, port=5000)
