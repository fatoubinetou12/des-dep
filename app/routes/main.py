import os
import requests
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint, render_template, request, session, abort,
    redirect, url_for, flash, current_app, jsonify
)
from werkzeug.utils import secure_filename
from flask_mail import Message

from app import db, mail
from app.forms.forms import (
    AdminLoginForm, AddVehiculeForm, ReservationForm,
    AddTarifForfaitForm, AddTarifRegleForm
)
from app.models.models import Vehicule, Reservation, TarifForfait, TarifRegle

main = Blueprint('main', __name__)

# ------------------------
# Helpers
# ------------------------
def to_int(value, default=None):
    """Convertit en int; renvoie default si vide/non convertible."""
    if value is None:
        return default
    s = str(value).strip()
    if s == "":
        return default
    try:
        return int(s)
    except (TypeError, ValueError):
        return default

def parse_datetime_local(value: str):
    """
    Parse un input HTML5 type 'datetime-local'.
    Exemples acceptés: '2025-10-14T23:51' ou variantes ISO.
    """
    if not value:
        return None
    s = value.strip()
    # Format standard datetime-local (sans secondes)
    try:
        return datetime.strptime(s, '%Y-%m-%dT%H:%M')
    except ValueError:
        pass
    # Variante avec secondes
    try:
        return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        pass
    # Dernière chance: fromisoformat (gère microsecondes, etc.)
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

# ------------------------
# Utilitaire Google Distance Matrix
# ------------------------
def get_distance_and_time(depart, arrivee):
    key = current_app.config['GOOGLE_MAPS_KEY']
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": depart,
        "destinations": arrivee,
        "mode": "driving",
        "units": "metric",
        "key": key
    }
    r = requests.get(url, params=params, timeout=15)
    data = r.json()
    if data.get('status') != 'OK':
        raise Exception(f"Erreur API Google : {data.get('status')}")
    element = data['rows'][0]['elements'][0]
    if element.get('status') != 'OK':
        raise Exception(f"Impossible de calculer la distance : {element.get('status')}")
    distance_km = element['distance']['value'] / 1000
    temps_min = element['duration']['value'] / 60
    return distance_km, temps_min

# ------------------------
# Protection Admin
# ------------------------
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('main.login', next=request.path))
        return f(*args, **kwargs)
    return wrapper

# ------------------------
# Pages publiques
# ------------------------
@main.route('/a-propos')
def about():
    return render_template('about.html')

@main.route('/')
def home():
    vehicules = Vehicule.query.filter_by(disponible=True).limit(6).all()
    transferts_populaires = (
        TarifForfait.query.filter_by(actif=True)
        .order_by(TarifForfait.created_at.desc())
        .limit(8).all()
    )
    google_key = current_app.config.get("GOOGLE_MAPS_KEY")
    return render_template(
        'home.html',
        vehicules=vehicules,
        transferts_populaires=transferts_populaires,
        google_key=google_key
    )

# ------------------------
# Authentification admin
# ------------------------
@main.route('/login', methods=["GET", "POST"])
def login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        # ⚠️ À remplacer par une vraie vérification en BDD
        if form.username.data == "admin" and form.password.data == "admin123":
            session["admin_logged_in"] = True
            flash("Connexion admin réussie.", "success")
            return redirect(request.args.get('next') or url_for("main.admin_dashboard"))
        flash("Identifiants invalides.", "danger")
    return render_template("login.html", form=form)

@main.route('/logout')
def logout():
    session.pop("admin_logged_in", None)
    flash("Déconnexion effectuée.", "info")
    return redirect(url_for("main.home"))

# ------------------------
# Dashboard Admin - Véhicules
# ------------------------
@main.route('/admin/dashboard', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    form = AddVehiculeForm()
    vehicules = Vehicule.query.all()

    if form.validate_on_submit():
        if Vehicule.query.filter_by(immatriculation=form.immatriculation.data).first():
            flash("Un véhicule avec cette immatriculation existe déjà.", "danger")
            return redirect(url_for('main.admin_dashboard'))

        image_filename = None
        if form.photo.data:
            filename = secure_filename(form.photo.data.filename)
            folder = os.path.join(current_app.root_path, 'static/images/vehicules')
            os.makedirs(folder, exist_ok=True)
            form.photo.data.save(os.path.join(folder, filename))
            image_filename = f'images/vehicules/{filename}'

        v = Vehicule(
            immatriculation=form.immatriculation.data,
            marque=form.marque.data,
            modele=form.modele.data,
            caracteristiques_techniques=form.caracteristiques_techniques.data,
            type=form.type.data,
            capacite_passagers=form.capacite_passagers.data,
            volume_coffre_bagages=form.volume_coffre_bagages.data,
            volume_coffre_rabattus=form.volume_coffre_rabattus.data,
            nb_sieges_bebe=form.nb_sieges_bebe.data,
            nb_valises=form.nb_valises.data,
            coffre_de_toit=form.coffre_de_toit.data,
            details_coffre_toit=form.details_coffre_toit.data,
            disponible=form.disponible.data if form.disponible.data is not None else True,
            image=image_filename
        )
        db.session.add(v)
        db.session.commit()
        flash("Véhicule ajouté avec succès !", "success")
        return redirect(url_for('main.admin_dashboard'))

    return render_template('dashboard.html', form=form, vehicules=vehicules)

@main.route('/vehicule/modifier/<int:id>', methods=['POST'])
@admin_required
def modifier_vehicule(id):
    v = Vehicule.query.get_or_404(id)
    for field in ['immatriculation','marque','modele','caracteristiques_techniques',
                  'type','capacite_passagers','volume_coffre_bagages','volume_coffre_rabattus',
                  'nb_sieges_bebe','nb_valises','details_coffre_toit']:
        setattr(v, field, request.form.get(field))
    v.coffre_de_toit = 'coffre_de_toit' in request.form
    v.disponible = 'disponible' in request.form
    img = request.files.get('photo')
    if img and img.filename:
        filename = secure_filename(img.filename)
        folder = os.path.join(current_app.root_path, 'static/images/vehicules')
        os.makedirs(folder, exist_ok=True)
        img.save(os.path.join(folder, filename))
        v.image = f'images/vehicules/{filename}'
    db.session.commit()
    flash("Véhicule modifié avec succès.", "success")
    return redirect(url_for('main.admin_dashboard'))

@main.route('/vehicule/supprimer', methods=['GET'])
@admin_required
def supprimer_vehicule():
    v = Vehicule.query.get_or_404(request.args.get('id'))
    db.session.delete(v)
    db.session.commit()
    flash("Véhicule supprimé avec succès.", "success")
    return redirect(url_for('main.admin_dashboard'))

# ------------------------
# Réservations – Workflow client
# ------------------------
@main.route('/vehicules-disponibles')
def vehicules_disponibles():
    vehicules = Vehicule.query.filter_by(disponible=True).all()
    return render_template('vehicules_disponibles.html', vehicules=vehicules)

@main.route('/reservation/<int:vehicule_id>')
def reservation_page(vehicule_id):
    v = Vehicule.query.get_or_404(vehicule_id)
    google_key = current_app.config.get("GOOGLE_MAPS_KEY")
    return render_template('reservation.html', vehicule=v, form=ReservationForm(), google_key=google_key)

@main.route('/reservation/<int:vehicule_id>/recap', methods=['POST'])
def reservation_recap(vehicule_id):
    v = Vehicule.query.get_or_404(vehicule_id)
    form = ReservationForm()
    data = {k: request.form.get(k) for k in [
        'client_nom','client_email','client_telephone','date_heure','vol_info',
        'adresse_depart','adresse_arrivee','nb_passagers','nb_valises_23kg',
        'nb_valises_10kg','nb_sieges_bebe','poids_enfants','paiement','commentaires'
    ]}
    if not data['client_nom'] or not data['client_email'] or not data['adresse_depart'] or not data['adresse_arrivee']:
        flash("Merci de remplir les informations obligatoires.", "danger")
        return redirect(url_for('main.reservation_page', vehicule_id=vehicule_id))
    return render_template('fiche_vehicule.html', vehicule=v, data=data, form=form)

@main.route('/reserver/<int:vehicule_id>', methods=['POST'])
def reserver_vehicule(vehicule_id):
    v = Vehicule.query.get_or_404(vehicule_id)

    # 1) Collecte brute
    data = {k: request.form.get(k) for k in [
        'client_nom','client_email','client_telephone','date_heure','vol_info',
        'adresse_depart','adresse_arrivee','nb_passagers','nb_valises_23kg',
        'nb_valises_10kg','nb_sieges_bebe','poids_enfants','paiement','commentaires'
    ]}

    # 2) Validation champs nécessaires
    if not data['client_nom'] or not data['client_email']:
        flash("Erreur : données de réservation incomplètes.", "danger")
        return redirect(url_for('main.reservation_page', vehicule_id=vehicule_id))

    # 3) Parsing datetime-local -> datetime
    dt = parse_datetime_local(data.get('date_heure'))
    if not dt:
        flash("Format de date/heure invalide. Utilisez le sélecteur de date et d'heure.", "danger")
        return redirect(url_for('main.reservation_page', vehicule_id=vehicule_id))

    # 4) Conversions numériques sûres
    nb_passagers    = to_int(data.get('nb_passagers'), default=1)
    nb_v23          = to_int(data.get('nb_valises_23kg'), default=0)
    nb_v10          = to_int(data.get('nb_valises_10kg'), default=0)
    nb_sieges_bebe  = to_int(data.get('nb_sieges_bebe'), default=0)

    # 🔸 IMPORTANT: poids_enfants est un String(100) dans ton modèle
    poids_enfants_str = (data.get('poids_enfants') or '').strip() or None

    # 5) Création + commit
    try:
        r = Reservation(
            vehicule_id=vehicule_id,
            client_nom=(data.get('client_nom') or '').strip(),
            client_email=(data.get('client_email') or '').strip(),
            client_telephone=(data.get('client_telephone') or '').strip(),
            date_heure=dt,  # objet datetime requis
            vol_info=(data.get('vol_info') or '').strip(),
            adresse_depart=(data.get('adresse_depart') or '').strip(),
            adresse_arrivee=(data.get('adresse_arrivee') or '').strip(),
            nb_passagers=nb_passagers,
            nb_valises_23kg=nb_v23,
            nb_valises_10kg=nb_v10,
            nb_sieges_bebe=nb_sieges_bebe,
            poids_enfants=poids_enfants_str,  # ← string ou None
            paiement=(data.get('paiement') or '').strip(),
            commentaires=(data.get('commentaires') or '').strip(),
            statut='En attente'  # ← correspond au défaut du modèle
        )
        db.session.add(r)
        db.session.commit()
    except Exception as e:
        current_app.logger.exception(f"Erreur DB réservation: {e}")
        flash("Une erreur est survenue lors de l'enregistrement. Réessayez.", "danger")
        return redirect(url_for('main.reservation_page', vehicule_id=vehicule_id))

    # 6) Emails
    try:
        msg = Message(
            subject="Nouvelle réservation - DS Travel",
            sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
            recipients=[current_app.config.get('ADMIN_EMAIL')]
        )
        msg.body = f"""
Nouvelle réservation pour le véhicule {v.marque} {v.modele}

Nom : {r.client_nom}
Email : {r.client_email}
Téléphone : {r.client_telephone}
Départ : {r.adresse_depart}
Arrivée : {r.adresse_arrivee}
Date & Heure : {r.date_heure.strftime('%Y-%m-%d %H:%M')}
Numéro de vol/train : {r.vol_info or '-'}
Nombre de passagers : {r.nb_passagers}
Valises 23 kg : {r.nb_valises_23kg or 0}
Valises 10 kg : {r.nb_valises_10kg or 0}
Sièges bébé : {r.nb_sieges_bebe or 0}
Poids enfants : {r.poids_enfants or '-'}
Paiement : {r.paiement}
Commentaires : {r.commentaires or '-'}
"""
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Erreur email admin : {e}")
        flash("Réservation enregistrée mais l'e-mail n'a pas pu être envoyé à l'admin.", "warning")

    try:
        msg_client = Message(
            subject="Confirmation de votre réservation - DS Travel",
            sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
            recipients=[r.client_email]
        )
        msg_client.body = f"""
Bonjour {r.client_nom},

Nous confirmons la réception de votre réservation pour le véhicule {v.marque} {v.modele}.

Départ : {r.adresse_depart}
Arrivée : {r.adresse_arrivee}
Date & Heure : {r.date_heure.strftime('%Y-%m-%d %H:%M')}

Merci d’avoir choisi DS Travel.
Nous vous recontacterons pour confirmer votre réservation.
"""
        mail.send(msg_client)
    except Exception as e:
        current_app.logger.error(f"Erreur email client : {e}")
        flash("Réservation enregistrée mais l'e-mail de confirmation n'a pas pu être envoyé au client.", "warning")

    # Normalisation pour l'affichage
    data['date_heure'] = r.date_heure.strftime('%Y-%m-%d %H:%M')
    data['nb_passagers'] = str(r.nb_passagers)
    data['nb_valises_23kg'] = str(r.nb_valises_23kg or 0)
    data['nb_valises_10kg'] = str(r.nb_valises_10kg or 0)
    data['nb_sieges_bebe'] = str(r.nb_sieges_bebe or 0)
    data['poids_enfants'] = r.poids_enfants or '-'

    flash("Réservation enregistrée, nous vous contacterons.", "success")
    return render_template('fiche_vehicule.html', vehicule=v, data=data, form=ReservationForm())

# ------------------------
# Administration des réservations
# ------------------------
@main.route('/admin/reservations')
@admin_required
def reservations_admin():
    r = Reservation.query.order_by(Reservation.date_heure.desc()).all()
    return render_template('admin_reservations.html', reservations=r)

@main.route('/admin/reservation/valider/<int:id>')
@admin_required
def valider_reservation(id):
    r = Reservation.query.get_or_404(id)
    r.statut = "Confirmée"
    r.vehicule.disponible = False
    db.session.commit()
    flash("Réservation confirmée.", "success")
    return redirect(url_for('main.reservations_admin'))

@main.route('/admin/reservation/annuler/<int:id>')
@admin_required
def annuler_reservation(id):
    r = Reservation.query.get_or_404(id)
    r.statut = "Annulée"
    r.vehicule.disponible = True
    db.session.commit()
    flash("Réservation annulée.", "warning")
    return redirect(url_for('main.reservations_admin'))

@main.route('/admin/reservation/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_reservation(id):
    # TODO: Implémenter le formulaire d'édition
    flash("Page de modification à implémenter.", "info")
    return redirect(url_for('main.reservations_admin'))

@main.route('/admin/reservation/terminer/<int:id>')
@admin_required
def terminer_reservation(id):
    r = Reservation.query.get_or_404(id)
    r.statut = "Terminée"
    db.session.commit()
    flash("Réservation terminée.", "success")
    return redirect(url_for('main.reservations_admin'))

@main.route('/admin/reservation/delete/<int:id>')
@admin_required
def delete_reservation(id):
    r = Reservation.query.get_or_404(id)
    db.session.delete(r)
    db.session.commit()
    flash("Réservation supprimée.", "success")
    return redirect(url_for('main.reservations_admin'))

# ------------------------
# Tarifs (Forfaits et Règles)
# ------------------------
@main.route('/admin/tarifs', methods=['GET', 'POST'])
@admin_required
def tarifs_admin():
    form_forfait = AddTarifForfaitForm()
    form_regle = AddTarifRegleForm()

    if form_forfait.validate_on_submit() and request.form.get('form_name') == 'forfait':
        depart, arrivee = form_forfait.depart.data.strip(), form_forfait.arrivee.data.strip()
        doublon = TarifForfait.query.filter(
            db.or_(
                db.and_(TarifForfait.depart == depart, TarifForfait.arrivee == arrivee),
                db.and_(TarifForfait.bidirectionnel == True,
                        TarifForfait.depart == arrivee,
                        TarifForfait.arrivee == depart)
            )
        ).first()
        if doublon:
            flash("Un forfait identique existe déjà.", "warning")
        else:
            tf = TarifForfait(
                depart=depart,
                arrivee=arrivee,
                prix_cfa=form_forfait.prix_cfa.data,
                distance_km=form_forfait.distance_km.data,
                bidirectionnel=form_forfait.bidirectionnel.data,
                actif=form_forfait.actif.data
            )
            db.session.add(tf)
            db.session.commit()
            flash("Tarif forfaitaire ajouté.", "success")
        return redirect(url_for('main.tarifs_admin'))

    if form_regle.validate_on_submit() and request.form.get('form_name') == 'regle':
        tr = TarifRegle(
            base=form_regle.base.data,
            prix_km=form_regle.prix_km.data,
            minimum=form_regle.minimum.data or 0,
            coeff_nuit=form_regle.coeff_nuit.data or 1.0,
            coeff_weekend=form_regle.coeff_weekend.data or 1.0,
            actif=form_regle.actif.data
        )
        db.session.add(tr)
        db.session.commit()
        flash("Règle kilométrique ajoutée.", "success")
        return redirect(url_for('main.tarifs_admin'))

    forfaits = TarifForfait.query.order_by(TarifForfait.created_at.desc()).all()
    regles = TarifRegle.query.order_by(TarifRegle.created_at.desc()).all()
    return render_template('admin_tarifs.html', form_forfait=form_forfait, form_regle=form_regle,
                           forfaits=forfaits, regles=regles)

@main.route('/admin/tarifs/forfait/delete/<int:id>')
@admin_required
def delete_tarif_forfait(id):
    t = TarifForfait.query.get_or_404(id)
    db.session.delete(t)
    db.session.commit()
    flash("Forfait supprimé.", "success")
    return redirect(url_for('main.tarifs_admin'))

@main.route('/admin/tarifs/regle/delete/<int:id>')
@admin_required
def delete_tarif_regle(id):
    t = TarifRegle.query.get_or_404(id)
    db.session.delete(t)
    db.session.commit()
    flash("Règle supprimée.", "success")
    return redirect(url_for('main.tarifs_admin'))

@main.route('/admin/tarifs/forfait/toggle/<int:id>')
@admin_required
def toggle_tarif_forfait(id):
    t = TarifForfait.query.get_or_404(id)
    t.actif = not t.actif
    db.session.commit()
    flash("Statut du forfait modifié.", "info")
    return redirect(url_for('main.tarifs_admin'))

@main.route('/admin/tarifs/regle/toggle/<int:id>')
@admin_required
def toggle_tarif_regle(id):
    t = TarifRegle.query.get_or_404(id)
    t.actif = not t.actif
    db.session.commit()
    flash("Statut de la règle modifié.", "info")
    return redirect(url_for('main.tarifs_admin'))

# ------------------------
# Estimation de trajet
# ------------------------
@main.route('/estimation', methods=['POST'])
def estimation_trajet():
    depart = (request.form.get('depart') or "").strip()
    arrivee = (request.form.get('arrivee') or "").strip()
    if not depart or not arrivee:
        flash("Veuillez saisir un départ et une arrivée.", "danger")
        return redirect(url_for('main.home'))

    forfait = TarifForfait.query.filter(
        db.and_(
            TarifForfait.actif == True,
            db.or_(
                db.and_(TarifForfait.depart == depart, TarifForfait.arrivee == arrivee),
                db.and_(TarifForfait.bidirectionnel == True,
                        TarifForfait.depart == arrivee,
                        TarifForfait.arrivee == depart)
            )
        )
    ).first()

    if forfait:
        distance_km = forfait.distance_km
        temps_min = distance_km * 1.2
        tarif = f"{forfait.prix_cfa:,.0f} F CFA"
    else:
        regle = TarifRegle.query.filter_by(actif=True).first()
        if not regle:
            flash("Aucun tarif disponible.", "warning")
            return redirect(url_for('main.home'))
        try:
            distance_km, temps_min = get_distance_and_time(depart, arrivee)
        except Exception as e:
            flash(f"Erreur calcul distance : {e}", "danger")
            return redirect(url_for('main.home'))
        prix = regle.base + regle.prix_km * distance_km
        if prix < regle.minimum:
            prix = regle.minimum
        now = datetime.now()
        if now.hour >= 22 or now.hour < 6:
            prix *= regle.coeff_nuit
        if now.weekday() >= 5:
            prix *= regle.coeff_weekend
        distance_km = round(distance_km)
        temps_min = round(temps_min)
        tarif = f"{prix:,.0f} F CFA"

    vehicules = Vehicule.query.filter_by(disponible=True).limit(3).all()
    return render_template('home.html', vehicules=vehicules,
                           depart=depart, arrivee=arrivee,
                           distance_km=distance_km, temps_min=temps_min, tarif=tarif)

@main.route('/calculer_tarif', methods=['POST'])
def calculer_tarif():
    data = request.get_json() or {}
    depart = data.get('depart', '').strip()
    arrivee = data.get('arrivee', '').strip()
    if not depart or not arrivee:
        return jsonify({'error': 'Veuillez indiquer les adresses'}), 400

    forfait = TarifForfait.query.filter(
        db.and_(
            TarifForfait.actif == True,
            db.or_(
                db.and_(TarifForfait.depart == depart, TarifForfait.arrivee == arrivee),
                db.and_(TarifForfait.bidirectionnel == True,
                        TarifForfait.depart == arrivee,
                        TarifForfait.arrivee == depart)
            )
        )
    ).first()

    if forfait:
        distance_km = forfait.distance_km
        temps_min = round(distance_km * 1.2)
        prix = forfait.prix_cfa
    else:
        regle = TarifRegle.query.filter_by(actif=True).first()
        if not regle:
            return jsonify({'error': 'Aucun tarif disponible'}), 400
        try:
            distance_km, temps_min = get_distance_and_time(depart, arrivee)
        except Exception as e:
            return jsonify({'error': f'Erreur distance : {e}'}), 500
        prix = regle.base + regle.prix_km * distance_km
        if prix < regle.minimum:
            prix = regle.minimum
        now = datetime.now()
        if now.hour >= 22 or now.hour < 6:
            prix *= regle.coeff_nuit
        if now.weekday() >= 5:
            prix *= regle.coeff_weekend
        distance_km = round(distance_km)
        temps_min = round(temps_min)

    return jsonify({
        'distance_km': distance_km,
        'temps_min': temps_min,
        'tarif': f"{prix:,.0f} F CFA"
    })
