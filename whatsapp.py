"""
Notifications WhatsApp.

⚠️ Deux niveaux possibles :
1. GRATUIT ET SIMPLE (ce qui est implémenté ici) : génère un lien "wa.me"
   pré-rempli. Il faut ensuite qu'un humain (vous) clique dessus, ou qu'un
   navigateur headless l'ouvre automatiquement — l'envoi n'est pas 100%
   automatique sans action.
2. AUTOMATIQUE COMPLET (non inclus, nécessite un compte payant) : l'API
   officielle WhatsApp Business (Meta) permet un envoi 100% automatique,
   mais nécessite une validation Meta Business + un numéro dédié + un coût
   mensuel selon le volume. À activer plus tard si le volume le justifie.
"""
import urllib.parse

WHATSAPP_BASE = "https://wa.me/"


def build_link(numero: str, message: str) -> str:
    """Construit un lien WhatsApp pré-rempli. `numero` au format international
    sans le +, ex: 237690000000"""
    numero_clean = numero.strip().replace("+", "").replace(" ", "")
    return f"{WHATSAPP_BASE}{numero_clean}?text={urllib.parse.quote(message)}"


def message_nouvelle_commande(client_whatsapp: str, montant: float) -> str:
    return (
        f"🔔 Nouvelle commande !\n"
        f"Client : {client_whatsapp}\n"
        f"Montant : {montant} FCFA\n"
        f"Vérifiez le tableau de bord admin pour les détails."
    )


def message_support_client(access_token: str) -> str:
    return (
        f"Bonjour, j'ai besoin d'aide avec mon bot Telegram.\n"
        f"Mon code : {access_token[:8]}"
    )


def message_code_activation(access_token: str, formulaire_url: str) -> str:
    return (
        f"✅ Votre paiement est confirmé !\n\n"
        f"Complétez maintenant votre formulaire ici :\n{formulaire_url}\n\n"
        f"⚠️ Ce lien est personnel et à usage unique, ne le partagez pas."
    )
