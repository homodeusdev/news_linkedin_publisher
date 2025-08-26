import os
import requests
import openai
import logging
from dotenv import load_dotenv
from datetime import datetime
import random
import json
import re
from typing import List, Union, Optional
import io
from fpdf import FPDF

# Cargar variables de entorno desde .env (para desarrollo local)
load_dotenv()

NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_ID = os.environ.get("LINKEDIN_PERSON_ID")
TOTAL_ARTICLES = int(os.environ.get("TOTAL_ARTICLES", "8"))  # cantidad objetivo por corrida

openai.api_key = os.environ.get("OPENAI_API_KEY")


# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Archivo temporal para artículos publicados en Lambda
PUBLISHED_ARTICLES_FILE = "/tmp/published_articles.txt"
LAST_CATEGORY_FILE = "/tmp/last_category.txt"

HISTORY_FILE = "/tmp/published_history.jsonl"
HISTORY_DAYS = int(os.environ.get("HISTORY_DAYS", "7"))

STOPWORDS = set(
    "a al algo algunas algunos ante antes como con contra de del desde donde dos el la los las en entre es esa ese eso esta este esto hacia hay hasta la las lo los mas más me mi mis muy no o para pero por que se sin sobre su sus te tu tus un una uno y ya son fue ser si sí".split()
)

def _read_local_published() -> set:
    if not os.path.exists(PUBLISHED_ARTICLES_FILE):
        return set()
    with open(PUBLISHED_ARTICLES_FILE, "r") as f:
        return set(line.strip() for line in f.readlines() if line.strip())

def _append_local_published(url: str) -> None:
    with open(PUBLISHED_ARTICLES_FILE, "a") as f:
        f.write(url.strip() + "\n")

def _load_history() -> list:
    records = []
    if not os.path.exists(HISTORY_FILE):
        return records
    with open(HISTORY_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records

def _save_history(records: list) -> None:
    with open(HISTORY_FILE, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def _prune_history(days: int = HISTORY_DAYS) -> list:
    now = datetime.utcnow()
    keep = []
    for r in _load_history():
        try:
            ts = datetime.fromisoformat(r.get("ts", ""))
        except Exception:
            # If parsing fails, keep a couple of days as safety
            continue
        if (now - ts).days <= days:
            keep.append(r)
    _save_history(keep)
    return keep

def _norm_tokens(s: str) -> set:
    s = re.sub(r"[^\wáéíóúñÁÉÍÓÚÑ]+", " ", (s or "").lower())
    tokens = [t for t in s.split() if t and t not in STOPWORDS]
    return set(tokens)

def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

def _normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()

def is_already_published(url: str, title: str = "") -> bool:
    url = (url or "").strip()
    if not url:
        return False
    # direct URL check
    if url in _read_local_published():
        return True
    # heuristic: similar title in recent history
    title_tokens = _norm_tokens(title)
    history = _prune_history(HISTORY_DAYS)
    for r in history:
        if url == r.get("url"):
            return True
        sim = _jaccard(title_tokens, set(r.get("title_tokens", [])))
        if sim >= 0.8:  # very similar title
            return True
    return False

def mark_as_published(url: str, title: str = "") -> None:
    url = (url or "").strip()
    if not url:
        return
    _append_local_published(url)
    rec = {
        "ts": datetime.utcnow().isoformat(timespec="seconds"),
        "url": url,
        "title_norm": _normalize_text(title),
        "title_tokens": sorted(list(_norm_tokens(title)))
    }
    history = _prune_history(HISTORY_DAYS)
    history.append(rec)
    _save_history(history)

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

# Tópicos de interés para profesionistas en MX (para priorización)
PRO_INTEREST_MX = [
    # Economía/empleo
    "salarios", "inflación", "impuestos", "ISR", "IVA", "nearshoring", "empleo calificado",
    # Finanzas/Banca/Crédito
    "crédito", "tarjetas", "buró de crédito", "CNBV", "Banxico", "fintech", "banca digital",
    # Tecnología/Regulación/Privacidad
    "datos personales", "privacidad", "ciberseguridad", "regulación", "ley fintech",
    # Sectores relevantes MX
    "telecom", "AMLO", "gasolina", "energía", "Pemex", "CFE", "startups", "inversión",
]


# --- NewsAPI biased fetch: MX/global, dedup, controversy/interest rank ---
from math import ceil

def _newsapi_query(query: str, language: str, page_size: int, domains: Optional[str] = None, page: int = 1, since_hours: int = 48, sort_by: str = "relevancy"):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": language,
        "sortBy": sort_by,
        "apiKey": NEWSAPI_KEY,
        "pageSize": page_size,
        "page": page
    }
    if domains:
        params["domains"] = domains
    # Date window: from now minus since_hours
    now = datetime.utcnow()
    from_dt = now - timedelta(hours=since_hours)
    params["from"] = from_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    params["to"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        logger.error(f"NewsAPI error {resp.status_code}: {resp.text}")
        return []
    return resp.json().get("articles", [])


def _rank_score(article: dict) -> int:
    # Controversia base
    c = controversy_score(article)
    # Bonificación si contiene palabras clave de interés profesional MX
    text = (article.get("title", "") + " " + article.get("description", "")).lower()
    bonus = sum(1 for kw in PRO_INTEREST_MX if kw.lower() in text)
    return c * 2 + min(bonus, 3)  # dar más peso a controversia


from datetime import timedelta

def fetch_news_biased(total: int = TOTAL_ARTICLES):
    """Obtiene un set mixto garantizando ~60% MX y ~40% global, priorizando temas polémicos para profesionistas.
    Devuelve lista de artículos (dict) deduplicados y ordenados por score.
    """
    total = max(4, min(total, 20))
    mx_needed = ceil(total * 0.6)
    gl_needed = total - mx_needed

    # Variability for NewsAPI params
    since_hours = random.choice([24, 36, 48, 72])
    sort_by = random.choice(["publishedAt", "relevancy"])
    interest_seed = random.choice(PRO_INTEREST_MX)

    # MX queries: usar bloque 5 + boosters de controversia
    mx_topics = CATEGORY_BLOCKS[4]
    mx_q = f"({ ' OR '.join(mx_topics) }) (México OR Mexico OR CDMX OR Banxico OR CNBV) (fraude OR multa OR ciberataque OR reforma OR inflación OR tasas OR {interest_seed})"
    mx_domains = "elfinanciero.com.mx,expansion.mx,forbes.com.mx,eleconomista.com.mx,animalpolitico.com,aristeguinoticias.com"
    mx_articles = _newsapi_query(mx_q, "es", page_size=mx_needed * 2, domains=mx_domains, since_hours=since_hours, sort_by=sort_by)

    # Global queries (no MX) desde bloques 1-4
    non_mx_blocks = CATEGORY_BLOCKS[:4]
    gl_topics = random.choice(non_mx_blocks)
    gl_q = f"({ ' OR '.join(gl_topics) }) (fraud OR lawsuit OR breach OR regulation OR layoff OR controversy OR {interest_seed})"
    gl_articles = _newsapi_query(gl_q, "en", page_size=gl_needed * 2, since_hours=since_hours, sort_by=sort_by)

    # Mezclar, deduplicar por URL
    seen = set()
    combined = []
    for art in (mx_articles + gl_articles):
        url = art.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        combined.append(art)

    # Rankear por score combinado y recortar al total
    combined.sort(key=_rank_score, reverse=True)
    selected = combined[:total]
    logger.info(f"fetch_news_biased seleccionó {len(selected)} artículos (MX~{mx_needed}, GL~{gl_needed}).")
    return selected

def select_category():
    """
    Selecciona una categoría con sesgo hacia México (bloque 5).
    ~60% de probabilidad: elegir del bloque 5 (Economía/FinTech MX).
    ~40% restante: rotación por día laboral; fines de semana al azar.
    """
    day_of_week = datetime.now().weekday()  # Monday = 0 … Sunday = 6
    # 60% de probabilidad de elegir el bloque 5 (índice 4)
    if random.random() < 0.6:
        block = CATEGORY_BLOCKS[4]
        return random.choice(block)

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
    # Detect if topic is explicitly about Mexico/FinTech MX
    is_mexico_topic = ("MX" in category) or ("México" in category) or ("Mexico" in category)
    language = "es" if is_mexico_topic else "en"
    query = (
        f"{category}"
        if not is_mexico_topic
        else f"{category} OR México OR Mexico OR CDMX OR Banxico OR CNBV"
    )
    since_hours = random.choice([24, 36, 48, 72])
    sort_by = random.choice(["publishedAt", "relevancy"])
    MX_DOMAINS = "elfinanciero.com.mx,expansion.mx,forbes.com.mx,eleconomista.com.mx"
    articles = _newsapi_query(
        query,
        language,
        page_size=20,
        domains=MX_DOMAINS if is_mexico_topic else None,
        page=1,
        since_hours=since_hours,
        sort_by=sort_by
    )
    # Deduplicate per domain cap (original code may have more, but keep logic as before)
    logger.info(f"Se encontraron {len(articles)} artículos para la categoría {category}.")
    return articles

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

# ----------  PDF Carousel helpers  ----------
def generate_slides(summary: str) -> List[dict]:
    """
    Devuelve lista de slides [{'title': str, 'points': [str, ...]}]
    """
    prompt = (
        "Divide el siguiente texto en un carrusel de 4 slides para LinkedIn. "
        "Cada slide debe tener un 'title' (≤40 caracteres) y 3 bullets (≤60 caracteres cada uno). "
        "Devuélvelo en JSON: [{'title': str, 'points': [str, str, str]}]\n\n"
        + summary[:1200]
    )
    try:
        import json as _json
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )
        return _json.loads(res.choices[0].message.content)
    except Exception as e:
        logger.error(f"GPT slides fallback: {e}")
        return [
            {"title": "Resumen", "points": [summary[:100], "...", "..."]},
            {"title": "Datos clave", "points": ["…", "…", "…"]},
            {"title": "Impacto", "points": ["…", "…", "…"]},
            {"title": "Y ahora…", "points": ["¿Qué opinas?", "", ""]}
        ]

class CarouselPDF(FPDF):
    def header(self):
        pass  # no automatic header

def build_pdf(slides: List[dict]) -> bytes:
    pdf = CarouselPDF(orientation="P", unit="pt", format="LETTER")
    pdf.set_auto_page_break(auto=False)
    for slide in slides:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 24)
        pdf.multi_cell(0, 40, slide["title"], align="L")
        pdf.ln(10)
        pdf.set_font("Helvetica", "", 14)
        for pt in slide["points"]:
            if pt:
                pdf.multi_cell(0, 18, u"• " + pt, align="L")
                pdf.ln(4)
    buffer = io.BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()

def register_pdf_asset(pdf_bytes: bytes) -> str:
    url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202506",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    payload = {
        "registerUploadRequest": {
            "owner": f"urn:li:person:{LINKEDIN_PERSON_ID}",
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-document"],
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent"
            }],
            "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"]
        }
    }
    res = requests.post(url, headers=headers, json=payload).json()
    upload_url = res["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset_urn = res["value"]["asset"]
    up_headers = {"Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
                  "Content-Type": "application/pdf"}
    requests.put(upload_url, headers=up_headers, data=pdf_bytes).raise_for_status()
    return asset_urn

def post_document(asset_urn: str, commentary: str):
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
        "lifecycleState": "PUBLISHED",
        "content": {"document": {"asset": asset_urn}}
    }
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 201:
        logger.info("Carrusel PDF publicado con éxito ✅")
    else:
        logger.error(f"Error publicando carrusel: {res.status_code} {res.text}")

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
        logger.info(f"Opciones publicadas: {[o['text'] for o in payload['content']['poll']['options']]}")
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
    articles = fetch_news_biased(TOTAL_ARTICLES)
    logger.info(f"Artículos obtenidos: {len(articles) if articles else 0}")
    if not articles:
        return

    processed = []  # list of tuples (score, article, summary)
    for art in articles:
        if is_already_published(art.get("url", ""), art.get("title", "")):
            logger.info(f"Artículo ya publicado, se omite: {art['url']}")
            continue
        summary = summarize_and_rewrite(art)
        score = controversy_score(art)
        processed.append((score, art, summary))

    if not processed:
        return

    # Publicar **todas** las noticias como encuesta (poll)
    for score, art, summary in processed:
        content = f"{summary}\n\nFuente 👉 {art['url']}"
        question, options = generate_dynamic_poll(summary)
        options = _sanitize_poll_options(options)
        post_to_linkedin_poll(content, question, options)
        mark_as_published(art["url"], art.get("title", ""))


# --- Helper: Sanitiza opciones de encuesta a 2–3 palabras ---
def _sanitize_poll_options(options: List[str]) -> List[str]:
    """Recorta cada opción a 2–3 palabras (sin signos extras) y elimina vacíos."""
    sanitized = []
    for opt in options:
        # Quitar espacios duplicados y caracteres no deseados al principio/fin
        text = re.sub(r"\s+", " ", str(opt)).strip()
        words = text.split()
        if not words:
            continue
        # Asegurar 2–3 palabras: tomar máximo 3; si solo hay 1, mantener 1 pero intentaremos complementarla abajo
        words = words[:3]
        text = " ".join(words)
        sanitized.append(text)
    # Si alguna quedó con 1 palabra, intentar alargar a 2 usando adiciones neutras
    fixed = []
    for t in sanitized:
        if len(t.split()) == 1:
            fixed.append(f"{t} ✔️")  # añade un marcador corto para llegar a 2 tokens visibles
        else:
            fixed.append(t)
    # Mantener máximo 4 opciones, únicas y no vacías
    out = []
    for t in fixed:
        if t and t not in out:
            out.append(t)
        if len(out) == 4:
            break
    return out

def generate_dynamic_poll(summary: str) -> tuple[str, List[str]]:
    """
    Usa OpenAI para generar una pregunta provocadora tipo encuesta y 4 opciones (2–3 palabras c/u).
    """
    prompt = (
        "Eres un estratega de contenido para LinkedIn con enfoque en noticias tech, economía y controversias actuales. "
        "Dado el siguiente resumen de una noticia, genera una pregunta provocadora tipo encuesta para la audiencia profesional latinoamericana. "
        "La pregunta debe invitar al debate o a la reflexión.\n\n"
        "➡️ Tono informal, profesional, con 1–2 emojis si ayudan.\n"
        "➡️ Devuelve EXACTAMENTE 4 opciones, cada una de 2 a 3 palabras (no más), claras y distintas; evita 'Sí/No'.\n\n"
        "Formato de salida estrictamente en JSON como este:\n"
        "{\n"
        "  \"question\": \"¿Cuál es tu opinión sobre X?\",\n"
        "  \"options\": [\"Opción A\", \"Opción B\", \"Opción C\", \"Opción D\"]\n"
        "}\n\n"
        f"Resumen de la noticia:\n{summary}"
    )
    try:
        import json as _json
        res = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.8
        )
        poll_data = _json.loads(res.choices[0].message.content)
        question = poll_data.get("question", "¿Qué opinas sobre esta noticia?")
        options = poll_data.get("options", ["Interesante tema", "Preocupa impacto", "Exagerado quizá", "Falta contexto"]) 
        options = _sanitize_poll_options(options)
        # Relleno de respaldo si vienen menos de 4
        defaults = ["Interesa mucho", "Me preocupa", "Exagerado", "Más contexto"]
        i = 0
        while len(options) < 4 and i < len(defaults):
            options.append(defaults[i])
            i += 1
        return question, options
    except Exception as e:
        logger.error(f"Error generando encuesta dinámica con OpenAI: {e}")
        return (
            "¿Qué opinas sobre esta noticia?",
            ["Interesa mucho", "Me preocupa", "Exagerado", "Más contexto"]
        )

def lambda_handler(event, context):
    main()
    return {
        "statusCode": 200,
        "body": "Ejecución finalizada correctamente."
    }