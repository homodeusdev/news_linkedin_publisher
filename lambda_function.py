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

openai.api_key = OPENAI_API_KEY

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
        return url.strip() in (line.strip() for line in f)

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
    """
    category = select_category()
    logger.info(f"Categoría seleccionada para hoy: {category}")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": category,
        "language": "en",
        "sortBy": "relevancy",
        "apiKey": NEWSAPI_KEY,
        "pageSize": 5
    }
    resp = requests.get(url, params=params)
    if resp.status_code == 200:
        articles = resp.json().get("articles", [])
        logger.info(f"Se encontraron {len(articles)} artículos.")
        return articles
    else:
        logger.error(f"Error al obtener noticias: {resp.status_code} {resp.text}")
        return []

def fetch_image_for_article(article):
    """
    Busca una imagen alusiva para la noticia usando Unsplash API.
    """
    query = f"minimalist {article.get('title','')}"
    url = "https://api.unsplash.com/search/photos"
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        logger.error("UNSPLASH_ACCESS_KEY no configurado.")
        return None
    headers = {"Authorization": f"Client-ID {key}"}
    resp = requests.get(url, params={"query": query, "per_page":1}, headers=headers)
    if resp.status_code == 200:
        results = resp.json().get("results", [])
        if results:
            img = results[0]
            return {
                "image_url": img["urls"]["regular"],
                "author_name": img["user"]["name"]
            }
    else:
        logger.error(f"Error Unsplash: {resp.status_code} {resp.text}")
    return None

def download_image(image_url: str) -> bytes:
    resp = requests.get(image_url, timeout=10)
    resp.raise_for_status()
    return resp.content

def upload_image_to_linkedin(image_bytes: bytes) -> str:
    # Inicializa upload (solo owner permitido)
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

    # Subida binaria
    put_headers = {"Content-Type": "application/octet-stream"}
    put = requests.put(upload_url, headers=put_headers, data=image_bytes, timeout=30)
    put.raise_for_status()
    return image_urn

def post_to_linkedin_ugc(text: str, image_urn: Optional[str] = None) -> str:
    """
    Publica un UGC Post. Si image_urn es None → solo texto;
    si image_urn existe → adjunta la imagen.
    """
    if image_urn:
        share_content = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "IMAGE",
            "media": [
                {"status": "READY", "media": image_urn}
            ]
        }
    else:
        share_content = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "NONE"
        }

    body = {
        "author": f"urn:li:person:{LINKEDIN_PERSON_ID}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": share_content
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    headers = {**HEADERS_LI, "Content-Type": "application/json"}
    res = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=body,
        timeout=10
    )
    try:
        res.raise_for_status()
    except requests.HTTPError:
        logger.error(f"UGC error {res.status_code}: {res.text}")
        raise
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
    content = article.get("description","")
    if len(content) < 50:
        return content or "Not enough content to summarize."
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
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":prompt}],
        max_tokens=600,
        temperature=0.7
    )
    return resp.choices[0].message.content.strip()

def main():
    articles = fetch_news()
    if not articles:
        logger.info("No hay artículos.")
        return

    for article in articles:
        url = article.get("url")
        if is_already_published(url):
            continue

        summary = summarize_and_rewrite(article)
        post_content = (
            f"{article.get('title')}\n\n"
            f"{summary}\n\n"
            "Link en el primer comentario 👇"
        )

        img_info = fetch_image_for_article(article)
        image_urn = None
        author_credit = ""
        if img_info:
            img_bytes = download_image(img_info["image_url"])
            image_urn = upload_image_to_linkedin(img_bytes)
            author_credit = f"\n📸 Imagen de {img_info['author_name']} vía Unsplash"

        ugc_urn = post_to_linkedin_ugc(post_content + author_credit, image_urn)
        comment_with_link(ugc_urn, url)
        mark_as_published(url)

def lambda_handler(event, context):
    main()
    return {"statusCode": 200, "body": "Ejecución finalizada correctamente."}