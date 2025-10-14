from flask import render_template
from flask_mail import Message
from app import mail

def envoyer_emails_reservation(reservation, vehicule):
    try:
        # Mail client
        msg_client = Message(
            subject="Confirmation de votre réservation - SD Travel",
            recipients=[reservation.client_email]
        )
        msg_client.body = render_template("emails/confirmation.txt", reservation=reservation, vehicule=vehicule)
        msg_client.html = render_template("emails/confirmation.html", reservation=reservation, vehicule=vehicule)
        mail.send(msg_client)

        # Mail admin (copie)
        msg_admin = Message(
            subject=f"Nouvelle réservation - {reservation.client_nom}",
            recipients=["admin@sdtravel.com"]  # <-- à adapter
        )
        msg_admin.body = render_template("emails/admin_notification.txt", reservation=reservation, vehicule=vehicule)
        msg_admin.html = render_template("emails/admin_notification.html", reservation=reservation, vehicule=vehicule)
        mail.send(msg_admin)

        return True
    except Exception as e:
        print("Erreur envoi email :", e)
        return False
