from datetime import datetime
from app import db


# --- Gestion des administrateurs ---
class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(255), nullable=False)
    notifications = db.relationship('Notification', backref='admin', lazy=True)


# --- Véhicules ---
class Vehicule(db.Model):
    __tablename__ = 'vehicule'
    id = db.Column(db.Integer, primary_key=True)
    immatriculation = db.Column(db.String(100), unique=True, nullable=False)
    marque = db.Column(db.String(100), nullable=False)
    modele = db.Column(db.String(100), nullable=False)
    caracteristiques_techniques = db.Column(db.Text)  # ex: motorisation, options...
    type = db.Column(db.String(50), nullable=False)   # Berline, Van, SUV, etc.
    capacite_passagers = db.Column(db.Integer, nullable=False)

    # Détails de chargement
    volume_coffre_bagages = db.Column(db.Integer)      # en litres
    volume_coffre_rabattus = db.Column(db.Integer)     # en litres
    nb_sieges_bebe = db.Column(db.Integer, default=0)
    nb_valises = db.Column(db.Integer, default=0)
    coffre_de_toit = db.Column(db.Boolean, default=False)
    details_coffre_toit = db.Column(db.Text)

    # Disponibilité & illustration
    disponible = db.Column(db.Boolean, default=True)
    image = db.Column(db.String(200))

    # Relations
    reservations = db.relationship('Reservation', backref='vehicule', lazy=True)


# --- Réservations ---
class Reservation(db.Model):
    __tablename__ = 'reservation'
    id = db.Column(db.Integer, primary_key=True)

    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicule.id'), nullable=False)

    # Infos client (sans compte)
    client_nom = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(120), nullable=False)
    client_telephone = db.Column(db.String(20), nullable=False)

    # Lieux & date
    date_heure = db.Column(db.DateTime, nullable=False)
    adresse_depart = db.Column(db.String(200), nullable=False)
    adresse_arrivee = db.Column(db.String(200), nullable=False)
    vol_info = db.Column(db.String(100))

    # Passagers & bagages supplémentaires
    nb_passagers = db.Column(db.Integer)
    nb_valises_23kg = db.Column(db.Integer)
    nb_valises_10kg = db.Column(db.Integer)
    nb_sieges_bebe = db.Column(db.Integer)
    poids_enfants = db.Column(db.String(100))

    # Paiement & remarques
    paiement = db.Column(db.String(50))
    commentaires = db.Column(db.Text)
    statut = db.Column(db.String(50), nullable=False, default="En attente")


    # Lien vers le trajet calculé
    trajet = db.relationship('Trajet', uselist=False, backref='reservation', lazy=True)


# --- Détails du trajet ---
class Trajet(db.Model):
    __tablename__ = 'trajet'
    id = db.Column(db.Integer, primary_key=True)
    adresse_depart = db.Column(db.String(200), nullable=False)
    adresse_arrivee = db.Column(db.String(200), nullable=False)
    distance_km = db.Column(db.Float)
    duree_estimee_min = db.Column(db.Integer)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservation.id'), nullable=False)


# --- Tarification ---
class TarifForfait(db.Model):
    """
    Trajets à prix fixe définis par l'admin.
    Exemple : Dakar -> AIBD à 45 000 F.
    """
    __tablename__ = 'tarif_forfait'
    id = db.Column(db.Integer, primary_key=True)
    depart = db.Column(db.String(200), nullable=False)
    arrivee = db.Column(db.String(200), nullable=False)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categorie_vehicule.id'))
    prix_cfa = db.Column(db.Integer, nullable=False)
    distance_km = db.Column(db.Float)
    bidirectionnel = db.Column(db.Boolean, default=True)
    actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TarifRegle(db.Model):
    """
    Règle générale pour calculer un prix au kilomètre si aucun forfait n'est défini.
    Exemple : base 10 000 F + 500 F/km.
    """
    __tablename__ = 'tarif_regle'
    id = db.Column(db.Integer, primary_key=True)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categorie_vehicule.id'))
    base = db.Column(db.Integer, nullable=False)
    prix_km = db.Column(db.Integer, nullable=False)
    minimum = db.Column(db.Integer, default=0)
    coeff_nuit = db.Column(db.Float, default=1.0)
    coeff_weekend = db.Column(db.Float, default=1.0)
    actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# --- Notifications administratives ---
class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
class CategorieVehicule(db.Model):
    __tablename__ = 'categorie_vehicule'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
