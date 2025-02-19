from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from cryptography.fernet import Fernet
import os
from base64 import b64encode, b64decode

db = SQLAlchemy()

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user = db.Column(db.String(255), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    session_id = db.Column(db.String(255), nullable=True)
    level = db.Column(db.String(20), nullable=False, default='INFO')

    def __init__(self, user, action, details, ip_address=None, session_id=None, level='INFO'):
        self.user = user
        self.action = action
        self.details = details
        self.ip_address = ip_address
        self.session_id = session_id
        self.level = level

class ServiceProfile(db.Model):
    __bind_key__ = 'service_profiles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    ou = db.Column(db.String(255), nullable=False)
    groups = db.Column(db.Text, nullable=True)  # Liste de DNs de groupes stockée en JSON
    extras = db.Column(db.Text, nullable=True)  # Paramètres additionnels en JSON
    manager = db.Column(db.String(255), nullable=True)  # DN du manager
    domains = db.Column(db.Text, nullable=True)  # Liste des domaines autorisés stockée en JSON
    function = db.Column(db.String(255), nullable=True)  # Attribut IpPhone pour la fonction
    service = db.Column(db.String(255), nullable=True)  # Attribut department
    society = db.Column(db.String(255), nullable=True)  # Attribut title
    ip_telephony = db.Column(db.Boolean, default=False)  # Case à cocher Téléphonie IP
    
    # Règles de transformation pour les attributs utilisateur
    samaccountname_suffix = db.Column(db.String(255), nullable=True)  # Suffixe pour sAMAccountName
    commonname_suffix = db.Column(db.String(255), nullable=True)  # Suffixe pour cn, name, displayName
    givenname_suffix = db.Column(db.String(255), nullable=True)  # Suffixe pour givenName
    mail_suffix = db.Column(db.String(255), nullable=True)  # Suffixe pour mail, userPrincipalName
    mailnickname_suffix = db.Column(db.String(255), nullable=True)  # Suffixe pour mailNickname
    proxyaddresses_suffix = db.Column(db.String(255), nullable=True)  # Suffixe pour proxyAddresses
    targetaddress_suffix = db.Column(db.String(255), nullable=True)  # Suffixe pour targetAddress

class LDAPConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trash_ou = db.Column(db.String(255), nullable=False)
    default_password = db.Column(db.String(255), nullable=True)
    encryption_key = db.Column(db.String(255), nullable=True)
    domains = db.Column(db.Text, nullable=True)  # Stockage des domaines AD séparés par des sauts de ligne
    tenant = db.Column(db.String(255), nullable=True)  # Tenant Microsoft 365
    
    # Configuration du pattern de username
    username_pattern_order = db.Column(db.String(10), nullable=True)  # "NOM_PRENOM" ou "PRENOM_NOM"
    username_first_part_chars = db.Column(db.String(5), nullable=True)  # Nombre de caractères ou "*"
    username_second_part_chars = db.Column(db.String(5), nullable=True)  # Nombre de caractères ou "*"
    username_separator = db.Column(db.String(1), nullable=True)  # Caractère séparateur

    # Configuration du pattern d'email
    email_pattern_order = db.Column(db.String(10), nullable=True)  # "NOM_PRENOM" ou "PRENOM_NOM"
    email_first_part_chars = db.Column(db.String(5), nullable=True)  # Nombre de caractères ou "*"
    email_second_part_chars = db.Column(db.String(5), nullable=True)  # Nombre de caractères ou "*"
    email_separator = db.Column(db.String(1), nullable=True)  # Caractère séparateur
    
    def __init__(self, trash_ou, default_password=None, domains=None, tenant=None):
        self.trash_ou = trash_ou
        self.domains = domains
        self.tenant = tenant
        if not self.encryption_key:
            print("[Password Debug] Génération d'une nouvelle clé de chiffrement")
            self.encryption_key = Fernet.generate_key().decode('utf-8')
        if default_password:
            print("[Password Debug] Chiffrement du mot de passe initial")
            self.set_password(default_password)

    def _get_fernet(self):
        """Retourne une instance Fernet avec la clé stockée"""
        if self.encryption_key:
            try:
                print("[Password Debug] Initialisation de l'instance Fernet")
                key = self.encryption_key.encode('utf-8')
                return Fernet(key)
            except Exception as e:
                print(f"[Password Error] Erreur lors de l'initialisation Fernet: {str(e)}")
                return None
        print("[Password Debug] Pas de clé de chiffrement disponible")
        return None

    def set_password(self, password):
        """Chiffre et stocke le mot de passe"""
        print("[Password Debug] Tentative de chiffrement du mot de passe")
        if not self.encryption_key:
            print("[Password Debug] Génération d'une nouvelle clé de chiffrement")
            self.encryption_key = Fernet.generate_key().decode('utf-8')
        
        f = self._get_fernet()
        if f and password:
            try:
                print("[Password Debug] Chiffrement du mot de passe")
                encrypted = f.encrypt(password.encode('utf-8'))
                self.default_password = b64encode(encrypted).decode('utf-8')
                print("[Password Debug] Mot de passe chiffré et stocké avec succès")
            except Exception as e:
                print(f"[Password Error] Erreur lors du chiffrement: {str(e)}")
        else:
            print("[Password Debug] Impossible de chiffrer le mot de passe: Fernet ou mot de passe non disponible")

    def get_decrypted_password(self):
        """Décrypte et retourne le mot de passe"""
        print("[Password Debug] Tentative de décryptage du mot de passe")
        if self.default_password and self.encryption_key:
            try:
                f = self._get_fernet()
                if f:
                    print("[Password Debug] Décryptage du mot de passe")
                    encrypted = b64decode(self.default_password.encode('utf-8'))
                    decrypted = f.decrypt(encrypted).decode('utf-8')
                    print("[Password Debug] Mot de passe décrypté avec succès")
                    return decrypted
                else:
                    print("[Password Debug] Impossible d'initialiser Fernet")
            except Exception as e:
                print(f"[Password Error] Erreur lors du décryptage: {str(e)}")
                return None
        else:
            print("[Password Debug] Pas de mot de passe ou de clé disponible")
        return None

    @staticmethod
    def get_config():
        return LDAPConfig.query.first()
