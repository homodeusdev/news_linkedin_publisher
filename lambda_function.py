import os
import requests
import openai
import logging
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional

# Cargar variables de entorno desde .env (para desarrollo local)
load_dotenv()

# Obtener claves y tokens desde variables de entorno
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_ID = os.environ.get("LINKEDIN_PERSON_ID")

openai.api_key = os.environ.get("OPENAI_API_KEY")

LINKEDIN_VERSION = "202506"
HEADERS_LI = {
    "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
    "LinkedIn-Version": LINKEDIN_VERSION,
    "X-Restli-Protocol-Version": "2.0.0"
}

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

def download_image(image_url: str) -> bytes:
    response = requests.get(image_url, timeout=10)
    response.raise_for_status()
    return response.content


def upload_image_to_linkedin(image_bytes: bytes) -> str:
    # Per Images API, only the owner field is allowed in initializeUploadRequest.
    init_body = {
        "initializeUploadRequest": {
            "owner": f"urn:li:person:{LINKEDIN_PERSON_ID}"
        }
    }
    init_res = requests.post(
        "https://api.linkedin.com/rest/images?action=initializeUpload",
        headers=HEADERS_LI,
        json=init_body,
        timeout=10
    )
    init_res.raise_for_status()
    data = init_res.json()["value"]
    upload_url = data["uploadUrl"]
    image_urn = data["image"]

    put_headers = {"Content-Type": "application/octet-stream"}
    put = requests.put(upload_url, headers=put_headers, data=image_bytes, timeout=30)
    put.raise_for_status()
    return image_urn


def post_to_linkedin_ugc(text: str, image_urn: Optional[str] = None, alt_text: Optional[str] = None) -> str:
    share_media_category = "NONE" if image_urn is None else "IMAGE"
    media_block = []
    if image_urn:
        media_block.append({
            "status": "READY",
            "media": image_urn,
            "altText": alt_text or ""
        })

    body = {
        "author": f"urn:li:person:{LINKEDIN_PERSON_ID}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": share_media_category,
                "media": media_block
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    res = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=HEADERS_LI,
        json=body,
        timeout=10
    )
    res.raise_for_status()
    return res.json()["id"]


def comment_with_link(ugc_urn: str, url: str):
    payload = {
        "actor": f"urn:li:person:{LINKEDIN_PERSON_ID}",
        "message": {"text": url}
    }
    comments_url = f"https://api.linkedin.com/v2/socialActions/{ugc_urn}/comments"
    res = requests.post(comments_url, headers=HEADERS_LI, json=payload, timeout=10)
    res.raise_for_status()

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
            "Link en el primer comentario 👇"
        )
        image_info = fetch_image_for_article(article)
        image_url = image_info["image_url"] if image_info else None
        author_credit = (
            f"\n📸 Imagen de {image_info['author_name']} vía Unsplash"
            if image_info and image_info.get("author_name") else ""
        )

        # Generate alt‑text
        alt_prompt = (
            f"Describe brevemente (<=120 caracteres) la imagen para un público tech latino: "
            f"{article.get('title')}"
        )
        alt_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": alt_prompt}],
            max_tokens=60,
            temperature=0.4
        )
        alt_text = alt_response.choices[0].message.content.strip()

        # Upload image if present
        image_urn = None
        if image_url:
            img_bytes = download_image(image_url)
            image_urn = upload_image_to_linkedin(img_bytes)

        # Publish the UGC post
        ugc_urn = post_to_linkedin_ugc(post_content + author_credit, image_urn, alt_text)

        # Add original link in the first comment
        comment_with_link(ugc_urn, article.get("url"))

        mark_as_published(url)

def lambda_handler(event, context):
    main()
    return {
        "statusCode": 200,
        "body": "Ejecución finalizada correctamente."
    }