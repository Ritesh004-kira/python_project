"""
scripts/train_model.py

Run this standalone script to train (or re-train) the collaborative
filtering model from the current review data in the SQLite database.

Usage:
    venv\\Scripts\\python.exe scripts\\train_model.py
    venv\\Scripts\\python.exe scripts\\train_model.py --epochs 20
"""

import os
import sys
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

def main():
    parser = argparse.ArgumentParser(description="Train the Moctale collaborative filtering model.")
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs (default: 10)")
    args = parser.parse_args()

    from backend.app import create_app
    app = create_app()

    with app.app_context():
        from backend.services.recommendation import recommender
        print("=" * 50)
        print("  Moctale — Collaborative Filtering Training")
        print("=" * 50)

        success = recommender.train_collaborative(epochs=args.epochs)

        if success:
            print("\n[OK] Training complete! Model saved to data/cf_model.keras")
            print("   Restart the Flask app to serve recommendations with the new model.")
        else:
            print("\n[SKIP] Training skipped (TensorFlow unavailable or no review data).")

if __name__ == "__main__":
    main()
