"""
Application principale — routes publiques (client) et admin.

Lancer en local : uvicorn main:app --reload
"""
import json
import os
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from itsdangerous import URLSafeSerializer, BadSignature
from passlib.hash import bcrypt

import models
import monetbil
import generator
import whatsapp

app = FastAPI(title="Plateforme Bot Telegram")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

models.init_db()

SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", "changez-moi-en-production")
signer = URLSafeSerializer(SECRET_KEY, salt="admin-session")


def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_settings(db: Session) -> models.Settings:
    return db.query(models.Settings).filter_by(id="main").first()


# =====================================================================
# ROUTES PUBLIQUES — CLIENT
# =====================================================================

@app.get("/", response_class=HTMLResponse)
def accueil(request: Request, db: Session = Depends(get_db)):
    settings = get_settings(db)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "settings": settings,
    })


@app.post("/commander")
def commander(request: Request, whatsapp_number: str = Form(...), db: Session = Depends(get_db)):
    """Le client entre son numéro WhatsApp -> on crée la commande et on
    l'envoie payer sur CinetPay."""
    settings = get_settings(db)

    client = db.query(models.Client).filter_by(whatsapp_number=whatsapp_number).first()
    if not client:
        client = models.Client(whatsapp_number=whatsapp_number)
        db.add(client)
        db.commit()

    order = models.Order(
        client_id=client.id,
        client_whatsapp=whatsapp_number,
        montant=settings.prix_fcfa,
    )
    db.add(order)
    db.commit()

    try:
        payment = monetbil.create_payment(order.id, settings.prix_fcfa, whatsapp_number)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return RedirectResponse(payment["payment_url"], status_code=303)


@app.post("/webhook/monetbil")
async def webhook_monetbil(request: Request, db: Session = Depends(get_db)):
    """Monetbil appelle cette route pour confirmer un paiement (notify_url).
    Les champs exacts renvoyés sont à reconfirmer dans le tableau de bord
    Monetbil au moment de l'intégration finale (payment_ref / item_ref selon
    la version de leur API)."""
    body = await request.form()
    transaction_id = body.get("payment_ref") or body.get("item_ref") or body.get("transaction_id")
    status = (body.get("status") or "").lower()

    if not transaction_id:
        raise HTTPException(status_code=400, detail="transaction_id manquant")

    order = db.query(models.Order).filter_by(id=transaction_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande inconnue")

    if status in ("success", "successful", "1", "true") and monetbil.verify_payment(transaction_id):
        order.statut = "payé"
        order.paid_at = datetime.utcnow()
        db.commit()

        settings = get_settings(db)
        formulaire_url = f"{monetbil.PUBLIC_BASE_URL}/formulaire/{order.access_token}"
        if settings.whatsapp_support:
            link = whatsapp.build_link(
                settings.whatsapp_support,
                whatsapp.message_nouvelle_commande(order.client_whatsapp, order.montant),
            )
            # Le lien est prêt ; l'envoi effectif nécessite l'API WhatsApp
            # Business (payante) ou un clic manuel — voir whatsapp.py.
            print(f"[ALERTE ADMIN] Nouveau paiement confirmé. Lien notif: {link}")

    return {"ok": True}


@app.get("/formulaire/{token}", response_class=HTMLResponse)
def formulaire(token: str, request: Request, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter_by(access_token=token).first()
    if not order:
        raise HTTPException(status_code=404, detail="Lien invalide")

    if order.statut == "en_attente_paiement":
        return templates.TemplateResponse("attente_paiement.html", {"request": request})

    if order.statut != "payé":
        # déjà rempli ou déjà livré -> on redirige vers la livraison
        return RedirectResponse(f"/livraison/{token}")

    return templates.TemplateResponse("formulaire.html", {"request": request, "token": token})


@app.post("/formulaire/{token}")
def soumettre_formulaire(
    token: str,
    bot_token: str = Form(...),
    owner_id: str = Form(...),
    channel_id: str = Form(...),
    group_id: str = Form(""),
    post_hour_utc: str = Form("9"),
    anthropic_api_key: str = Form(""),
    db: Session = Depends(get_db),
):
    order = db.query(models.Order).filter_by(access_token=token).first()
    if not order or order.statut != "payé":
        raise HTTPException(status_code=403, detail="Formulaire non accessible")

    config = {
        "bot_token": bot_token,
        "owner_id": owner_id,
        "channel_id": channel_id,
        "group_id": group_id,
        "post_hour_utc": post_hour_utc,
        "anthropic_api_key": anthropic_api_key,
    }
    order.config_json = json.dumps(config)
    order.statut = "formulaire_rempli"
    db.commit()

    return RedirectResponse(f"/livraison/{token}", status_code=303)


@app.get("/livraison/{token}", response_class=HTMLResponse)
def livraison(token: str, request: Request, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter_by(access_token=token).first()
    if not order:
        raise HTTPException(status_code=404, detail="Lien invalide")

    if order.statut == "formulaire_rempli":
        # Première visite après le formulaire -> on génère les livrables
        result = generator.generate_delivery(order)
        order.html_file_path = result["html_file_path"]
        order.deploy_link = result["deploy_link"]
        order.statut = "livré"
        order.delivered_at = datetime.utcnow()
        db.commit()

    if order.statut != "livré":
        raise HTTPException(status_code=403, detail="Rien à livrer pour cette commande")

    return templates.TemplateResponse("livraison.html", {
        "request": request,
        "token": token,
        "deploy_link": order.deploy_link,
    })


@app.get("/livraison/{token}/telecharger")
def telecharger_html(token: str, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter_by(access_token=token).first()
    if not order or not order.html_file_path or not os.path.exists(order.html_file_path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(order.html_file_path, filename="mon-bot-telegram.html")


@app.get("/paiement-retour/{order_id}")
def paiement_retour(order_id: str, db: Session = Depends(get_db)):
    """Page de retour après paiement (avant confirmation webhook, qui peut
    prendre quelques secondes)."""
    order = db.query(models.Order).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404)
    return RedirectResponse(f"/formulaire/{order.access_token}")


# =====================================================================
# ADMIN — AUTHENTIFICATION
# =====================================================================

ADMIN_COOKIE = "admin_session"


def require_admin(request: Request):
    cookie = request.cookies.get(ADMIN_COOKIE)
    if not cookie:
        raise HTTPException(status_code=303, headers={"Location": "/gestion-privee/connexion"})
    try:
        data = signer.loads(cookie)
    except BadSignature:
        raise HTTPException(status_code=303, headers={"Location": "/gestion-privee/connexion"})
    return data


@app.get("/gestion-privee/connexion", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request, "erreur": None})


@app.post("/gestion-privee/connexion")
def admin_login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    settings = get_settings(db)

    if not settings.admin_password_hash:
        # Premier démarrage : aucun mot de passe défini encore
        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "erreur": "Aucun compte admin configuré. Voir README.md pour l'initialiser.",
        })

    if email != settings.admin_email or not bcrypt.verify(password, settings.admin_password_hash):
        return templates.TemplateResponse("admin_login.html", {
            "request": request, "erreur": "Email ou mot de passe incorrect.",
        })

    response = RedirectResponse("/gestion-privee", status_code=303)
    cookie_value = signer.dumps({"email": email})
    response.set_cookie(ADMIN_COOKIE, cookie_value, httponly=True, max_age=60 * 60 * 12)
    return response


@app.get("/gestion-privee/deconnexion")
def admin_logout():
    response = RedirectResponse("/gestion-privee/connexion")
    response.delete_cookie(ADMIN_COOKIE)
    return response


# =====================================================================
# ADMIN — DASHBOARD & GESTION
# =====================================================================

@app.get("/gestion-privee", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    total_commandes = db.query(models.Order).count()
    payees = db.query(models.Order).filter(models.Order.statut.in_(["payé", "formulaire_rempli", "livré"])).count()
    en_attente = db.query(models.Order).filter_by(statut="en_attente_paiement").count()
    livrees = db.query(models.Order).filter_by(statut="livré").count()
    revenus = sum(o.montant for o in db.query(models.Order).filter(
        models.Order.statut.in_(["payé", "formulaire_rempli", "livré"])).all())
    taux_conversion = round((payees / total_commandes * 100), 1) if total_commandes else 0
    settings = get_settings(db)

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "total_commandes": total_commandes,
        "payees": payees,
        "en_attente": en_attente,
        "livrees": livrees,
        "revenus": revenus,
        "taux_conversion": taux_conversion,
        "prix_actuel": settings.prix_fcfa,
    })


@app.get("/gestion-privee/commandes", response_class=HTMLResponse)
def admin_commandes(request: Request, statut: str = "", db: Session = Depends(get_db), _=Depends(require_admin)):
    query = db.query(models.Order).order_by(models.Or
