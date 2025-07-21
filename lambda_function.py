import os
import requests
import openai
import logging
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from datetime import datetime

# Cargar variables de entorno desde .env (para desarrollo local)
load_dotenv()

# Obtener claves y tokens desde variables de entorno
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_ID = os.environ.get("LINKEDIN_PERSON_ID")

openai.api_key = os.environ.get("OPENAI_API_KEY")


# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Archivo temporal para artículos publicados en Lambda
PUBLISHED_ARTICLES_FILE = "/tmp/published_articles.txt"

def is_already_published(url):
    if not os.path.exists(PUBLISHED_ARTICLES_FILE):
        return False
    with open(PUBLISHED_ARTICLES_FILE, "r") as f:
        return url.strip() in [line.strip() for line in f.readlines()]

def mark_as_published(url):
    with open(PUBLISHED_ARTICLES_FILE, "a") as f:
        f.write(url.strip() + "\n")

# Rotación temática semanal de categorías para publicaciones
CATEGORIES = [
    # Semana 1 - Inteligencia Artificial y automatización
    "Artificial Intelligence",
    "Machine Learning",
    "Deep Learning",
    "Natural Language Processing",
    "Computer Vision",
    "Generative AI",
    "Prompt Engineering",

    # Semana 2 - Aplicaciones de IA y Ética
    "AI Agents & Automation",
    "AI Ethics & Regulation",
    "Human-AI Interaction",
    "Robotics",
    "Business Strategy in AI Era",
    "Green Tech with AI",

    # Semana 3 - Ciencia y Tecnología Emergente
    "Scientific Breakthroughs",
    "Quantum Computing",
    "Neuroscience & AI",
    "Emerging Technologies",
    "Cloud Computing",
    "Edge AI",
    "Tech Policy & Regulation",

    # Semana 4 - Fintech y economía digital
    "FinTech",
    "InsurTech",
    "HealthTech",
    "RegTech",
    "Cybersecurity",
    "Blockchain",
    "AI Startups & Innovation"
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
    query = f"{category}"
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
    Devuelve un diccionario con la URL de la imagen y el nombre del autor, o None si no se encuentra.
    """
    search_query = f"minimalist {article.get('title', '')}"
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
              author_name = results[0].get("user", {}).get("name", "")
              return {"image_url": image_url, "author_name": author_name}
    else:
         logger.error(f"Error al buscar imagen en Unsplash: {response.status_code} {response.text}")
    return None

def summarize_and_rewrite(article):
    content = article.get('description', '')
    if len(content.strip()) < 50:
        return article.get('description', 'Not enough content to generate a summary.')
    
    prompt = (
        "Eres un escritor galardonado de noticias tecnológicas, mexicano, ingeniero en inteligencia artificial de 40 años, "
        "con un estilo millennial, provocador, cálido y que disfruta escribir con un toque de humor, ironía y mucha claridad. "
        "Tus publicaciones deben conectar con una audiencia de profesionales tech mexicanos y latinoamericanos en LinkedIn.\n\n"
        "Crea una publicación en español bien redactada, entretenida, accesible para todos los niveles, con un estilo informal pero profesional. "
        "NO comiences la publicación con el título original de la noticia ni lo pongas como encabezado. Si lo deseas, puedes referenciarlo dentro del texto de forma natural.\n\n"
        "NO uses asteriscos para destacar texto. En su lugar, USA MAYÚSCULAS o guiones visuales para resaltar ideas importantes.\n\n"
        "Usa emojis cuando sea adecuado, y separa en párrafos cortos para facilitar la lectura.\n\n"
        "Agrega entre 3 y 5 hashtags relevantes (en español, sin repetir '#IA') y finaliza con una pregunta provocadora o reflexión que motive a la conversación.\n\n"
        "Esta es la descripción de la noticia sobre la cual debes escribir:\n\n" + content
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

def post_to_linkedin_shares(content, image_url=None):
    print(content)

    url = "https://api.linkedin.com/v2/shares"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "owner": f"urn:li:person:{LINKEDIN_PERSON_ID}",
        "text": {"text": content}
    }

    if image_url:
        payload["content"] = {
            "contentEntities": [
                {
                    "entityLocation": image_url,
                    "thumbnails": [{"resolvedUrl": image_url}]
                }
            ],
            "title": "Imagen relacionada"
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
        url = article.get("url")
        if is_already_published(url):
            logger.info(f"Artículo ya publicado, se omite: {url}")
            continue
        logger.info(f"Procesando artículo: {article.get('title')}")
        summary = summarize_and_rewrite(article)
        post_content = (
            f"{article.get('title')}\n\n"
            f"{summary}\n\n"
            f"Fuente: {article.get('url')}"
        )
        image_info = fetch_image_for_article(article)
        image_url = image_info["image_url"] if image_info else None
        author_credit = f"\n📸 Imagen de {image_info['author_name']} vía Unsplash" if image_info and image_info.get("author_name") else ""
        post_to_linkedin_shares(post_content + author_credit, image_url=image_url)
        mark_as_published(url)

def lambda_handler(event, context):
    main()
    return {
        "statusCode": 200,
        "body": "Ejecución finalizada correctamente."
    }