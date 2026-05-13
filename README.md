---
title: Mera Cinema
emoji: 🎬
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Mera Cinema - AI Powered Movie Recommendations

Mera Cinema is a modular, production-grade hybrid recommendation engine for movies.

## Features
- **Hybrid Engine**: Combines Popularity, Content-Based, and Collaborative filtering.
- **Personalized Recommendations**: Log in to see movies tailored to your taste.
- **Caching**: Results are cached for high performance.
- **Modern UI**: Clean, responsive design with a "Glassmorphism" aesthetic.

## Deployment
This project is configured for deployment on **Railwayapp**.

### Local Setup
1. Create a virtual environment: `python -m venv venv`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `python app.py`

### AI Models
The collaborative filtering engine uses a trained Keras model located in `backend/data/cf_model.keras`.
