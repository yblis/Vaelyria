from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

    @staticmethod
    def get(user_id):
        from flask import session
        # Utiliser le nom d'utilisateur LDAP stocké dans la session
        username = session.get('ldap_user', 'Anonymous')
        return User(user_id, username)
