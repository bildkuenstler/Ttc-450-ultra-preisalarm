# TTC450 Ultra Cloud Price Watcher

A starter project for a daily GitHub Actions check with email alerts.

## Alert rules
- **Kaufalarm:** total <= 500 EUR
- **Dealalarm:** total > 500 EUR and <= 550 EUR
- Only product titles that clearly identify the TTC450 Ultra base model are eligible.
- TTC450 Pro, other TTC450 models, accessories, laser/rotary/vacuum bundles are rejected.
- Unknown shipping is **not** assumed to be free.

## Important limitations
Retailer websites may block automated requests, render prices with JavaScript, or omit shipping costs until checkout. In those cases the script reports an unverified price and does not send a purchase alert. The title/price parser is deliberately conservative but cannot guarantee that every seller page is parsed correctly. For reliable operation, use exact product URLs and confirm each alert on the retailer checkout page.

Amazon/AliExpress may require an approved API or price-tracking provider for reliable data. Do not try to bypass login, CAPTCHA, or anti-bot protections.

## Setup
1. Create a private GitHub repository and upload the contents of this folder.
2. Edit `config.json`. Replace every placeholder with the exact product URL for the **TTC450 Ultra base model**.
3. Enter shipping cost in `shipping_eur`. Use `0` only when free shipping to Germany is confirmed. If shipping varies or is only known at checkout, leave it `null`; that listing will not trigger an alert.
4. In GitHub: **Settings → Secrets and variables → Actions → New repository secret**, add:
   - `SMTP_HOST` (for example `smtp.gmail.com`)
   - `SMTP_PORT` (`465` for SMTP SSL)
   - `SMTP_USERNAME` (sender mailbox)
   - `SMTP_PASSWORD` (mail-provider app password, not your normal account password)
   - `ALERT_EMAIL_FROM` (optional; usually same as username)
   - `ALERT_EMAIL_TO` (recipient email address)
5. In Gmail, use an app password with 2-step verification enabled. For other providers, use their SMTP server and an app password/token.
6. Under **Actions**, enable workflows, then run **TTC450 Ultra price check → Run workflow** to test.
7. The workflow checks daily. It sends an email only for a newly observed eligible price in the alert bands.

## Data and security
- Keep the repository private.
- Never put mail passwords or tokens into `config.json` or source code.
- Check `price_report.json` and the Actions log after the first run.
- If GitHub cannot push the state file, grant the repository's workflow the required write permission under Settings → Actions → General.


## Installierbare Handy-Web-App (PWA)
Diese Version enthält eine mobile Dashboard-Web-App unter `docs/`. Sie kann über HTTPS im Android-Browser geöffnet und – abhängig vom Browser – zum Startbildschirm hinzugefügt werden. Der Preischeck läuft weiterhin über GitHub Actions in der Cloud; das Handy muss dafür nicht eingeschaltet oder online sein.

### Einrichten
1. Lade den Inhalt dieses ZIPs in ein GitHub-Repository hoch und verwende den Branch `main`.
2. Ersetze die Platzhalter in `config.json` durch die echten Produktlinks. Trage Versandkosten nur dann als `0` ein, wenn kostenloser Versand nach Deutschland bestätigt ist.
3. Lege für E-Mail-Alarme die im Abschnitt „Setup“ genannten SMTP-Secrets unter **Settings → Secrets and variables → Actions** an.
4. Aktiviere Actions und starte **TTC450 Ultra price check → Run workflow** einmal manuell.
5. Aktiviere GitHub Pages: **Settings → Pages → Build and deployment → Source: GitHub Actions**. Das Repository muss für GitHub Pages mit deinem Tarif kompatibel sein; bei einem kostenlosen privaten Repository kann es nötig sein, das Repository öffentlich zu machen. Mache es nur öffentlich, wenn du damit einverstanden bist, dass Konfiguration und Preisberichte sichtbar sind. SMTP-Secrets bleiben als GitHub Secrets geschützt.
6. Öffne nach dem ersten erfolgreichen Pages-Deployment die veröffentlichte `github.io`-Adresse. In Chrome auf Android: Menü **⋮ → Zum Startbildschirm hinzufügen** oder **App installieren**.
7. Die App zeigt den letzten Preisbericht. Der Workflow aktualisiert ihn täglich und sendet E-Mail-Alarme nur bei verifizierten Angeboten in den konfigurierten Preisgrenzen.

### Grenzen
- Diese PWA ist die Oberfläche, kein eigener Scraper im Handy und kein Push-Benachrichtigungsdienst.
- Die tägliche Cloud-Abfrage ist nur so gut wie die jeweiligen Shopseiten. Bei nicht verifizierbaren Preisen bleibt die App ausdrücklich vorsichtig.
- Die Web-App zeigt nur den zuletzt veröffentlichten Prüfbericht; „Aktualisieren“ lädt diesen Bericht neu und startet keinen neuen Händler-Check.
