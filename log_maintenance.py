from datetime import datetime, timedelta
from models import db, AuditLog
from audit_log import log_user_action
from flask import current_app
import logging

def purge_old_logs(app):
    if current_app.config.get('PURGE_RUNNING', False):
        logging.warning("Une purge est déjà en cours, opération annulée")
        return
    
    try:
        current_app.config['PURGE_RUNNING'] = True
        with app.app_context():
            # Statistiques avant purge
            total_logs = db.session.query(AuditLog).count()
            logging.info(f"État initial : {total_logs} logs en base")
            
            # Calcul de la date limite
            retention_months = app.config['LOG_RETENTION_MONTH']
            cutoff_date = datetime.utcnow() - timedelta(days=retention_months * 30)
            
            # Suppression optimisée des logs
            deleted_count = db.session.query(AuditLog).filter(
                AuditLog.timestamp < cutoff_date
            ).delete()
            
            db.session.commit()
            
            # VACUUM si plus de 10% des logs ont été supprimés
            if deleted_count > 0 and (deleted_count / total_logs) > 0.1:
                logging.info("Plus de 10% des logs supprimés, optimisation de la base...")
                db.session.execute("VACUUM")
                db.session.commit()
                logging.info("Base de données optimisée après purge des logs")
            
            # Logs détaillés de l'opération
            message = (
                f"Purge automatique terminée :\n"
                f"- Logs supprimés : {deleted_count}\n"
                f"- Logs restants : {total_logs - deleted_count}\n"
                f"- Rétention : {retention_months} mois\n"
                f"- Date limite : {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"- Optimisation base : {'Oui' if deleted_count > 0 and (deleted_count / total_logs) > 0.1 else 'Non'}"
            )
            log_user_action('PURGE_LOGS', message, level='INFO')
            logging.info(message)
            
    except Exception as e:
        error_msg = f"Erreur lors de la purge des logs: {str(e)}"
        log_user_action('PURGE_LOGS_ERROR', error_msg, level='ERROR')
        logging.error(error_msg)
        
    finally:
        current_app.config['PURGE_RUNNING'] = False
