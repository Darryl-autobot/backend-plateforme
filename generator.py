"""
Génération des livrables pour un client, une fois son formulaire complété.

Livrable 1 — Fichier HTML : un panneau de contrôle autonome qui affiche
             clairement les valeurs à copier-coller, les instructions,
             et les boutons d'action. Ce n'est PAS le bot lui-même
             (un fichier HTML ne peut pas tourner 24/7).

Livrable 2 — Lien de déploiement : pointe vers notre template Railway
             (dossier bot-template/). Le client clique, colle les valeurs
             affichées dans le fichier HTML dans les champs demandés par
             Railway, et c'est déployé — c'est CE lien qui fait vraiment
             tourner le bot en continu, même téléphone éteint.

⚠️ RAILWAY_TEMPLATE_URL doit être remplacé par l'URL de VOTRE propre
template Railway, créé une fois à partir du contenu de bot-template/.
Voir README.md, section "Créer le template Railway".
"""
import json
import os
from pathlib import Path

RAILWAY_TEMPLATE_URL = os.environ.get(
    "RAILWAY_TEMPLATE_URL", "https://railway.app/template/VOTRE-TEMPLATE-ID"
)

DELIVERIES_DIR = Path(__file__).parent / "deliveries"
DELIVERIES_DIR.mkdir(exist_ok=True)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Votre bot Telegram — Panneau de configuration</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700;9..144,900&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg:#170f2b; --bg-panel:#221639; --bg-raised:#2b1c47;
    --accent:#ffb238; --live:#3ecf8e; --text:#f5f0e8; --text-muted:#b8a9d9; --border:#382a54;
  }}
  * {{ box-sizing:border-box; }}
  body {{
    font-family:"Inter",-apple-system,Segoe UI,Roboto,sans-serif;
    background:radial-gradient(ellipse 80% 50% at 50% -10%, #33204f 0%, var(--bg) 60%);
    color:var(--text); margin:0; padding:28px 16px 60px; line-height:1.55;
  }}
  .wrap {{ max-width:640px; margin:0 auto; }}
  .card {{ background:var(--bg-panel); border:1px solid var(--border); border-radius:14px; padding:28px; margin-bottom:20px; }}
  h1 {{ font-family:"Fraunces",serif; font-size:26px; margin:0 0 8px; }}
  h2.eyebrow {{ text-transform:uppercase; letter-spacing:.12em; font-size:12px; color:var(--accent); font-weight:700; margin:0 0 14px; }}
  p.lede {{ color:var(--text-muted); font-size:15px; }}
  .beacon {{ display:inline-flex; align-items:center; gap:8px; font-size:13px; font-weight:600; color:var(--live); text-transform:uppercase; letter-spacing:.08em; margin-bottom:14px; }}
  .beacon .dot {{ position:relative; width:8px; height:8px; background:var(--live); border-radius:50%; }}
  .beacon .dot::before {{ content:""; position:absolute; inset:-6px; border-radius:50%; border:1px solid var(--live); animation:pulse 2s ease-out infinite; }}
  @keyframes pulse {{ 0% {{ transform:scale(.6); opacity:.9; }} 100% {{ transform:scale(1.8); opacity:0; }} }}
  .field-row {{ display:flex; justify-content:space-between; align-items:center; gap:10px; background:var(--bg); border:1px solid var(--border); border-radius:10px; padding:12px 14px; margin:8px 0; }}
  .field-row span.label {{ color:var(--text-muted); font-size:13px; }}
  .field-row code {{ font-family:"IBM Plex Mono",monospace; font-size:13px; color:var(--live); word-break:break-all; text-align:right; }}
  a.btn {{ display:block; text-align:center; font-weight:700; padding:15px; border-radius:10px; text-decoration:none; margin-top:14px; font-size:15px; }}
  a.btn-live {{ background:var(--live); color:#0c2a1d; }}
  a.btn-ghost {{ background:transparent; color:var(--text); border:1px solid var(--border); }}
  ol.steps {{ list-style:none; margin:0; padding:0; counter-reset:step; }}
  ol.steps li {{ counter-increment:step; position:relative; padding-left:40px; margin-bottom:16px; color:var(--text-muted); }}
  ol.steps li::before {{
    content:counter(step); position:absolute; left:0; top:-2px; width:26px; height:26px;
    background:var(--bg-raised); border:1px solid var(--accent); color:var(--accent);
    border-radius:50%; display:flex; align-items:center; justify-content:center;
    font-family:"Fraunces",serif; font-weight:700; font-size:12px;
  }}
  ol.steps strong {{ color:var(--text); }}
</style>
</head>
<body>
<div class="wrap">

<div class="card">
  <span class="beacon"><span class="dot"></span> Bot généré</span>
  <h1>Vos identifiants, prêts à copier</h1>
  <p class="lede">Gardez cette page ouverte pendant le déploiement — vous en aurez besoin à chaque champ.</p>

  {fields_html}

  <a class="btn btn-live" href="{deploy_link}" target="_blank">Déployer maintenant sur Railway</a>
  <a class="btn btn-ghost" href="{support_link}" target="_blank">Besoin d'aide ? Contactez le support</a>
</div>

<div class="card">
  <h2 class="eyebrow">Déploiement</h2>
  <ol class="steps">
    <li><strong>Cliquez sur "Déployer maintenant"</strong> ci-dessus.</li>
    <li><strong>Créez un compte Railway gratuit</strong> si besoin (email ou GitHub).</li>
    <li><strong>Collez chaque valeur</strong> ci-dessus dans le champ correspondant demandé par Railway.</li>
    <li><strong>Cliquez sur "Deploy"</strong> — votre bot est en ligne en 1 à 2 minutes, 24h/24.</li>
    <li><strong>Sur Telegram, ajoutez votre bot comme administrateur</strong> de votre canal (et du groupe de discussion pour les réponses automatiques). Sans cette étape, il ne peut pas publier.</li>
  </ol>
</div>

</div>
</body>
</html>
"""

FIELD_ROW = """
  <div class="field-row">
    <span class="label">{label}</span>
    <code>{value}</code>
  </div>
"""


def generate_html_panel(order) -> str:
    """Crée le fichier HTML de livraison pour une commande, retourne son chemin."""
    config = json.loads(order.config_json or "{}")

    fields = [
        ("TELEGRAM_BOT_TOKEN", config.get("bot_token", "")),
        ("OWNER_ID", config.get("owner_id", "")),
        ("TELEGRAM_CHANNEL_ID", config.get("channel_id", "")),
        ("TELEGRAM_GROUP_ID", config.get("group_id", "")),
        ("POST_HOUR_UTC", str(config.get("post_hour_utc", "9"))),
        ("ANTHROPIC_API_KEY", config.get("anthropic_api_key", "(laisser vide si non utilisé)")),
    ]
    fields_html = "".join(FIELD_ROW.format(label=k, value=v or "—") for k, v in fields)

    from whatsapp import build_link, message_support_client
    support_number = os.environ.get("SUPPORT_WHATSAPP_NUMBER", "")
    support_link = build_link(support_number, message_support_client(order.access_token))

    html = HTML_TEMPLATE.format(
        fields_html=fields_html,
        deploy_link=RAILWAY_TEMPLATE_URL,
        support_link=support_link,
    )

    file_path = DELIVERIES_DIR / f"bot_{order.id}.html"
    file_path.write_text(html, encoding="utf-8")
    return str(file_path)


def generate_delivery(order) -> dict:
    """Point d'entrée principal : génère tous les livrables pour une commande."""
    html_path = generate_html_panel(order)
    return {
        "html_file_path": html_path,
        "deploy_link": RAILWAY_TEMPLATE_URL,
    }
