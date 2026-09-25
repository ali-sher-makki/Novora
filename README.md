# NOVORA

An e-commerce platform for Eastern and Western fashion, extended with an AI-powered styling engine — customers get personalized outfit recommendations based on their actual body measurements, plus an AI shopping assistant for fashion advice and support questions.

## Features

- **Product catalog** — Eastern and Western wear, multiple sizes, multiple images per product, stock tracking
- **Cart & wishlist** — add, remove, and save items for later
- **Checkout** — Cash-on-Delivery order flow with order history and tracking
- **Product reviews**
- **AI Stylist** — customer enters their body measurements (bust/chest, waist, hips, height); the app calculates their body shape (e.g. Hourglass, Pear, Rectangle for women; Trapezoid, Triangle, Oval for men), generates a personalized styling note via an LLM, and recommends matching products pulled live from the store's own inventory
- **AI Chatbot** — an LLM-powered assistant that answers fashion questions and FAQs (shipping, returns, Cash-on-Delivery)
- **User accounts** — registration, login, and profile management

## Tech Stack

- **Backend:** Django, Python
- **Database:** SQLite (development)
- **AI:** OpenRouter API (LLM access for the Stylist and Chatbot features)
- **Other:** Pillow (image handling), python-dotenv, Gunicorn, Whitenoise

## Getting Started

### Prerequisites
- Python 3.11+
- pip

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/ali-sher-makki/Novora.git
   cd Novora
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # macOS/Linux
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file inside the `novora/` directory with:
   ```
   DJANGO_SECRET_KEY=your-django-secret-key-here
   chatbot_API_Key=your-openrouter-api-key-here
   ```
   > Get a free/paid API key at [openrouter.ai](https://openrouter.ai). Without it, the chatbot falls back to a default message and the AI Stylist falls back to a template-based note — the rest of the site still works normally.

5. Move into the project folder, run migrations, and start the server:
   ```
   cd novora
   python manage.py migrate
   python manage.py runserver
   ```

6. Visit `http://127.0.0.1:8000/` in your browser.

## Project Structure

```
novora/
├── manage.py
├── novora/            # Django project settings, URLs, WSGI/ASGI
└── store/              # Main app: products, cart, wishlist, orders,
                         # AI Stylist & Chatbot views, templates
```

## Author

**Ali Sher Makki**
- GitHub: [github.com/ali-sher-makki](https://github.com/ali-sher-makki)
- LinkedIn: [linkedin.com/in/ali-sher-0a2a78266](https://www.linkedin.com/in/ali-sher-0a2a78266)
- Upwork: [upwork.com/freelancers/~017c5d404ff0c6ab67](https://www.upwork.com/freelancers/~017c5d404ff0c6ab67)

This project is shared for portfolio and demonstration purposes.
