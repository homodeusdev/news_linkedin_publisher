import os
import requests
import openai
import logging
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from datetime import datetime

# Cargar variables de entorno desde .env (para desarrollo local)
load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Obtener claves y tokens desde variables de entorno
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_ID = os.environ.get("LINKEDIN_PERSON_ID")

openai.api_key = os.environ.get("OPENAI_API_KEY")

# Lista de 28 categorías diversas para profesionales en LinkedIn
CATEGORIES = [
    "Artificial Intelligence",
    "Machine Learning",
    "Data Science",
    "Big Data",
    "Deep Learning",
    "Natural Language Processing",
    "Computer Vision",
    "Robotics",
    "Cybersecurity",
    "Cloud Computing",
    "Internet of Things",
    "Blockchain",
    "Quantum Computing",
    "Augmented Reality",
    "Virtual Reality",
    "Edge Computing",
    "Software Development",
    "DevOps & Automation",
    "Data Analytics",
    "FinTech",
    "HealthTech",
    "Economy",
    "Business Strategy",
    "Digital Marketing",
    "Green Tech & Sustainability",
    "Telecommunications",
    "Gaming & Esports",
    "Emerging Technologies"
]

def select_category():
    """Selecciona una categoría basada en el día del año."""
    day_of_year = datetime.now().timetuple().tm_yday
    index = (day_of_year - 1) % len(CATEGORIES)
    return CATEGORIES[index]

def fetch_news():
    """
    Obtiene noticias usando NewsAPI para la categoría seleccionada del día.
    Se incluyen palabras clave generales para ampliar el alcance.
    """
    category = select_category()
    logger.info(f"Categoría seleccionada para hoy: {category}")
    url = "https://newsapi.org/v2/everything"
    query = f"{category} OR 'Artificial Intelligence' OR 'Data Science' OR 'Machine Learning' OR 'Deep Learning'"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "relevancy",
        "apiKey": NEWSAPI_KEY,
        "pageSize": 5
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        articles = data.get("articles", [])
        logger.info(f"Se encontraron {len(articles)} artículos para la categoría {category}.")
        return articles
    else:
        logger.error(f"Error al obtener noticias: {response.status_code} {response.text}")
        return []

def fetch_image_for_article(article):
    """
    Busca una imagen alusiva para la noticia usando Unsplash API, basándose en el título.
    Devuelve la URL de la imagen, o None si no se encuentra.
    """
    search_query = article.get("title", "")
    url = "https://api.unsplash.com/search/photos"
    params = {
         "query": search_query,
         "per_page": 1
    }
    unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not unsplash_key:
        logger.error("UNSPLASH_ACCESS_KEY no está configurado en las variables de entorno.")
        return None
    headers = {"Authorization": f"Client-ID {unsplash_key}"}
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
         data = response.json()
         results = data.get("results", [])
         if results:
              image_url = results[0].get("urls", {}).get("regular", "")
              return image_url
    else:
         logger.error(f"Error al buscar imagen en Unsplash: {response.status_code} {response.text}")
    return None

def summarize_and_rewrite(article):
    """
    Genera un post bilingüe (English/Spanish) a partir de la noticia,
    manteniendo un estilo casual de un millennial cuarentón.
    El post incluirá un encabezado, un resumen en inglés y un resumen en español.
    """
    content = f"{article.get('title', '')}\n{article.get('description', '')}"
    if len(content.strip()) < 50:
        return article.get('description', 'Not enough content to generate a summary.')
    
    prompt = (
        "You are an award-winning tech news writer and a 40-year-old millennial machine learning engineer with a casual, professional tone. "
        "Generate a highly engaging, bilingual post (in English and Spanish) summarizing the following news. Your output must follow this exact format:\n\n"
        "HEADER (EN/ES): [A bold, catchy headline in English and Spanish]\n\n"
        "SUMMARY (EN): [A concise and engaging summary in English]\n\n"
        "RESUMEN (ES): [A concise and engaging summary in Spanish]\n\n"
        "SOURCE: [News URL]\n\n"
        "Now, summarize the following news while preserving its meaning:\n\n" + content
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional tech news writer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.7
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"Error al resumir el artículo: {e}")
        return "Error generating summary 😢."

def post_to_linkedin_shares(content):
    print(content)

    url = "https://api.linkedin.com/v2/shares"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "owner": f"urn:li:person:{LINKEDIN_PERSON_ID}",
        "text": {
            "text": content
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        logger.info("Publicación en LinkedIn (Shares) realizada con éxito ✅.")
    else:
        logger.error(f"Error al publicar en LinkedIn (Shares): {response.status_code} {response.text}")

def main():
    articles = fetch_news()
    print(articles)
    if not articles:
        logger.info("No se encontraron artículos para procesar.")
        return

    for article in articles:
        logger.info(f"Procesando artículo: {article.get('title')}")
        summary = summarize_and_rewrite(article)
        post_content = (
            f"{article.get('title')}\n\n"
            f"{summary}\n\n"
            f"Fuente: {article.get('url')}"
        )
        post_to_linkedin_shares(post_content)

def lambda_handler(event, context):
    main()
    return {
        "statusCode": 200,
        "body": "Ejecución finalizada correctamente."
    }
