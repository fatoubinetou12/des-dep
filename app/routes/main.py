import os
import requests
from datetime import datetime
from functools import wraps
from threading import Thread

from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, flash, current_app, jsonify
)
from werkzeug.utils import secure_filename
from sqlalchemy import and_, or_

from app import db, mail  # mail peut rester importé même si on n'utilise plus SMTP
from app.forms.forms import (
    AdminLoginForm, AddVehiculeForm, ReservationForm,
    AddTarifForfaitForm, AddTarifRegleForm
)
from app.models.models import Vehicule, Reservation, TarifForfait, TarifRegle


# ========================
# Blueprint
# ========================
main = Blueprint("main", __name__)


# ========================
# Helpers
# ========================
def to_int(value, default=None):
    """Convertit en int ; renvoie default si vide/non convertible."""
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
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def get_distance_and_time(depart, arrivee):
    """Distance (km) + durée (min) via Google Distance Matrix."""
    key = current_app.config.get("GOOGLE_MAPS_KEY")
    if not key:
        raise Exception("Clé Google Maps manquante (GOOGLE_MAPS_KEY).")
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": depart,
        "destinations": arrivee,
        "mode": "driving",
        "units": "metric",
        "key": key,
    }
    r = requests.get(url, params=params, timeout=15)
    data = r.json()
    if data.get("status") != "OK":
        raise Exception(f"Erreur API Google : {data.get('status')}")
    element = data["rows"][0]["elements"][0]
    if element.get("status") != "OK":
        raise Exception(f"Impossible de calculer la distance : {element.get('status')}")
    distance_km = element["distance"]["value"] / 1000
    temps_min = element["duration"]["value"] / 60
    return distance_km, temps_min


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("main.login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


# ========================
# Envoi email via SendGrid (HTTP, pas SMTP)
# ========================
def _sendgrid_request(to_email, subject, text):
    api_key = os.getenv("SENDGRID_API_KEY")
    sender = os.getenv("MAIL_DEFAULT_SENDER") or os.getenv("MAIL_USERNAME")
    if not api_key:
        raise Exception("SENDGRID_API_KEY manquant (Render → Environment).")
    if not sender:
        raise Exception("MAIL_DEFAULT_SENDER manquant.")

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": sender},
        "subject": subject,
        "content": [{"type": "text/plain", "value": text}],
    }

    r = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )
    if r.status_code >= 400:
        raise Exception(f"Erreur SendGrid {r.status_code}: {r.text}")


def send_via_sendgrid_async(to_email, subject, text):
    # envoie dans un thread pour ne pas bloquer la requête web
    def _job():
        try:
            _sendgrid_request(to_email, subject, text)
        except Exception as e:
            current_app.logger.error(f"[SendGrid] Echec envoi vers {to_email}: {e}")

    Thread(target=_job, daemon=True).start()


# ========================
# Pages publiques
# ========================
@main.route("/")
def home():
    vehicules = Vehicule.query.filter_by(disponible=True).limit(6).all()
    transferts_populaires = (
        TarifForfait.query.filter_by(actif=True)
        .order_by(TarifForfait.created_at.desc())
        .limit(8)
        .all()
    )
    google_key = current_app.config.get("GOOGLE_MAPS_KEY")
    return render_template(
        "home.html",
        vehicules=vehicules,
        transferts_populaires=transferts_populaires,
        google_key=google_key,
    )


@main.route("/a-propos")
def about():
    return render_template("about.html")


# ========================
# Authentification admin
# ========================
@main.route("/login", methods=["GET", "POST"])
def login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        # ⚠️ À remplacer par une vraie vérification en BDD
        if form.username.data == "admin" and form.password.data == "admin123":
            session["admin_logged_in"] = True
            flash("Connexion admin réussie.", "success")
            return redirect(request.args.get("next") or url_for("main.admin_dashboard"))
        flash("Identifiants invalides.", "danger")
    return render_template("login.html", form=form)


@main.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    flash("Déconnexion effectuée.", "info")
    return redirect(url_for("main.home"))


# ========================
# Dashboard Admin - Véhicules
# ========================
@main.route("/admin/dashboard", methods=["GET", "POST"])
@admin_required
def admin_dashboard():
    form = AddVehiculeForm()
    vehicules = Vehicule.query.all()

    if form.validate_on_submit():
        if Vehicule.query.filter_by(immatriculation=form.immatriculation.data).first():
            flash("Un véhicule avec cette immatriculation existe déjà.", "danger")
            return redirect(url_for("main.admin_dashboard"))

        image_filename = None
        if form.photo.data:
            filename = secure_filename(form.photo.data.filename)
            folder = os.path.join(current_app.root_path, "static/images/vehicules")
            os.makedirs(folder, exist_ok=True)
            form.photo.data.save(os.path.join(folder, filename))
            image_filename = f"images/vehicules/{filename}"

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
            image=image_filename,
        )
        db.session.add(v)
        db.session.commit()
        flash("Véhicule ajouté avec succès !", "success")
        return redirect(url_for("main.admin_dashboard"))

    return render_template("dashboard.html", form=form, vehicules=vehicules)


@main.route("/vehicule/modifier/<int:id>", methods=["POST"])
@admin_required
def modifier_vehicule(id):
    v = Vehicule.query.get_or_404(id)
    for field in [
        "immatriculation", "marque", "modele", "caracteristiques_techniques",
        "type", "capacite_passagers", "volume_coffre_bagages", "volume_coffre_rabattus",
        "nb_sieges_bebe", "nb_valises", "details_coffre_toit",
    ]:
        setattr(v, field, request.form.get(field))

    v.coffre_de_toit = "coffre_de_toit" in request.form
    v.disponible = "disponible" in request.form

    img = request.files.get("photo")
    if img and img.filename:
        filename = secure_filename(img.filename)
        folder = os.path.join(current_app.root_path, "static/images/vehicules")
        os.makedirs(folder, exist_ok=True)
        img.save(os.path.join(folder, filename))
        v.image = f"images/vehicules/{filename}"

    db.session.commit()
    flash("Véhicule modifié avec succès.", "success")
    return redirect(url_for("main.admin_dashboard"))


@main.route("/vehicule/supprimer", methods=["GET"])
@admin_required
def supprimer_vehicule():
    v = Vehicule.query.get_or_404(request.args.get("id"))
    db.session.delete(v)
    db.session.commit()
    flash("Véhicule supprimé avec succès.", "success")
    return redirect(url_for("main.admin_dashboard"))


# ========================
# Réservations – Workflow client
# ========================
@main.route("/vehicules-disponibles")
def vehicules_disponibles():
    vehicules = Vehicule.query.filter_by(disponible=True).all()
    return render_template("vehicules_disponibles.html", vehicules=vehicules)


# 1) Formulaire
@main.route("/reservation/<int:vehicule_id>")
def reservation_page(vehicule_id):
    v = Vehicule.query.get_or_404(vehicule_id)
    google_key = current_app.config.get("GOOGLE_MAPS_KEY")
    return render_template("reservation.html", vehicule=v, form=ReservationForm(), google_key=google_key)


# 2) Récapitulatif
@main.route("/reservation/<int:vehicule_id>/recap", methods=["POST"])
def reservation_recap(vehicule_id):
    v = Vehicule.query.get_or_404(vehicule_id)
    form = ReservationForm()
    data = {k: (request.form.get(k) or "").strip() for k in [
        "client_nom", "client_email", "client_telephone", "date_heure", "vol_info",
        "adresse_depart", "adresse_arrivee", "nb_passagers", "nb_valises_23kg",
        "nb_valises_10kg", "nb_sieges_bebe", "poids_enfants", "paiement", "commentaires"
    ]}
    if not data["client_nom"] or not data["client_email"] or not data["adresse_depart"] or not data["adresse_arrivee"]:
        flash("Merci de remplir les informations obligatoires.", "danger")
        return redirect(url_for("main.reservation_page", vehicule_id=vehicule_id))
    return render_template("fiche_vehicule.html", vehicule=v, data=data, form=form)


# 3) Enregistrement + emails (POST)
@main.route("/reserver/<int:vehicule_id>", methods=["POST"])
def reserver_vehicule(vehicule_id):
    v = Vehicule.query.get_or_404(vehicule_id)

    # Collecte brute
    data = {k: request.form.get(k) for k in [
        "client_nom", "client_email", "client_telephone", "date_heure", "vol_info",
        "adresse_depart", "adresse_arrivee", "nb_passagers", "nb_valises_23kg",
        "nb_valises_10kg", "nb_sieges_bebe", "poids_enfants", "paiement", "commentaires"
    ]}

    # Validation minimum
    if not data["client_nom"] or not data["client_email"]:
        flash("Erreur : données de réservation incomplètes.", "danger")
        return redirect(url_for("main.reservation_page", vehicule_id=vehicule_id))

    # Date/heure
    dt = parse_datetime_local(data.get("date_heure"))
    if not dt:
        flash("Format de date/heure invalide. Utilisez le sélecteur de date et d'heure.", "danger")
        return redirect(url_for("main.reservation_page", vehicule_id=vehicule_id))

    # Conversions numériques
    nb_passagers   = to_int(data.get("nb_passagers"), default=1)
    nb_v23         = to_int(data.get("nb_valises_23kg"), default=0)
    nb_v10         = to_int(data.get("nb_valises_10kg"), default=0)
    nb_sieges_bebe = to_int(data.get("nb_sieges_bebe"), default=0)
    poids_enfants  = (data.get("poids_enfants") or "").strip() or None  # String(100)

    # Création + commit
    try:
        r = Reservation(
            vehicule_id=vehicule_id,
            client_nom=(data.get("client_nom") or "").strip(),
            client_email=(data.get("client_email") or "").strip(),
            client_telephone=(data.get("client_telephone") or "").strip(),
            date_heure=dt,
            vol_info=(data.get("vol_info") or "").strip(),
            adresse_depart=(data.get("adresse_depart") or "").strip(),
            adresse_arrivee=(data.get("adresse_arrivee") or "").strip(),
            nb_passagers=nb_passagers,
            nb_valises_23kg=nb_v23,
            nb_valises_10kg=nb_v10,
            nb_sieges_bebe=nb_sieges_bebe,
            poids_enfants=poids_enfants,
            paiement=(data.get("paiement") or "").strip(),
            commentaires=(data.get("commentaires") or "").strip(),
            statut="En attente",
        )
        db.session.add(r)
        db.session.commit()
    except Exception as e:
        current_app.logger.exception(f"Erreur DB réservation: {e}")
        flash("Une erreur est survenue lors de l'enregistrement. Réessayez.", "danger")
        return redirect(url_for("main.reservation_page", vehicule_id=vehicule_id))

    # Email admin (SendGrid)
    try:
        body_admin = f"""
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
        send_via_sendgrid_async(
            current_app.config.get("ADMIN_EMAIL"),
            "Nouvelle réservation - DS Travel",
            body_admin,
        )
    except Exception as e:
        current_app.logger.error(f"Erreur email admin (SendGrid) : {e}")
        flash("Réservation enregistrée mais l'e-mail admin n'a pas pu partir.", "warning")

    # Email client (SendGrid)
    try:
        body_client = f"""
Bonjour {r.client_nom},

Nous confirmons la réception de votre réservation pour le véhicule {v.marque} {v.modele}.

Départ : {r.adresse_depart}
Arrivée : {r.adresse_arrivee}
Date & Heure : {r.date_heure.strftime('%Y-%m-%d %H:%M')}

Merci d’avoir choisi DS Travel.
Nous vous recontacterons pour confirmer votre réservation.
"""
        send_via_sendgrid_async(
            r.client_email,
            "Confirmation de votre réservation - DS Travel",
            body_client,
        )
    except Exception as e:
        current_app.logger.error(f"Erreur email client (SendGrid) : {e}")
        flash("Réservation enregistrée mais l'e-mail client n'a pas pu partir.", "warning")

    # Normalisation pour affichage sur la même page
    data["date_heure"] = r.date_heure.strftime("%Y-%m-%d %H:%M")
    data["nb_passagers"] = str(r.nb_passagers)
    data["nb_valises_23kg"] = str(r.nb_valises_23kg or 0)
    data["nb_valises_10kg"] = str(r.nb_valises_10kg or 0)
    data["nb_sieges_bebe"] = str(r.nb_sieges_bebe or 0)
    data["poids_enfants"] = r.poids_enfants or "-"

    flash("Réservation enregistrée, nous vous contacterons.", "success")
    return render_template("fiche_vehicule.html", vehicule=v, data=data, form=ReservationForm())


# GET “pare-chocs” : si quelqu’un ouvre l’URL à la main
@main.route("/reserver/<int:vehicule_id>", methods=["GET"])
def reserver_vehicule_get(vehicule_id):
    return redirect(url_for("main.reservation_page", vehicule_id=vehicule_id))


# ========================
# Administration des réservations
# ========================
@main.route("/admin/reservations")
@admin_required
def reservations_admin():
    r = Reservation.query.order_by(Reservation.date_heure.desc()).all()
    return render_template("admin_reservations.html", reservations=r)


@main.route("/admin/reservation/valider/<int:id>")
@admin_required
def valider_reservation(id):
    r = Reservation.query.get_or_404(id)
    r.statut = "Confirmée"
    r.vehicule.disponible = False
    db.session.commit()
    flash("Réservation confirmée.", "success")
    return redirect(url_for("main.reservations_admin"))


@main.route("/admin/reservation/annuler/<int:id>")
@admin_required
def annuler_reservation(id):
    r = Reservation.query.get_or_404(id)
    r.statut = "Annulée"
    r.vehicule.disponible = True
    db.session.commit()
    flash("Réservation annulée.", "warning")
    return redirect(url_for("main.reservations_admin"))


@main.route("/admin/reservation/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_reservation(id):
    flash("Page de modification à implémenter.", "info")
    return redirect(url_for("main.reservations_admin"))


@main.route("/admin/reservation/terminer/<int:id>")
@admin_required
def terminer_reservation(id):
    r = Reservation.query.get_or_404(id)
    r.statut = "Terminée"
    db.session.commit()
    flash("Réservation terminée.", "success")
    return redirect(url_for("main.reservations_admin"))


@main.route("/admin/reservation/delete/<int:id>")
@admin_required
def delete_reservation(id):
    r = Reservation.query.get_or_404(id)
    db.session.delete(r)
    db.session.commit()
    flash("Réservation supprimée.", "success")
    return redirect(url_for("main.reservations_admin"))


# ========================
# Tarifs (Forfaits et Règles)
# ========================
@main.route("/admin/tarifs", methods=["GET", "POST"])
@admin_required
def tarifs_admin():
    form_forfait = AddTarifForfaitForm()
    form_regle = AddTarifRegleForm()

    if form_forfait.validate_on_submit() and request.form.get("form_name") == "forfait":
        depart, arrivee = form_forfait.depart.data.strip(), form_forfait.arrivee.data.strip()
        doublon = TarifForfait.query.filter(
            or_(
                and_(TarifForfait.depart == depart, TarifForfait.arrivee == arrivee),
                and_(
                    TarifForfait.bidirectionnel.is_(True),
                    TarifForfait.depart == arrivee,
                    TarifForfait.arrivee == depart,
                ),
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
                actif=form_forfait.actif.data,
            )
            db.session.add(tf)
            db.session.commit()
            flash("Tarif forfaitaire ajouté.", "success")
        return redirect(url_for("main.tarifs_admin"))

    if form_regle.validate_on_submit() and request.form.get("form_name") == "regle":
        tr = TarifRegle(
            base=form_regle.base.data,
            prix_km=form_regle.prix_km.data,
            minimum=form_regle.minimum.data or 0,
            coeff_nuit=form_regle.coeff_nuit.data or 1.0,
            coeff_weekend=form_regle.coeff_weekend.data or 1.0,
            actif=form_regle.actif.data,
        )
        db.session.add(tr)
        db.session.commit()
        flash("Règle kilométrique ajoutée.", "success")
        return redirect(url_for("main.tarifs_admin"))

    forfaits = TarifForfait.query.order_by(TarifForfait.created_at.desc()).all()
    regles = TarifRegle.query.order_by(TarifRegle.created_at.desc()).all()
    return render_template(
        "admin_tarifs.html",
        form_forfait=form_forfait,
        form_regle=form_regle,
        forfaits=forfaits,
        regles=regles,
    )


@main.route("/admin/tarifs/forfait/delete/<int:id>")
@admin_required
def delete_tarif_forfait(id):
    t = TarifForfait.query.get_or_404(id)
    db.session.delete(t)
    db.session.commit()
    flash("Forfait supprimé.", "success")
    return redirect(url_for("main.tarifs_admin"))


@main.route("/admin/tarifs/regle/delete/<int:id>")
@admin_required
def delete_tarif_regle(id):
    t = TarifRegle.query.get_or_404(id)
    db.session.delete(t)
    db.session.commit()
    flash("Règle supprimée.", "success")
    return redirect(url_for("main.tarifs_admin"))


@main.route("/admin/tarifs/forfait/toggle/<int:id>")
@admin_required
def toggle_tarif_forfait(id):
    t = TarifForfait.query.get_or_404(id)
    t.actif = not t.actif
    db.session.commit()
    flash("Statut du forfait modifié.", "info")
    return redirect(url_for("main.tarifs_admin"))


@main.route("/admin/tarifs/regle/toggle/<int:id>")
@admin_required
def toggle_tarif_regle(id):
    t = TarifRegle.query.get_or_404(id)
    t.actif = not t.actif
    db.session.commit()
    flash("Statut de la règle modifié.", "info")
    return redirect(url_for("main.tarifs_admin"))


# ========================
# Estimation de trajet (POST form)
# ========================
@main.route("/estimation", methods=["POST"])
def estimation_trajet():
    depart = (request.form.get("depart") or "").strip()
    arrivee = (request.form.get("arrivee") or "").strip()
    if not depart or not arrivee:
        flash("Veuillez saisir un départ et une arrivée.", "danger")
        return redirect(url_for("main.home"))

    forfait = TarifForfait.query.filter(
        and_(
            TarifForfait.actif.is_(True),
            or_(
                and_(TarifForfait.depart == depart, TarifForfait.arrivee == arrivee),
                and_(
                    TarifForfait.bidirectionnel.is_(True),
                    TarifForfait.depart == arrivee,
                    TarifForfait.arrivee == depart,
                ),
            ),
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
            return redirect(url_for("main.home"))
        try:
            distance_km, temps_min = get_distance_and_time(depart, arrivee)
        except Exception as e:
            flash(f"Erreur calcul distance : {e}", "danger")
            return redirect(url_for("main.home"))
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
    return render_template(
        "home.html",
        vehicules=vehicules,
        depart=depart,
        arrivee=arrivee,
        distance_km=distance_km,
        temps_min=temps_min,
        tarif=tarif,
    )


# ========================
# Calcul AJAX (JSON)
# ========================
@main.route("/calculer_tarif", methods=["POST"])
def calculer_tarif():
    data = request.get_json() or {}
    depart = data.get("depart", "").strip()
    arrivee = data.get("arrivee", "").strip()
    if not depart or not arrivee:
        return jsonify({"error": "Veuillez indiquer les adresses"}), 400

    forfait = TarifForfait.query.filter(
        and_(
            TarifForfait.actif.is_(True),
            or_(
                and_(TarifForfait.depart == depart, TarifForfait.arrivee == arrivee),
                and_(
                    TarifForfait.bidirectionnel.is_(True),
                    TarifForfait.depart == arrivee,
                    TarifForfait.arrivee == depart,
                ),
            ),
        )
    ).first()

    if forfait:
        distance_km = forfait.distance_km
        temps_min = round(distance_km * 1.2)
        prix = forfait.prix_cfa
    else:
        regle = TarifRegle.query.filter_by(actif=True).first()
        if not regle:
            return jsonify({"error": "Aucun tarif disponible"}), 400
        try:
            distance_km, temps_min = get_distance_and_time(depart, arrivee)
        except Exception as e:
            return jsonify({"error": f"Erreur distance : {e}"}), 500
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
        "distance_km": distance_km,
        "temps_min": temps_min,
        "tarif": f"{prix:,.0f} F CFA",
    })


# ========================
# Debug
# ========================
@main.route("/debug/routes")
def debug_routes():
    lines = []
    for rule in current_app.url_map.iter_rules():
        methods = ",".join(sorted(rule.methods))
        lines.append(f"{methods:20s} {rule.endpoint:30s} {rule.rule}")
    return "<pre>" + "\n".join(sorted(lines)) + "</pre>"


@main.route("/debug/sendgrid")
def debug_sendgrid():
    """Test d'envoi via SendGrid."""
    try:
        send_via_sendgrid_async(
            os.getenv("ADMIN_EMAIL"),
            "Test SendGrid DS Travel",
            "Ceci est un test d'envoi via SendGrid."
        )
        return "✅ Email (SendGrid) déclenché", 200
    except Exception as e:
        current_app.logger.exception("Echec test SendGrid")
        return f"❌ Erreur SendGrid : {e}", 500


@main.route("/debug/sendgrid-verbose")
def debug_sendgrid_verbose():
    try:
        api_key = os.getenv("SENDGRID_API_KEY")
        sender = os.getenv("MAIL_DEFAULT_SENDER") or os.getenv("MAIL_USERNAME")
        to_email = os.getenv("ADMIN_EMAIL") or sender

        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": sender},
            "subject": "Test SendGrid VERBOSE",
            "content": [{"type": "text/plain", "value": "Test verbose depuis DS Travel"}],
        }

        r = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        # SendGrid renvoie souvent 202 si accepté
        body = r.text.strip()
        return (
            f"Status: {r.status_code}\n"
            f"Response: {body if body else '<no body>'}\n"
            f"From: {sender}\nTo: {to_email}\n"
            f"SENDGRID_API_KEY: {'SET' if api_key else 'MISSING'}\n",
            200,
            {"Content-Type": "text/plain"},
        )
    except Exception as e:
        return f"Exception: {e}", 500, {"Content-Type": "text/plain"}

