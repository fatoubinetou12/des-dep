from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField,
    IntegerField, TextAreaField, FloatField, SelectField
)
from wtforms.fields.datetime import DateTimeLocalField
from wtforms.fields.simple import EmailField, TelField
from wtforms.validators import DataRequired, Optional, Email, NumberRange,Length
from flask_wtf.file import FileAllowed, FileField




# --------------------------
# Formulaire de connexion admin
# --------------------------
class AdminLoginForm(FlaskForm):
    username = StringField("Nom d'utilisateur", validators=[DataRequired()])
    password = PasswordField("Mot de passe", validators=[DataRequired()])
    submit = SubmitField("Se connecter")


# --------------------------
# Formulaire d'ajout/modification d'un véhicule
# --------------------------
class AddVehiculeForm(FlaskForm):
    immatriculation = StringField('Immatriculation', validators=[DataRequired()])
    marque = StringField('Marque', validators=[DataRequired()])
    modele = StringField('Modèle', validators=[DataRequired()])
    caracteristiques_techniques = TextAreaField('Caractéristiques techniques', validators=[Optional()])
    type = StringField('Type de véhicule', validators=[DataRequired()])
    capacite_passagers = IntegerField('Capacité de passagers', validators=[DataRequired(), NumberRange(min=1)])
    volume_coffre_bagages = IntegerField('Volume coffre à bagages (L)', validators=[Optional(), NumberRange(min=0)])
    volume_coffre_rabattus = IntegerField('Volume coffre sièges rabattus (L)', validators=[Optional(), NumberRange(min=0)])
    nb_sieges_bebe = IntegerField('Nombre de sièges bébé', validators=[Optional(), NumberRange(min=0)])
    nb_valises = IntegerField('Nombre de valises', validators=[Optional(), NumberRange(min=0)])
    coffre_de_toit = BooleanField('Coffre de toit')
    details_coffre_toit = TextAreaField('Détails du coffre de toit', validators=[Optional()])
    disponible = BooleanField('Disponible')
    photo = FileField('Photo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images uniquement !')
    ])
    submit = SubmitField('Ajouter')

# --------------------------
# Formulaire de réservation
# --------------------------
class ReservationForm(FlaskForm):
    # Infos client
    client_nom = StringField('Nom complet', validators=[DataRequired()])
    client_email = EmailField('Email', validators=[DataRequired(), Email()])
    client_telephone = TelField('Téléphone', validators=[DataRequired()])

    # Détails du trajet
    date_heure = DateTimeLocalField('Date et heure', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    vol_info = StringField('Numéro de vol', validators=[Optional()])
    adresse_depart = StringField('Adresse de départ', validators=[DataRequired()])
    adresse_arrivee = StringField("Adresse d'arrivée", validators=[DataRequired()])

    # Passagers et bagages
    nb_passagers = IntegerField('Nombre de passagers', validators=[DataRequired(), NumberRange(min=1)])
    nb_valises_23kg = IntegerField('Valises 23kg', validators=[Optional(), NumberRange(min=0)])
    nb_valises_10kg = IntegerField('Valises 10kg', validators=[Optional(), NumberRange(min=0)])
    nb_sieges_bebe = IntegerField('Sièges bébé', validators=[Optional(), NumberRange(min=0)])
    poids_enfants = StringField('Poids enfants', validators=[Optional()])


    # Paiement
    paiement = SelectField('Méthode de paiement', choices=[
        ('', 'Sélectionner...'),
        ('Espèces', 'Espèces'),
        ('Carte bancaire', 'Carte bancaire'),
        ('Virement', 'Virement'),
        ('PayPal', 'PayPal')
    ], validators=[DataRequired()])

    commentaires = TextAreaField('Commentaires supplémentaires', validators=[Optional()])
    submit = SubmitField('Confirmer la réservation')


# --------------------------
# Formulaire de tarification forfaitaire
# --------------------------
class AddTarifForfaitForm(FlaskForm):
    depart = StringField("Départ", validators=[DataRequired()])
    arrivee = StringField("Arrivée", validators=[DataRequired()])
    type_vehicule = StringField("Type de véhicule (ex. Berline, Van)", validators=[Optional()])
    prix_cfa = IntegerField("Prix (F CFA)", validators=[DataRequired(), NumberRange(min=0)])
    distance_km = FloatField("Distance de référence (km)", validators=[Optional(), NumberRange(min=0)])
    bidirectionnel = BooleanField("Valable dans les deux sens", default=True)
    actif = BooleanField("Actif", default=True)
    submit = SubmitField("Enregistrer le forfait")


# --------------------------
# Formulaire de règle kilométrique
# --------------------------
class AddTarifRegleForm(FlaskForm):
    type_vehicule = StringField("Type de véhicule (ex. Berline, Van)", validators=[Optional()])
    base = IntegerField("Prix de base (F CFA)", validators=[DataRequired(), NumberRange(min=0)])
    prix_km = IntegerField("Prix par km (F CFA)", validators=[DataRequired(), NumberRange(min=0)])
    minimum = IntegerField("Prix minimum (F CFA)", validators=[Optional(), NumberRange(min=0)])
    coeff_nuit = FloatField("Coeff. nuit (ex. 1.2)", validators=[Optional(), NumberRange(min=0)])
    coeff_weekend = FloatField("Coeff. week-end (ex. 1.1)", validators=[Optional(), NumberRange(min=0)])
    actif = BooleanField("Actif", default=True)
    submit = SubmitField("Enregistrer la règle")
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class EstimationForm(FlaskForm):
    depart = StringField('Départ', validators=[DataRequired()])
    arrivee = StringField('Arrivée', validators=[DataRequired()])
    submit = SubmitField('Estimer')

    # --------------------------
# Formulaire de contact
# --------------------------



class ContactForm(FlaskForm):
    nom = StringField("Nom", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=180)])
    sujet = StringField("Sujet", validators=[DataRequired(), Length(max=160)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(max=5000)])
    submit = SubmitField("Envoyer")
