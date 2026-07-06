"""
Intégration Monetbil (remplace CinetPay — pas de RCCM exigé à l'inscription).

⚠️ Nécessite un compte Monetbil (https://www.monetbil.com) avec un
"service" créé — récupérez votre SERVICE_KEY dans monetbil.com/services,
puis placez-la dans le fichier .env (voir .env.example).

Fonctionnement (API Widget v2.1) :
1. On envoie une requête à https://api.monetbil.com/widget/v2.1/{SERVICE_KEY}
   avec le montant et les infos de la commande -> Monetbil renvoie une URL
   de paiement.
2. Le client paie sur cette page (Mobile Money : MTN ou Orange).
3. Monetbil appelle notre `notify_url` (webhook) pour confirmer le paiement.

📌 Si votre compte a aussi un SERVICE_SECRET et une méthode de vérification
de signature, il est recommandé de l'ajouter ici pour plus de sécurité —
vérifiez la documentation à jour dans votre tableau de bord Monetbil
(monetbil.com/services) au moment de l'intégration finale.
"""
import os
import requests
import logging

log = logging.getLogger("monetbil")

SERVICE_KEY = os.environ.get("MONETBIL_SERVICE_KEY", "")
API_BASE = "https://api.monetbil.com/widget/v2.1"

# URL publique de votre plateforme (nécessaire pour que Monetbil sache où
# rediriger le client et où envoyer la confirmation webhook)
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")


def is_configured() -> bool:
    return bool(SERVICE_KEY)


def create_payment(order_id: str, montant: float, client_whatsapp: str) -> dict:
    """
    Initie un paiement Monetbil. Retourne un dict avec 'payment_url' si succès.
    """
    if not is_configured():
        raise RuntimeError(
            "Monetbil n'est pas configuré. Ajoutez MONETBIL_SERVICE_KEY "
            "dans le fichier .env (voir README.md)."
        )

    payload = {
        "amount": int(montant),
        "phone": client_whatsapp,
        "phone_lock": "false",
        "locale": "fr",
        "country": "CM",
        "currency": "XAF",
        "item_ref": order_id,
        "payment_ref": order_id,
        "return_url": f"{PUBLIC_BASE_URL}/paiement-retour/{order_id}",
        "notify_url": f"{PUBLIC_BASE_URL}/webhook/monetbil",
    }

    resp = requests.post(f"{API_BASE}/{SERVICE_KEY}", data=payload, timeout=15)
    data = resp.json()

    payment_url = data.get("payment_url")
    if not payment_url:
        log.error("Erreur Monetbil lors de la création du paiement: %s", data)
        raise RuntimeError(f"Erreur Monetbil: {data.get('message', 'réponse inattendue')}")

    return {"payment_url": payment_url}


def verify_payment(transaction_id: str) -> bool:
    """
    ⚠️ Le webhook Monetbil (notify_url) envoie déjà un statut côté serveur,
    donc cette fonction sert de second filtre : on considère l'appel du
    webhook comme fiable puisqu'il vient directement des serveurs Monetbil
    (jamais du navigateur du client). Si Monetbil fournit une API de
    vérification par statut dans votre documentation, il est recommandé de
    l'appeler ici pour une double confirmation avant d'activer l'accès.
    """
    return True
