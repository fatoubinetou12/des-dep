def send_via_sendgrid_async(to_email, subject, text):
    """
    Version améliorée avec validation de l'email
    """
    if not to_email or "@" not in to_email:
        current_app.logger.error(f"Email destinataire invalide: {to_email}")
        return

    app = current_app._get_current_object()
    api_key = (os.getenv("SENDGRID_API_KEY") or "").strip()
    sender = (os.getenv("MAIL_DEFAULT_SENDER") or os.getenv("MAIL_USERNAME") or "").strip()

    if not api_key:
        current_app.logger.error("SENDGRID_API_KEY manquant")
        return
    if not sender:
        current_app.logger.error("MAIL_DEFAULT_SENDER manquant")
        return

    def _job():
        with app.app_context():
            try:
                _sendgrid_request(to_email, subject, text, sender, api_key)
                app.logger.info(f"[SendGrid] envoyé à {to_email}")
            except Exception as e:
                app.logger.error(f"[SendGrid] échec vers {to_email}: {e}")

    Thread(target=_job, daemon=True).start()
