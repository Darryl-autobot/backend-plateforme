"""
Modèles de base de données — SQLAlchemy + SQLite.

SQLite est utilisé ici car il ne nécessite AUCUN serveur de base de données
séparé : un simple fichier. Suffisant pour démarrer (des centaines de
commandes/jour sans souci). Si le volume grossit fortement plus tard,
migrer vers PostgreSQL est possible sans réécrire toute la logique.
"""
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, Float
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./platform.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def new_id() -> str:
    return uuid.uuid4().hex


class Client(Base):
    """Un client identifié par son numéro WhatsApp (pas de mot de passe)."""
    __tablename__ = "clients"

    id = Column(String, primary_key=True, default=new_id)
    whatsapp_number = Column(String, unique=True, index=True, nullable=False)
    nom = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Order(Base):
    """Une commande = un cycle complet paiement -> formulaire -> livraison."""
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=new_id)
    client_id = Column(String, index=True, nullable=False)
    client_whatsapp = Column(String, index=True, nullable=False)

    # Statuts possibles : en_attente_paiement, payé, formulaire_rempli, livré
    statut = Column(String, default="en_attente_paiement", index=True)

    montant = Column(Float, default=5000)
    moyen_paiement = Column(String, default="")
    transaction_id = Column(String, default="")  # ID renvoyé par CinetPay

    # Jeton unique inclus dans le lien envoyé au client (formulaire + livraison)
    access_token = Column(String, unique=True, default=new_id, index=True)

    # Configuration soumise par le client dans le formulaire (JSON en texte)
    config_json = Column(Text, default="")

    # Chemins des fichiers livrés une fois générés
    html_file_path = Column(String, default="")
    deploy_link = Column(String, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(String, primary_key=True, default=new_id)
    nom = Column(String, nullable=False)          # ex: "Orange Money"
    icone = Column(String, default="💳")
    actif = Column(Boolean, default=True)
    instructions = Column(Text, default="")
    numero = Column(String, default="")


class Settings(Base):
    """Table à une seule ligne pour les paramètres globaux."""
    __tablename__ = "settings"

    id = Column(String, primary_key=True, default="main")
    prix_fcfa = Column(Float, default=5000)
    nom_plateforme = Column(String, default="AutoBot Telegram")
    message_bienvenue = Column(Text, default="Automatisez votre canal Telegram en quelques minutes.")
    whatsapp_support = Column(String, default="")   # votre numéro, pour recevoir les alertes
    admin_email = Column(String, default="")
    admin_password_hash = Column(String, default="")


def init_db():
    Base.metadata.create_all(engine)

    # Créer la ligne de paramètres par défaut si elle n'existe pas
    db = SessionLocal()
    try:
        if not db.query(Settings).filter_by(id="main").first():
            db.add(Settings(id="main"))
        if db.query(PaymentMethod).count() == 0:
            db.add_all([
                PaymentMethod(nom="Orange Money", icone="🟠"),
                PaymentMethod(nom="MTN Mobile Money", icone="🟡"),
                PaymentMethod(nom="Carte bancaire (Visa/Mastercard)", icone="💳"),
            ])
        db.commit()
    finally:
        db.close()
