"""
Script à exécuter UNE FOIS pour créer votre compte admin (email + mot de
passe). Peut être ré-exécuté à tout moment pour changer le mot de passe.

Usage :
    python create_admin.py
"""
import getpass
from passlib.hash import bcrypt

import models

models.init_db()

email = input("Email admin : ").strip()
password = getpass.getpass("Mot de passe admin (ne s'affiche pas) : ").strip()

if len(password) < 6:
    print("⚠️  Le mot de passe doit contenir au moins 6 caractères. Recommencez.")
    raise SystemExit(1)

db = models.SessionLocal()
try:
    settings = db.query(models.Settings).filter_by(id="main").first()
    settings.admin_email = email
    settings.admin_password_hash = bcrypt.hash(password)
    db.commit()
    print(f"✅ Compte admin créé/mis à jour pour {email}.")
    print("Connectez-vous sur /gestion-privee/connexion")
finally:
    db.close()
