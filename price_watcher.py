import json, os, re, smtplib, ssl, hashlib
from email.message import EmailMessage
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

CONFIG = json.loads(Path("config.json").read_text(encoding="utf-8"))
STATE_PATH = Path("last_alerts.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
}
POSITIVE = ("ttc450 ultra", "ttc 450 ultra")

NEGATIVE = (
    "ttc450 pro", "ttc 450 pro",
    "4th axis", "4th-axis", "4 achse", "rotary",
    "vacuum", "absaugung",
    "bundle", "combo", "kit", "starter set", "set",
    "package", "paket", "mit zubehör", "accessory",
    "zubehör", "spare part",
    "mit laser", "with laser", "laser module",
    "laser kit", "laser included", "laser bundle",
    "inkl. laser", "inklusive laser",
)

def parse_price(value):
    if value is None:
        return None
    s = str(value).strip().replace("\xa0", " ")
    # Structured-data prices are usually plain decimal numbers.
    if re.fullmatch(r"\d+(?:[.,]\d{1,2})?", s):
        return float(s.replace(",", "."))
    # For visible text such as "599,00 €" or "1.099,00 EUR".
    m = re.search(r"(\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})|\d+(?:[.,]\d{2})?)\s*(?:€|EUR)", s, re.I)
    if not m:
        return None
    return float(m.group(1).replace(" ", "").replace(".", "").replace(",", "."))

def extract_product(soup):
    """Extract a price only when it can be associated with product data."""

    def read_product(data):
        """Walk JSON-LD product structures, including nested graphs."""
        stack = data if isinstance(data, list) else [data]

        while stack:
            item = stack.pop()

            if isinstance(item, list):
                stack.extend(item)
                continue

            if not isinstance(item, dict):
                continue

            if isinstance(item.get("@graph"), list):
                stack.extend(item["@graph"])

            item_type = item.get("@type", "")
            if isinstance(item_type, list):
                is_product = "Product" in item_type
            else:
                is_product = item_type == "Product"

            if not is_product:
                continue

            title = str(item.get("name", "")).strip()
            offers = item.get("offers", [])
            if isinstance(offers, dict):
                offers = [offers]
            if not isinstance(offers, list):
                continue

            for offer in offers:
                if not isinstance(offer, dict):
                    continue

                price_value = (
                    offer.get("price")
                    or offer.get("lowPrice")
                    or offer.get("priceSpecification", {}).get("price")
                    if isinstance(offer.get("priceSpecification", {}), dict)
                    else offer.get("price") or offer.get("lowPrice")
                )

                price = parse_price(price_value)
                if title and price is not None:
                    return title, price

        return None, None

    # 1. Prefer structured Product JSON-LD.
    for node in soup.select('script[type="application/ld+json"]'):
        raw = node.string or node.get_text()
        if not raw:
            continue

        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue

        title, price = read_product(data)
        if title and price is not None:
            return title, price

    # 2. Explicit product price metadata.
    title_tag = soup.select_one('meta[property="og:title"]')
    h1 = soup.find("h1")
    title = (
        title_tag.get("content", "").strip() if title_tag else ""
    ) or (
        h1.get_text(" ", strip=True) if h1 else ""
    )

    for selector in (
        'meta[property="product:price:amount"]',
        'meta[property="og:price:amount"]',
        'meta[itemprop="price"]',
    ):
        tag = soup.select_one(selector)
        if tag:
            price = parse_price(tag.get("content") or tag.get("value"))
            if title and price is not None:
                return title, price

    # 3. No unverified generic price fallback:
    # never mistake shipping, a discount, or another product's price
    # for the actual TTC450 Ultra price.
    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True)

    return title, None

def valid_exact_model(title):
    t = re.sub(r"[-_]+", " ", title.lower())
    has_ultra = "ultra" in t and ("ttc450" in t.replace(" ", "") or "ttc 450" in t)
    if not has_ultra:
        return False
    # Explicitly reject Pro, bundles, laser/rotary/4th-axis and vacuum packages.
    if any(term in t for term in NEGATIVE):
        return False
    return True

def fetch_offer(shop, item):
    url = item["url"]

    if not url.startswith(("https://", "http://")) or "PASTE_EXACT" in url:
        return {
            "shop": shop,
            "url": url,
            "status": "unconfigured",
            "reason": "Bitte eine gültige Produkt-URL in config.json eintragen."
        }

    try:
        response = requests.get(url, headers=HEADERS, timeout=25)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title, price = extract_product(soup)
        if not title or price is None:
            return {"shop": shop, "url": url, "status": "unverified",
                    "reason": "Kein zuverlässig zuordenbarer Preis gefunden."}
        if not valid_exact_model(title):
            return {"shop": shop, "url": url, "title": title, "status": "rejected",
                    "reason": "Titel nicht eindeutig als TTC450 Ultra-Basismodell erkannt."}
        # Shipping must be explicitly configured by the user; unknown is not silently treated as zero.
        shipping = item.get("shipping_eur")
        if shipping is None:
            return {"shop": shop, "url": url, "title": title, "listed_price": price,
                    "status": "shipping_unknown",
                    "reason": "Versandkosten bitte in config.json ergänzen; Preis nicht als Endpreis werten."}
        total = round(price + float(shipping), 2)
        return {"shop": shop, "url": url, "title": title, "listed_price": price,
                "shipping": float(shipping), "total": total,
                "status": "ok" if total <= CONFIG["deal_threshold_eur"] else "over_threshold"}
    except Exception as e:
        return {"shop": shop, "url": url, "status": "unverified",
                "reason": f"Abfrage fehlgeschlagen ({type(e).__name__}); manuell prüfen."}

def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def send_email(subject, body):
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "465"))
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]
    recipient = os.environ["ALERT_EMAIL_TO"]
    sender = os.environ.get("ALERT_EMAIL_FROM", username)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
        server.login(username, password)
        server.send_message(msg)

def main():
    state = load_state()
    results = []
    for shop, items in CONFIG["shops"].items():
        for item in items:
            results.append(fetch_offer(shop, item))

    qualifying = [r for r in results if r.get("status") == "ok"]
    alerts = []
    for r in qualifying:
        band = "KAUFALARM" if r["total"] <= CONFIG["target_price_eur"] else "DEALALARM"
        key = hashlib.sha256((r["url"] + "|" + str(r["total"]) + "|" + band).encode()).hexdigest()
        if key not in state:
            alerts.append((band, r, key))

    if alerts:
        lines = [
            "TTC450 Ultra Preisalarm",
            f"Geprüft: {datetime.now(timezone.utc).astimezone().isoformat(timespec='minutes')}",
            "",
        ]
        for band, r, key in alerts:
            lines += [
                f"{band}: {r['total']:.2f} € inkl. konfiguriertem Versand",
                f"Händler: {r['shop']}",
                f"Angebotstitel: {r['title']}",
                f"Warenpreis: {r['listed_price']:.2f} €",
                f"Versand: {r['shipping']:.2f} €",
                f"Link: {r['url']}",
                ""
            ]
            state[key] = datetime.now(timezone.utc).isoformat()
        send_email(f"[TTC450 Ultra] {len(alerts)} Preisalarm(e)", "\n".join(lines))

    # Write a report for the GitHub Actions log/artifact.
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "note": "Only successfully parsed and title-validated prices are considered for alerts."
    }
    Path("price_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
