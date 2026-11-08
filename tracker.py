"""Conservative PS5 alerts, official retailers only. Unknown = no notification."""
import json, os, re, sys, time
from pathlib import Path
from datetime import datetime, timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state.json"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
HEADERS = {"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9", "Accept": "text/html,application/xhtml+xml"}


def normal(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def section(text, anchor, window=1600):
    pos = text.find(anchor)
    return text[pos:pos+window] if pos >= 0 else ""


def assess(mode, html):
    soup = BeautifulSoup(html, "html.parser")
    for bad in soup(["script", "style", "noscript", "footer", "nav"]):
        bad.decompose()
    h1 = soup.find("h1")
    if h1 is None or not re.search(r"\b(ps5|playstation\s*5|playstation®?5)\b", normal(h1.get_text(" ", strip=True))):
        return "unknown", "titre du produit non confirmé"
    # Constrain to the product's first section, not recommendation grids or alternative offers.
    text = normal(soup.get_text(" ", strip=True))
    start = text.find(normal(h1.get_text(" ", strip=True)))
    block = text[max(0, start):start+2300] if start >= 0 else ""
    if not block:
        return "unknown", "contenu non lisible"
    if mode == "boulanger":
        if "produit neuf vendu & expédié par boulanger" not in block and "produit neuf vendu et expédié par boulanger" not in block:
            return "unknown", "vendeur Boulanger non vérifié"
        # A product may have other available variations. Restrict to product block before detailed characteristics.
        anchor = block.find("produit neuf vendu")
        purchase = block[anchor:anchor+950]
        if re.search(r"livraison à domicile\s+indisponible", purchase) or re.search(r"livraison\s+indisponible", purchase):
            return "unavailable", "livraison indisponible"
        if "créer une alerte" in purchase and "ajouter au panier" not in purchase:
            return "unavailable", "alerte de stock proposée, pas d'achat confirmé"
        if "ajouter au panier" in purchase and "indisponible" not in purchase[:500]:
            return "available", "vendeur Boulanger et bouton d'achat détectés"
        return "unknown", "livraison non confirmée"
    if mode == "cultura":
        if not re.search(r"vendu et expédié par\s*:\s*cultura", block):
            return "unknown", "vendeur Cultura non vérifié (marketplace éventuelle)"
        seller_part = section(block, "vendu et expédié par")[:500]
        if "état : neuf" not in seller_part:
            return "unknown", "état neuf non confirmé"
        if "indisponible en ligne" in seller_part or "en stock vendeur" in seller_part:
            return "unavailable", "offre Cultura indisponible en ligne"
        if "en stock en ligne" in seller_part and ("ajouter" in seller_part or "livraison" in seller_part):
            return "available", "vendeur Cultura neuf et en stock en ligne"
        return "unknown", "stock Cultura non vérifiable"
    if mode == "auchan":
        if "vendu par auchan" not in block:
            return "unknown", "vendeur Auchan non vérifié"
        # Auchan can ask for a store even when a generic Add to basket is rendered.
        if "veuillez choisir votre magasin" in block or "bientôt dispo" in block:
            return "unavailable", "commande en ligne non confirmée"
        if "ajouter au panier" in block and re.search(r"livr\.|livraison à domicile", block):
            return "available", "vendeur Auchan et livraison indiquée"
        return "unknown", "livraison non confirmée"
    return "unknown", "site sans extracteur validé"


def telegram(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        print("Secrets Telegram manquants : aucune notification", file=sys.stderr)
        return False
    response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat, "text": msg, "disable_web_page_preview": True}, timeout=20)
    response.raise_for_status()
    return True


def fetch(session, url):
    """Récupération prudente ; pas de contournement de restrictions du site."""
    response = session.get(url, headers=HEADERS, timeout=(10, 30), allow_redirects=True)
    if response.status_code in (401, 403, 429):
        return None, f"HTTP {response.status_code} (accès refusé ou limité)"
    if response.status_code >= 400:
        return None, f"HTTP {response.status_code} (page inaccessible ou déplacée)"
    content_type = response.headers.get("Content-Type", "").lower()
    if "html" not in content_type:
        return None, f"réponse non HTML ({content_type[:60]})"
    if not response.text.strip():
        return None, "page vide"
    return response.text, "ok"


def run():
    products = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    old = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    new = dict(old)
    counts = {"available": 0, "unavailable": 0, "unknown": 0}
    session = requests.Session()
    retries = Retry(total=2, connect=2, read=1, backoff_factor=1,
                    status_forcelist=[500, 502, 503, 504],
                    allowed_methods=["GET"], respect_retry_after_header=True)
    session.mount("https://", HTTPAdapter(max_retries=retries))
    for p in products:
        url = p["url"]
        print(f"Checking {p['store']} {p['name']}")
        try:
            html, diagnostic = fetch(session, url)
            if html is None:
                status, reason = "unknown", diagnostic
            else:
                status, reason = assess(p["mode"], html)
        except requests.exceptions.Timeout:
            status, reason = "unknown", "délai dépassé après nouvelles tentatives"
        except requests.exceptions.ConnectionError:
            status, reason = "unknown", "connexion impossible après nouvelles tentatives"
        except (requests.RequestException, ValueError) as e:
            status, reason = "unknown", f"erreur ({type(e).__name__})"
        counts[status] += 1
        previous = old.get(url, "unknown")
        print(f"  {status}: {reason} / previous={previous}")
        # Never alert for unknown. Alert first confirmed availability, and a return after a confirmed outage.
        if status == "available" and previous != "available":
            message = f"🎮 PS5 NEUVE — DISPONIBLE EN LIGNE\n{p['name']}\nVendeur direct : {p['store']}\n{url}\n⚠️ Vérifie le vendeur et la livraison avant paiement."
            if not telegram(message):
                print("  Alert not sent; state not advanced")
                continue
        # Unknown does not overwrite a previously proven state.
        if status != "unknown":
            new[url] = status
        time.sleep(1.5)
    STATE.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Bilan:", counts, "sur", len(products), "fiches")
    print("Terminé", datetime.now(timezone.utc).isoformat())
    if counts["unknown"] == len(products):
        print("ÉCHEC : aucune fiche vérifiable. Ne pas confondre avec une rupture de stock.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run()
