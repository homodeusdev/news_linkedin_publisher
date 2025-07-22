import os
import requests
import openai
import logging
from dotenv import load_dotenv
from datetime import datetime
import random
import json
import re
from typing import List

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

# Rotación temática semanal de bloques (5 bloques, uno por día laboral)
CATEGORY_BLOCKS = [
    # Bloque 1 – Inteligencia Artificial y automatización
    [
        "Artificial Intelligence",
        "Machine Learning",
        "Deep Learning",
        "Natural Language Processing",
        "Computer Vision",
        "Generative AI",
        "Prompt Engineering",
    ],
    # Bloque 2 – Aplicaciones de IA y Ética
    [
        "AI Agents & Automation",
        "AI Ethics & Regulation",
        "Human-AI Interaction",
        "Robotics",
        "Business Strategy in AI Era",
        "Green Tech with AI",
    ],
    # Bloque 3 – Ciencia y Tecnología Emergente
    [
        "Scientific Breakthroughs",
        "Quantum Computing",
        "Neuroscience & AI",
        "Emerging Technologies",
        "Cloud Computing",
        "Edge AI",
        "Tech Policy & Regulation",
    ],
    # Bloque 4 – FinTech y economía digital
    [
        "FinTech",
        "InsurTech",
        "HealthTech",
        "RegTech",
        "Cybersecurity",
        "Blockchain",
        "AI Startups & Innovation",
    ],
    # Bloque 5 – Economía y FinTech en México
    [
        "Economía México",
        "Finanzas Personales MX",
        "FinTech México",
        "Pagos Digitales MX",
        "Banca Digital México",
        "Inclusión Financiera MX",
        "Cripto en México",
        "CNBV Regulación",
        "Startups Financieras MX",
    ],
]

# Palabras gatillo para calcular controversy_score
CONTROVERSY_KEYWORDS = [

    # Bloque 1 – IA y Automatización
    "sesgo", "bias",
    "desempleo", "job loss", "layoff", "automation layoffs",
    "deepfake", "deep fake",
    "killer robot", "killer robots",
    "privacy", "privacidad", "vigilancia", "surveillance",
    "copyright", "plagio", "lawsuit", "demanda",
    "monopolio", "monopoly",
    "agencia reguladora", "regulatory body",
    "AGI", "superinteligencia",
    "data leak", "filtración de datos",

    # Bloque 2 – Aplicaciones de IA, Ética y Robots
    "ética", "ethics", "regulación", "regulation", "barrera legal",
    "responsabilidad", "liability",
    "malfunction", "accidente", "fatal", "fatality",
    "robots reemplazan", "robots replace",

    # Bloque 3 – Tech emergente y ciencia
    "breakthrough controvertido",
    "quantum threat", "breaking encryption", "cripto-quiebre",
    "biohack", "bio-hacking", "edición genética", "gene editing",
    "neuromarketing", "implante cerebral", "brain implant",
    "colapso", "catástrofe", "catastrophic", "existential risk",

    # Bloque 4 – FinTech global y economía digital
    "fraude", "fraud", "phishing", "estafa", "scam",
    "hack", "breach", "data breach",
    "ransomware", "secuestro de datos",
    "lavado de dinero", "money laundering",
    "multas", "fine", "penalty",
    "bancarrota", "bankruptcy", "chapter 11",
    "burbuja", "bubble", "crash", "colapso bursátil",
    "regulación SEC", "SEC lawsuit", "KYC fail",

    # Bloque 5 – Economía y FinTech en México
    "CNBV", "Banxico", "superpeso", "devaluación", "inflación", "inflation",
    "alza de tasas", "raise rates", "tasa de interés", "interest rate",
    "moratoria", "default", "impago",
    "corrupción", "corrupcion",
    "fraude piramidal", "esquema ponzi", "ponzi scheme",
    "apagón bancario", "bank outage",
    "ciberataque", "cyberattack",
    "reforma fiscal", "tax reform"
]

def select_category():
    """
    Selecciona una categoría pseudo‑aleatoria basada en el día de la semana.
    L‑V: cada día corresponde a uno de los 5 bloques; S‑D elige bloque al azar.
    """
    day_of_week = datetime.now().weekday()  # Monday = 0 … Sunday = 6
    if day_of_week < 5:
        block_index = day_of_week
    else:
        block_index = random.randint(0, 4)  # Fin de semana

    block = CATEGORY_BLOCKS[block_index]
    return random.choice(block)

def fetch_news():
    """
    Obtiene noticias usando NewsAPI para la categoría seleccionada del día.
    Se incluyen palabras clave generales para ampliar el alcance.
    """
    category = select_category()
    logger.info(f"Categoría seleccionada para hoy: {category}")
    url = "https://newsapi.org/v2/everything"

    # Detect if topic is explicitly about Mexico/FinTech MX
    is_mexico_topic = ("MX" in category) or ("México" in category) or ("Mexico" in category)
    language = "es" if is_mexico_topic else "en"
    query = f"{category}" if not is_mexico_topic else f"{category} OR México OR Mexico"

    params = {
        "q": query,
        "language": language,
        "sortBy": "relevancy",
        "apiKey": NEWSAPI_KEY,
        "pageSize": 5
    }

    # Prioritize Mexican financial outlets when relevant
    MX_DOMAINS = "elfinanciero.com.mx,expansion.mx,forbes.com.mx,eleconomista.com.mx"
    if is_mexico_topic:
        params["domains"] = MX_DOMAINS

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
        "📌 OBJETIVO: Generar un post de entre 1 200 y 2 000 caracteres (200‑300 palabras) que mantenga la atención y fomente conversación.\n\n"
        "1️⃣ Comienza con un GANCHO de máximo dos líneas (pregunta retadora, dato impactante o chiste) para atrapar al lector.\n"
        "2️⃣ Desarrolla la historia en párrafos cortos (3‑5 ideas clave) usando emojis y MAYÚSCULAS o guiones visuales para resaltar puntos.\n"
        "3️⃣ Incluye UNO O DOS datos concretos (estadísticas, cifras o citas) antes del cierre, ya sea en párrafo aparte o en bullets.\n"
        "4️⃣ Finaliza con una pregunta provocadora que invite a comentar.\n\n"
        "Si la noticia trata de economía o FinTech, explica por qué impacta al ecosistema financiero mexicano (regulación, inversión, usuarios).\n\n"
        "NO comiences el texto con el título original de la noticia ni lo pongas como encabezado; si lo deseas, intégralo de forma natural dentro del cuerpo.\n"
        "NO uses asteriscos para destacar texto. Evita tecnicismos excesivos; busca claridad.\n\n"
        "Genera EXACTAMENTE entre 3 y 5 hashtags relevantes en español (sin repetir '#IA') colocados al final del post, en la misma línea.\n\n"
        "Esta es la descripción de la noticia sobre la cual debes escribir:\n\n" + content
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional tech news writer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        logger.error(f"Error al resumir el artículo: {e}")
        return "Error generating summary 😢."

def controversy_score(article: dict) -> int:
    """
    Returns a score 0‑5 based on how many controversy keywords appear
    in the title or description.
    """
    full_text = (article.get("title", "") + " " + article.get("description", "")).lower()
    hits = sum(1 for kw in CONTROVERSY_KEYWORDS if kw.lower() in full_text)
    return min(hits, 5)

def generate_poll(summary: str) -> tuple[str, List[str]]:
    """
    Use OpenAI to generate a poll question and 3‑4 short options.
    Falls back to a default poll if parsing fails.
    """
    poll_prompt = (
        "Devuelve en JSON con keys 'question' y 'options' (lista de 3‑4 elementos ≤30 caracteres) "
        "una encuesta para LinkedIn basada en este texto:\n\n" + summary
    )
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": poll_prompt}],
            max_tokens=150,
            temperature=0.7
        )
        match = re.search(r'\{.*\}', res.choices[0].message.content, re.S)
        data = json.loads(match.group(0)) if match else {}
        question = data.get("question") or "¿Qué opinas?"
        options = data.get("options") or ["Sí", "No", "Tal vez"]
    except Exception as e:
        logger.error(f"Error generando poll: {e}")
        question, options = "¿Qué opinas?", ["Sí", "No", "Tal vez"]
    return question, options[:4]

def post_to_linkedin_poll(commentary: str, poll_question: str, poll_options: List[str]):
    url = "https://api.linkedin.com/rest/posts"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202506",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    payload = {
        "author": f"urn:li:person:{LINKEDIN_PERSON_ID}",
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "lifecycleState": "PUBLISHED",
        "content": {
            "poll": {
                "question": poll_question,
                "options": [{"text": opt[:30]} for opt in poll_options],
                "settings": {"duration": "THREE_DAYS"}
            }
        }
    }
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 201:
        logger.info("Encuesta publicada con éxito ✅")
    else:
        logger.error(f"Error publicando encuesta: {res.status_code} {res.text}")

def post_to_linkedin_shares(content, image_url=None):
    logger.info(f"Preparando publicación: {content[:100]}...")

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
                    "thumbnails": [{"resolvedUrl": image_url}],
                    "altText": "Imagen alusiva a la noticia"
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
    logger.info(f"Artículos obtenidos: {len(articles) if articles else 0}")
    if not articles:
        return

    processed = []  # list of tuples (score, article, summary, image_info)
    for art in articles:
        if is_already_published(art["url"]):
            logger.info(f"Artículo ya publicado, se omite: {art['url']}")
            continue
        summary = summarize_and_rewrite(art)
        score = controversy_score(art)
        img_info = fetch_image_for_article(art)
        processed.append((score, art, summary, img_info))

    if not processed:
        return

    # Selecciona la noticia con mayor controversia
    top_tuple = max(processed, key=lambda x: x[0])
    top_score, top_art, top_summary, top_img = top_tuple

    for score, art, summary, img_info in processed:
        content = f"{summary}\n\nFuente 👉 {art['url']}"
        author_credit = (
            f"\n📸 Imagen de {img_info['author_name']} vía Unsplash"
            if img_info and img_info.get("author_name") else ""
        )
        if art == top_art and score > 0:
            # Publica encuesta
            q, opts = generate_poll(summary)
            post_to_linkedin_poll(content, q, opts)
        else:
            # Publica share normal
            img_url = img_info.get("image_url") if img_info else None
            post_to_linkedin_shares(content + author_credit, image_url=img_url)

        mark_as_published(art["url"])

def lambda_handler(event, context):
    main()
    return {
        "statusCode": 200,
        "body": "Ejecución finalizada correctamente."
    }