from ldap3 import Server, Connection, ALL, SUBTREE, MODIFY_REPLACE, Tls, SIMPLE
import ssl
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from flask import current_app as app

class ServiceProfile:
    def __init__(self, id: int, name: str, ou: str, groups: List[str], extras: str = "", 
                 manager: str = None, domains: List[str] = None, function: str = None, 
                 service: str = None, society: str = None, ip_telephony: bool = False,
                 samaccountname_suffix: str = None, commonname_suffix: str = None,
                 givenname_suffix: str = None, mail_suffix: str = None,
                 mailnickname_suffix: str = None, proxyaddresses_suffix: str = None,
                 targetaddress_suffix: str = None):
        self.id = id
        self.name = name
        self.ou = ou
        self.groups = groups
        self.extras = extras
        self.manager = manager
        self.domains = domains or []
        self.function = function
        self.service = service
        self.society = society
        self.ip_telephony = ip_telephony
        self.samaccountname_suffix = samaccountname_suffix
        self.commonname_suffix = commonname_suffix
        self.givenname_suffix = givenname_suffix
        self.mail_suffix = mail_suffix
        self.mailnickname_suffix = mailnickname_suffix
        self.proxyaddresses_suffix = proxyaddresses_suffix
        self.targetaddress_suffix = targetaddress_suffix

def init_service_profiles_db():
    """Initialise la base de données SQLite pour les profils de service"""
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    conn = sqlite3.connect(os.path.join(instance_path, 'service_profiles.db'))
    c = conn.cursor()
    
    # Création de la table des profils
    c.execute('''
        CREATE TABLE IF NOT EXISTS service_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            ou TEXT NOT NULL,
            groups TEXT,
            extras TEXT,
            manager TEXT,
            domains TEXT,
            function TEXT,
            service TEXT,
            society TEXT,
            ip_telephony BOOLEAN DEFAULT 0,
            samaccountname_suffix TEXT,
            commonname_suffix TEXT,
            givenname_suffix TEXT,
            mail_suffix TEXT,
            mailnickname_suffix TEXT,
            proxyaddresses_suffix TEXT,
            targetaddress_suffix TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Ajout des colonnes si elles n'existent pas
    try:
        c.execute('ALTER TABLE service_profiles ADD COLUMN manager TEXT')
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà

    try:
        c.execute('ALTER TABLE service_profiles ADD COLUMN domains TEXT')
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà

    # Ajout des nouvelles colonnes
    try:
        c.execute('ALTER TABLE service_profiles ADD COLUMN function TEXT')
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà

    try:
        c.execute('ALTER TABLE service_profiles ADD COLUMN service TEXT')
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà

    try:
        c.execute('ALTER TABLE service_profiles ADD COLUMN society TEXT')
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà

    try:
        c.execute('ALTER TABLE service_profiles ADD COLUMN ip_telephony BOOLEAN DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà

    # Ajout des colonnes de suffixes
    suffix_columns = [
        'samaccountname_suffix', 'commonname_suffix', 'givenname_suffix',
        'mail_suffix', 'mailnickname_suffix', 'proxyaddresses_suffix',
        'targetaddress_suffix'
    ]

    for column in suffix_columns:
        try:
            c.execute(f'ALTER TABLE service_profiles ADD COLUMN {column} TEXT')
        except sqlite3.OperationalError:
            pass  # La colonne existe déjà
    
    conn.commit()
    conn.close()

def get_service_profiles() -> List[ServiceProfile]:
    """Récupère tous les profils de service"""
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    conn = sqlite3.connect(os.path.join(instance_path, 'service_profiles.db'))
    c = conn.cursor()
    
    try:
        c.execute("""SELECT id, name, ou, groups, extras, manager, domains, 
                    function, service, society, ip_telephony,
                    samaccountname_suffix, commonname_suffix, givenname_suffix,
                    mail_suffix, mailnickname_suffix, proxyaddresses_suffix,
                    targetaddress_suffix FROM service_profiles""")
        profiles = []
        for row in c.fetchall():
            profiles.append(ServiceProfile(
                id=row[0],
                name=row[1],
                ou=row[2],
                groups=json.loads(row[3]),
                extras=row[4],
                manager=row[5],
                domains=json.loads(row[6]) if row[6] else None,
                function=row[7],
                service=row[8],
                society=row[9],
                ip_telephony=bool(row[10]),
                samaccountname_suffix=row[11],
                commonname_suffix=row[12],
                givenname_suffix=row[13],
                mail_suffix=row[14],
                mailnickname_suffix=row[15],
                proxyaddresses_suffix=row[16],
                targetaddress_suffix=row[17]
            ))
        return profiles
    finally:
        conn.close()

def get_service_profile(profile_id: int) -> Optional[ServiceProfile]:
    """Récupère un profil de service spécifique"""
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    conn = sqlite3.connect(os.path.join(instance_path, 'service_profiles.db'))
    c = conn.cursor()
    
    try:
        c.execute(
            """SELECT id, name, ou, groups, extras, manager, domains,
               function, service, society, ip_telephony,
               samaccountname_suffix, commonname_suffix, givenname_suffix,
               mail_suffix, mailnickname_suffix, proxyaddresses_suffix,
               targetaddress_suffix 
               FROM service_profiles WHERE id = ?""",
            (profile_id,)
        )
        row = c.fetchone()
        if row:
            return ServiceProfile(
                id=row[0],
                name=row[1],
                ou=row[2],
                groups=json.loads(row[3]),
                extras=row[4],
                manager=row[5],
                domains=json.loads(row[6]) if row[6] else None,
                function=row[7],
                service=row[8],
                society=row[9],
                ip_telephony=bool(row[10]),
                samaccountname_suffix=row[11],
                commonname_suffix=row[12],
                givenname_suffix=row[13],
                mail_suffix=row[14],
                mailnickname_suffix=row[15],
                proxyaddresses_suffix=row[16],
                targetaddress_suffix=row[17]
            )
        return None
    finally:
        conn.close()

def update_service_profile(profile_id: int, name: str, ou: str, groups: List[str], extras: str = "", 
                         manager: str = None, domains: List[str] = None, function: str = None,
                         service: str = None, society: str = None, ip_telephony: bool = False,
                         samaccountname_suffix: str = None, commonname_suffix: str = None,
                         givenname_suffix: str = None, mail_suffix: str = None,
                         mailnickname_suffix: str = None, proxyaddresses_suffix: str = None,
                         targetaddress_suffix: str = None) -> bool:
    """Met à jour un profil de service existant"""
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    conn = sqlite3.connect(os.path.join(instance_path, 'service_profiles.db'))
    c = conn.cursor()
    
    try:
        c.execute(
            """
            UPDATE service_profiles 
            SET name = ?, ou = ?, groups = ?, extras = ?, manager = ?, domains = ?, 
                function = ?, service = ?, society = ?, ip_telephony = ?, 
                samaccountname_suffix = ?, commonname_suffix = ?, givenname_suffix = ?,
                mail_suffix = ?, mailnickname_suffix = ?, proxyaddresses_suffix = ?,
                targetaddress_suffix = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (name, ou, json.dumps(groups), extras, manager, json.dumps(domains) if domains else None,
             function, service, society, 1 if ip_telephony else 0,
             samaccountname_suffix, commonname_suffix, givenname_suffix,
             mail_suffix, mailnickname_suffix, proxyaddresses_suffix,
             targetaddress_suffix, profile_id)
        )
        conn.commit()
        return c.rowcount > 0
    finally:
        conn.close()

def create_service_profile(name: str, ou: str, groups: List[str], extras: str = "", manager: str = None, 
                         domains: List[str] = None, function: str = None, service: str = None,
                         society: str = None, ip_telephony: bool = False,
                         samaccountname_suffix: str = None, commonname_suffix: str = None,
                         givenname_suffix: str = None, mail_suffix: str = None,
                         mailnickname_suffix: str = None, proxyaddresses_suffix: str = None,
                         targetaddress_suffix: str = None) -> int:
    """Crée un nouveau profil de service"""
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    conn = sqlite3.connect(os.path.join(instance_path, 'service_profiles.db'))
    c = conn.cursor()
    
    try:
        c.execute(
            """INSERT INTO service_profiles 
               (name, ou, groups, extras, manager, domains, function, service, society, ip_telephony,
                samaccountname_suffix, commonname_suffix, givenname_suffix,
                mail_suffix, mailnickname_suffix, proxyaddresses_suffix,
                targetaddress_suffix) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, ou, json.dumps(groups), extras, manager, json.dumps(domains) if domains else None,
             function, service, society, 1 if ip_telephony else 0,
             samaccountname_suffix, commonname_suffix, givenname_suffix,
             mail_suffix, mailnickname_suffix, proxyaddresses_suffix,
             targetaddress_suffix)
        )
        profile_id = c.lastrowid
        conn.commit()
        return profile_id
    finally:
        conn.close()

def delete_service_profile(profile_id: int) -> bool:
    """Supprime un profil de service"""
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    conn = sqlite3.connect(os.path.join(instance_path, 'service_profiles.db'))
    c = conn.cursor()
    
    try:
        c.execute("DELETE FROM service_profiles WHERE id = ?", (profile_id,))
        conn.commit()
        return c.rowcount > 0
    finally:
        conn.close()

def get_ldap_connection(user=None, password=None):
    """Établit une connexion au serveur LDAP"""
    from flask import session, current_app

    print("[LDAP] Initializing LDAP connection...")

    # Déterminer si on utilise LDAPS ou LDAP
    use_ssl_str = str(app.config.get('LDAP_USE_SSL', '')).lower().strip()
    use_ssl = use_ssl_str in ('true', '1', 'yes', 'on')
    print(f"[LDAP] Raw LDAP_USE_SSL value: {app.config.get('LDAP_USE_SSL')}")
    default_port = 636 if use_ssl else 389
    port = int(app.config.get('LDAP_PORT', default_port))  # Assure-toi que le port est bien un entier
    protocol = 'ldaps' if use_ssl else 'ldap'

    print(f"[LDAP] Connection settings:")
    print(f"[LDAP] - Protocol: {protocol}")
    print(f"[LDAP] - Server: {app.config['LDAP_SERVER']}")
    print(f"[LDAP] - Port: {port}")
    print(f"[LDAP] - SSL enabled: {use_ssl}")
    
    # Configuration TLS pour une connexion sécurisée si nécessaire
    tls = None
    if use_ssl:
        print("[LDAP] Configuring TLS settings...")
        tls = Tls(validate=ssl.CERT_NONE,  # En production, utilisez CERT_REQUIRED
                 version=ssl.PROTOCOL_TLSv1_2)
    
    server_url = app.config['LDAP_SERVER']  # Server hostname without protocol prefix
    print(f"[LDAP] Creating server connection to: {server_url}")
    
    try:
        server = Server(
            host=server_url,  # Just the hostname, Server class handles protocol internally
            port=port,
            use_ssl=use_ssl,
            tls=tls,
            get_info=ALL
        )
        print("[LDAP] Server connection created successfully")
    
        # Si aucun identifiant n'est fourni, utiliser ceux de la session
        if not user and not password:
            print("[LDAP] No credentials provided, checking session...")
            user = session.get('ldap_user')
            password = session.get('ldap_password')
            if not user or not password:
                print("[LDAP] No credentials found in session")
                raise Exception("Aucun identifiant LDAP disponible")
        
        print("[LDAP] Formatting username...")
        # Format du nom d'utilisateur pour AD
        if '@' not in user and '\\' not in user:
            domain = app.config.get('LDAP_DOMAIN', '')
            base_dn = app.config.get('BASE_DN', '')
            domain_parts = [part.split('=')[1] for part in base_dn.split(',') if part.startswith('DC=')]
            domain_name = '.'.join(domain_parts)
            formatted_user = f"{user}@{domain_name}"
            print(f"[LDAP] Username formatted as: {formatted_user}")
        else:
            formatted_user = user
            print("[LDAP] Username already properly formatted")

        print("[LDAP] Attempting to establish connection...")
        conn = Connection(
            server,
            user=formatted_user,
            password=password,
            authentication=SIMPLE,
            auto_bind=True,
            read_only=False,
            receive_timeout=30,  # timeout nécessaire pour les opérations de mot de passe
            auto_referrals=False  # nécessaire pour les opérations de mot de passe AD
        )
        print("[LDAP] Connection established successfully")
        return conn
    except Exception as e:
        print(f"[LDAP] Error during connection: {str(e)}")
        raise Exception(f"Erreur de connexion LDAP: {str(e)}")

def get_user(conn, dn):
    """Récupère un utilisateur spécifique"""
    conn.search(dn, '(objectClass=*)', SUBTREE, attributes=['*'])
    if len(conn.entries) > 0:
        return conn.entries[0]
    return None

def modify_user(conn, dn, changes):
    """Modifie un utilisateur"""
    try:
        result = conn.modify(dn, changes)
        return conn.result
    except Exception as e:
        return {'result': 1, 'description': str(e)}

def create_user(conn, user_info, groups=None):
    """Crée un nouvel utilisateur"""
    try:
        # Get schema to check for valid attributes
        schema = conn.server.schema
        if schema:
            # Filter out attributes that don't exist in schema
            valid_attributes = {k: v for k, v in user_info.items() 
                              if k == 'objectClass' or 
                              (k.lower() in [attr.lower() for attr in schema.attribute_types])}
        else:
            # If schema is not available, try without mailNickName and targetAddress
            valid_attributes = {k: v for k, v in user_info.items() 
                              if k not in ['mailNickName', 'targetAddress']}

        result = conn.add(valid_attributes['distinguishedName'], 
                         valid_attributes['objectClass'],
                         {k: v for k, v in valid_attributes.items() if k != 'objectClass'})
        
        if not result:
            return {'result': 1, 'description': f'LDAP Error: {conn.result["description"]}'}
        
        if result and groups:
            failed_groups = []
            for group in groups:
                try:
                    group_result = conn.extend.microsoft.add_members_to_groups(
                        [user_info['distinguishedName']], 
                        [group]
                    )
                    if not group_result:
                        failed_groups.append(group)
                except Exception as e:
                    failed_groups.append(f"{group} ({str(e)})")
            
            if failed_groups:
                return {
                    'result': 0,
                    'description': f'User created but failed to add to groups: {", ".join(failed_groups)}'
                }

        return {'result': 0, 'description': 'Success'}
    except Exception as e:
        return {'result': 1, 'description': f'Error creating user: {str(e)}'}

def search_users(conn, search_term=None, page_size=50, page=1, attributes=None, skip_pagination=False):
    """Recherche des utilisateurs dans l'AD avec pagination optionnelle"""
    if search_term:
        search_filter = f'(&(objectClass=user)(objectCategory=person)(|(cn=*{search_term}*)(sAMAccountName=*{search_term}*)(mail=*{search_term}*)))'
    else:
        search_filter = '(&(objectClass=user)(objectCategory=person))'
    
    # Use provided attributes or default ones
    if attributes is None:
        attributes = ['sn', 'givenName', 'sAMAccountName', 'mail', 'userAccountControl']
    
    # Effectuer la recherche
    conn.search(app.config['BASE_DN'], search_filter, attributes=attributes)
    total_entries = len(conn.entries)
    
    if skip_pagination:
        entries = conn.entries
    else:
        # Calculer l'offset pour la pagination
        offset = (page - 1) * page_size
        entries = conn.entries[offset:offset + page_size]
    
    return {
        'users': entries,
        'total': total_entries,
        'page': page,
        'total_pages': (total_entries + page_size - 1) // page_size
    }

def get_all_groups(conn, group_type=None):
    """Récupère tous les groupes AD avec leur DN et nom
    group_type peut être 'security' ou 'distribution' pour filtrer les groupes"""
    conn.search(app.config['BASE_DN'], '(objectClass=group)', attributes=['cn', 'groupType'])
    groups = {}
    for entry in conn.entries:
        if hasattr(entry, 'cn') and hasattr(entry, 'groupType'):
            is_security = int(entry.groupType.value) & 0x80000000
            # Si un type de groupe est spécifié, filtrer en conséquence
            if group_type == 'security' and not is_security:
                continue
            if group_type == 'distribution' and is_security:
                continue
            groups[entry.entry_dn] = entry.cn.value
    return groups

def generate_unique_phone_number(conn) -> str:
    """Génère un numéro de téléphone unique au format tel:+331384XXXX"""
    base = "tel:+331384"
    max_attempts = 1000
    
    print("[Phone Debug] Generating unique phone number")
    for _ in range(max_attempts):
        # Générer un nombre aléatoire à 4 chiffres
        import random
        suffix = f"{random.randint(0, 9999):04d}"
        phone = f"{base}{suffix}"
        
        # Vérifier si ce numéro existe déjà
        search_filter = f'(&(objectClass=user)(ipPhone={phone}))'
        print(f"[Phone Debug] Checking if phone number exists: {phone}")
        conn.search(app.config['BASE_DN'], search_filter, attributes=['ipPhone'])
        
        if len(conn.entries) == 0:
            print(f"[Phone Debug] Generated unique phone number: {phone}")
            return phone
    
    raise Exception("Could not generate a unique phone number after {max_attempts} attempts")

def move_to_trash(conn, dn):
    """Déplace un utilisateur vers la corbeille et le désactive"""
    try:
        from models import LDAPConfig
        config = LDAPConfig.get_config()
        if not config or not config.trash_ou:
            return {'result': 1, 'description': 'TRASH_OU configuration is missing in database'}

        user = get_user(conn, dn)
        if not user:
            return {'result': 1, 'description': 'User not found'}

        if not hasattr(user, 'cn'):
            return {'result': 1, 'description': 'User has no CN attribute'}

        new_dn = f"CN={user.cn.value},{config.trash_ou}"
        result = conn.modify_dn(dn, f"CN={user.cn.value}", new_superior=config.trash_ou)
        
        if not result:
            return {'result': 1, 'description': f'Failed to move user: {conn.result["description"]}'}

        return {'result': 0, 'description': 'Successfully moved to trash'}
    except Exception as e:
        return {'result': 1, 'description': f'Error moving user to trash: {str(e)}'}

def lock_unlock_user(conn, dn, lock=True):
    """Verrouille ou déverrouille un utilisateur"""
    try:
        changes = {
            'userAccountControl': [(MODIFY_REPLACE, ['514' if lock else '512'])],
            'lockoutTime': [(MODIFY_REPLACE, ['0'])]
        }
        result = modify_user(conn, dn, changes)
        return result
    except Exception as e:
        return {'result': 1, 'description': str(e)}

def trigger_ad_azure_sync():
    """Déclenche une synchronisation AD/Azure via le service AAD Connect"""
    try:
        import subprocess
        command = "Start-ADSyncSyncCycle -PolicyType Delta"
        process = subprocess.Popen(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise Exception(f"AD Azure sync failed: {stderr.decode()}")
        return True
    except Exception as e:
        raise

def apply_profile_to_existing_users(profile_id: int) -> bool:
    """Applique les paramètres d'un profil à tous les utilisateurs existants du service"""
    try:
        profile = get_service_profile(profile_id)
        if not profile:
            print("[Profile Debug] Profile not found")
            return False

        conn = get_ldap_connection()
        
        # 1. Identifier tous les utilisateurs dans l'OU spécifiée
        search_filter = '(&(objectClass=user)(objectCategory=person))'
        print(f"[Profile Debug] Searching users in OU: {profile.ou}")
        conn.search(profile.ou, search_filter, SUBTREE, attributes=['distinguishedName', 'memberOf'])
        
        if not conn.entries:
            print("[Profile Debug] No users found in the specified OU")
            return False

        success_count = 0
        failed_count = 0
        
        for user in conn.entries:
            try:
                current_groups = [g.lower() for g in user.memberOf.values] if hasattr(user, 'memberOf') else []
                groups_to_add = [g for g in profile.groups if g.lower() not in current_groups]
                
                if groups_to_add:
                    print(f"[Profile Debug] Adding user {user.distinguishedName.value} to groups: {groups_to_add}")
                    result = conn.extend.microsoft.add_members_to_groups(
                        [user.distinguishedName.value], 
                        groups_to_add
                    )
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                        print(f"[Profile Debug] Failed to add groups for user: {user.distinguishedName.value}")
                else:
                    success_count += 1
                    print(f"[Profile Debug] User {user.distinguishedName.value} already has all required groups")
                
            except Exception as e:
                failed_count += 1
                print(f"[Profile Debug] Error processing user {user.distinguishedName.value}: {str(e)}")

        print(f"[Profile Debug] Profile application completed. Success: {success_count}, Failed: {failed_count}")
        return success_count > 0

    except Exception as e:
        print(f"[Profile Debug] Error applying profile: {str(e)}")
        return False

def get_user_statistics(conn) -> Dict:
    """Récupère les statistiques sur les utilisateurs"""
    try:
        stats = {
            'total_users': 0,
            'active_users': 0,
            'inactive_users': 0,
            'disabled_users': 0,
            'expired_users': 0,
            'ou_distribution': {},
        }

        # Recherche de tous les utilisateurs
        base_filter = '(&(objectClass=user)(objectCategory=person))'
        conn.search(app.config['BASE_DN'], base_filter, attributes=[
            'userAccountControl', 'lastLogonTimestamp', 'accountExpires',
            'distinguishedName'
        ])

        inactive_threshold = datetime.now(tz=None) - timedelta(days=90)
        for user in conn.entries:
            try:
                stats['total_users'] += 1

                # Vérifier si le compte est désactivé
                if hasattr(user, 'userAccountControl'):
                    try:
                        uac = int(user.userAccountControl.value)
                        if uac & 2:  # ACCOUNTDISABLE flag
                            stats['disabled_users'] += 1
                    except (ValueError, TypeError) as e:
                        print(f"[Stats Debug] Error processing UAC: {str(e)}")

                # Vérifier la dernière connexion
                if hasattr(user, 'lastLogonTimestamp'):
                    try:
                        last_logon_value = user.lastLogonTimestamp.value
                        if last_logon_value is None:
                            stats['inactive_users'] += 1
                            continue
                            
                        if isinstance(last_logon_value, datetime):
                            last_logon = last_logon_value.replace(tzinfo=None)
                        else:
                            last_logon = datetime.fromtimestamp(
                                (int(last_logon_value) - 116444736000000000) // 10000000
                            ).replace(tzinfo=None)  # Make timezone-naive
                        if last_logon and last_logon > inactive_threshold:
                            stats['active_users'] += 1
                        else:
                            stats['inactive_users'] += 1
                    except (ValueError, TypeError) as e:
                        print(f"[Stats Debug] Error processing lastLogonTimestamp: {str(e)}")
                        stats['inactive_users'] += 1

                # Vérifier si le compte est expiré
                if hasattr(user, 'accountExpires'):
                    try:
                        if isinstance(user.accountExpires.value, datetime):
                            expiry_date = user.accountExpires.value
                        else:
                            expires = int(user.accountExpires.value)
                            if expires != 0 and expires != 9223372036854775807:
                                expiry_date = datetime.fromtimestamp(
                                    (expires - 116444736000000000) // 10000000
                                ).replace(tzinfo=None)  # Make timezone-naive
                            if expiry_date < datetime.now().replace(tzinfo=None):
                                stats['expired_users'] += 1
                    except (ValueError, TypeError) as e:
                        print(f"[Stats Debug] Error processing accountExpires: {str(e)}")

                # Distribution par OU
                if hasattr(user, 'distinguishedName'):
                    dn = user.distinguishedName.value
                    ou = ','.join([x for x in dn.split(',') if x.startswith('OU=')])
                    if ou:
                        stats['ou_distribution'][ou] = stats['ou_distribution'].get(ou, 0) + 1

            except Exception as e:
                print(f"[Stats Debug] Error processing user entry: {str(e)}")
                continue

        return stats

    except Exception as e:
        print(f"[Stats Debug] Error generating user statistics: {str(e)}")
        return {
            'total_users': 0,
            'active_users': 0,
            'inactive_users': 0,
            'disabled_users': 0,
            'expired_users': 0,
            'ou_distribution': {},
        }

def get_group_statistics(conn) -> Dict:
    """Récupère les statistiques sur les groupes"""
    try:
        stats = {
            'total_groups': 0,
            'security_groups': 0,
            'distribution_groups': 0,
            'avg_members': 0,
            'top_groups': [],
            'empty_groups': 0
        }

        # Recherche de tous les groupes
        conn.search(app.config['BASE_DN'], '(objectClass=group)', attributes=[
            'groupType', 'member', 'cn'
        ])

        total_members = 0
        group_sizes = []

        for group in conn.entries:
            try:
                stats['total_groups'] += 1

                # Type de groupe
                if hasattr(group, 'groupType'):
                    try:
                        group_type = int(group.groupType.value)
                        if group_type & 0x80000000:  # GROUP_TYPE_SECURITY_ENABLED
                            stats['security_groups'] += 1
                        else:
                            stats['distribution_groups'] += 1
                    except (ValueError, TypeError) as e:
                        print(f"[Stats Debug] Error processing group type: {str(e)}")

                # Nombre de membres
                member_count = len(group.member.values) if hasattr(group, 'member') else 0
                if member_count == 0:
                    stats['empty_groups'] += 1
                total_members += member_count
                
                if hasattr(group, 'cn'):
                    group_sizes.append((group.cn.value, member_count))

            except Exception as e:
                print(f"[Stats Debug] Error processing group: {str(e)}")
                continue

        # Moyenne des membres
        if stats['total_groups'] > 0:
            stats['avg_members'] = total_members / stats['total_groups']

        # Top 10 des groupes
        stats['top_groups'] = sorted(group_sizes, key=lambda x: x[1], reverse=True)[:10]

        return stats

    except Exception as e:
        print(f"[Stats Debug] Error generating group statistics: {str(e)}")
        return {
            'total_groups': 0,
            'security_groups': 0,
            'distribution_groups': 0,
            'avg_members': 0,
            'top_groups': [],
            'empty_groups': 0
        }

def get_security_statistics(conn) -> Dict:
    """Récupère les statistiques de sécurité"""
    try:
        stats = {
            'expired_passwords': 0,
            'never_changed_password': 0,
            'sensitive_groups': {},
            'admin_ou_distribution': {},
            'high_risk_users': []
        }

        sensitive_groups = [
            'Domain Admins', 'Enterprise Admins', 'Schema Admins',
            'Administrators', 'Account Operators', 'Backup Operators'
        ]

        # Recherche des utilisateurs avec des mots de passe expirés
        pwd_filter = '(&(objectClass=user)(objectCategory=person)(pwdLastSet=0))'
        conn.search(app.config['BASE_DN'], pwd_filter, attributes=['cn'])
        stats['never_changed_password'] = len(conn.entries)

        # Analyse des groupes sensibles
        for group in sensitive_groups:
            group_filter = f'(&(objectClass=group)(cn={group}))'
            conn.search(app.config['BASE_DN'], group_filter, attributes=['member'])
            if conn.entries:
                members = conn.entries[0].member.values if hasattr(conn.entries[0], 'member') else []
                stats['sensitive_groups'][group] = len(members)

                # Distribution des admins par OU
                for member_dn in members:
                    ou = ','.join([x for x in member_dn.split(',') if x.startswith('OU=')])
                    if ou:
                        stats['admin_ou_distribution'][ou] = stats['admin_ou_distribution'].get(ou, 0) + 1

                # Utilisateurs à haut risque
                for member_dn in members:
                    count = 0
                    for group_name, count_members in stats['sensitive_groups'].items():
                        if group_name in sensitive_groups:  # Only count sensitive groups
                            group_filter = f'(&(objectClass=group)(cn={group_name}))'
                            conn.search(app.config['BASE_DN'], group_filter, attributes=['member'])
                            if conn.entries and hasattr(conn.entries[0], 'member') and member_dn in conn.entries[0].member.values:
                                count += 1
                    if count > 1:
                        stats['high_risk_users'].append((member_dn, count))

        return stats

    except Exception as e:
        print(f"[Stats Debug] Error generating security statistics: {str(e)}")
        return {
            'expired_passwords': 0,
            'never_changed_password': 0,
            'sensitive_groups': {},
            'admin_ou_distribution': {},
            'high_risk_users': []
        }

def restore_user(conn, dn, target_ou):
    """Restaure un utilisateur depuis la corbeille et le réactive"""
    try:
        user = get_user(conn, dn)
        if not user:
            return {'result': 1, 'description': 'User not found'}

        # Déplacer l'utilisateur vers la nouvelle OU
        cn = dn.split(',')[0]  # Récupérer le CN de l'utilisateur
        new_dn = f"{cn},{target_ou}"
        result = conn.modify_dn(dn, cn, new_superior=target_ou)
        
        if not result:
            return {'result': 1, 'description': f'Failed to move user: {conn.result["description"]}'}

        # Réactiver le compte utilisateur
        changes = {
            'userAccountControl': [(MODIFY_REPLACE, ['512'])]  # 512 = Normal account
        }
        activation_result = modify_user(conn, new_dn, changes)
        
        if activation_result['result'] != 0:
            return {'result': 1, 'description': f'Failed to activate user: {activation_result["description"]}'}

        return {'result': 0, 'description': 'Successfully restored and activated user'}
    except Exception as e:
        return {'result': 1, 'description': f'Error restoring user: {str(e)}'}

def get_activity_statistics(conn) -> Dict:
    """Récupère les statistiques d'activité"""
    try:
        stats = {
            'disabled_users': [],
            'inactive_users_3months': [],
            'recent_password_changes': [],
            'locked_accounts': {
                'weekly': 0,
                'monthly': 0
            },
            'recent_creations': []
        }

        # Utilisateurs créés les 30 derniers jours
        seven_days_ago = datetime.now() - timedelta(days=30)
        when_created_filter = seven_days_ago.strftime('(&(objectClass=user)(objectCategory=person)(whenCreated>=%Y%m%d000000.0Z))')
        conn.search(app.config['BASE_DN'], 
                   when_created_filter, 
                   attributes=['cn', 'givenName', 'sn', 'whenCreated'])
        
        recent_creations = []
        for user in conn.entries:
            try:
                if hasattr(user, 'givenName') and hasattr(user, 'sn') and user.givenName.value and user.sn.value:
                    full_name = f"{user.givenName.value} {user.sn.value}"
                    recent_creations.append((full_name, user.whenCreated.value))
            except Exception as e:
                print(f"[Stats Debug] Error processing recent creation: {str(e)}")
                continue
        
        stats['recent_creations'] = sorted(recent_creations, key=lambda x: x[1], reverse=True)

        # Utilisateurs désactivés et inactifs
        user_filter = '(&(objectClass=user)(objectCategory=person))'
        conn.search(app.config['BASE_DN'], user_filter, attributes=[
            'cn', 'lastLogonTimestamp', 'userAccountControl'
        ])
        
        disabled_users = []
        inactive_users = []
        three_months_ago = datetime.now().replace(tzinfo=None) - timedelta(days=90)

        for user in conn.entries:
            try:
                # Get last logon time
                logon_time = None
                if hasattr(user, 'lastLogonTimestamp') and user.lastLogonTimestamp.value:
                    if isinstance(user.lastLogonTimestamp.value, datetime):
                        logon_time = user.lastLogonTimestamp.value.replace(tzinfo=None)
                    else:
                        logon_time = datetime.fromtimestamp(
                            (int(user.lastLogonTimestamp.value) - 116444736000000000) // 10000000
                        ).replace(tzinfo=None)

                if hasattr(user, 'givenName') and hasattr(user, 'sn'):
                    full_name = f"{user.givenName.value} {user.sn.value}"
                else:
                    full_name = user.cn.value

                # Check if user is disabled
                if hasattr(user, 'userAccountControl'):
                    uac = int(user.userAccountControl.value)
                    if uac & 2:  # ACCOUNTDISABLE flag
                        if not logon_time:
                            logon_time = datetime(1601, 1, 1)
                        disabled_users.append((full_name, logon_time))

                # Check if user is inactive (not disabled but no login for 3+ months)
                if logon_time and logon_time < three_months_ago:
                    if not hasattr(user, 'userAccountControl') or not (int(user.userAccountControl.value) & 2):
                        inactive_users.append((full_name, logon_time))

            except (ValueError, TypeError) as e:
                print(f"[Stats Debug] Error processing user data: {str(e)}")
                continue

        stats['disabled_users'] = sorted(disabled_users, key=lambda x: x[1], reverse=True)
        stats['inactive_users_3months'] = sorted(inactive_users, key=lambda x: x[1], reverse=True)

        # Derniers changements de mot de passe
        pwd_change_filter = '(&(objectClass=user)(objectCategory=person)(pwdLastSet=*))'
        conn.search(app.config['BASE_DN'], pwd_change_filter, attributes=[
            'cn', 'pwdLastSet'
        ])
        
        pwd_changes = []
        for user in conn.entries:
            try:
                if hasattr(user, 'pwdLastSet'):
                    if isinstance(user.pwdLastSet.value, datetime):
                        pwd_time = user.pwdLastSet.value
                    else:
                        pwd_time = datetime.fromtimestamp(
                            (int(user.pwdLastSet.value) - 116444736000000000) // 10000000
                        )
                    pwd_changes.append((user.cn.value, pwd_time))
            except (ValueError, TypeError) as e:
                print(f"[Stats Debug] Error processing password change time: {str(e)}")
        
        stats['recent_password_changes'] = sorted(pwd_changes, key=lambda x: x[1], reverse=True)[:10]

        # Comptes verrouillés (30 derniers jours)
        stats['locked_users'] = []
        month_ago = datetime.now().replace(tzinfo=None) - timedelta(days=30)
        
        locked_filter = '(&(objectClass=user)(objectCategory=person)(lockoutTime>=1))'
        conn.search(app.config['BASE_DN'], locked_filter, attributes=[
            'cn', 'givenName', 'sn', 'lockoutTime'
        ])
        
        for user in conn.entries:
            try:
                if hasattr(user, 'lockoutTime'):
                    if isinstance(user.lockoutTime.value, datetime):
                        lockout_time = user.lockoutTime.value.replace(tzinfo=None)
                    else:
                        try:
                            lockout_time = datetime.fromtimestamp(
                                (int(user.lockoutTime.value) - 116444736000000000) // 10000000
                            ).replace(tzinfo=None)
                        except (ValueError, OSError):
                            continue

                    if lockout_time and lockout_time > month_ago:
                        if hasattr(user, 'givenName') and hasattr(user, 'sn'):
                            full_name = f"{user.givenName.value} {user.sn.value}"
                        else:
                            full_name = user.cn.value
                        stats['locked_users'].append((full_name, lockout_time))
            except (ValueError, TypeError) as e:
                print(f"[Stats Debug] Error processing lockout time: {str(e)}")

        # Groupes vides
        group_filter = '(objectClass=group)'
        conn.search(app.config['BASE_DN'], group_filter, attributes=['cn', 'member'])
        
        stats['empty_groups'] = []
        for group in conn.entries:
            if hasattr(group, 'cn') and (not hasattr(group, 'member') or not group.member.values):
                stats['empty_groups'].append(group.cn.value)
        
        # Trier les listes
        stats['disabled_users'] = sorted(disabled_users, key=lambda x: x[1], reverse=True)
        stats['inactive_users_3months'] = sorted(inactive_users, key=lambda x: x[1], reverse=True)
        stats['locked_users'] = sorted(stats['locked_users'], key=lambda x: x[1], reverse=True)
        stats['empty_groups'] = sorted(stats['empty_groups'])

        return stats

    except Exception as e:
        print(f"[Stats Debug] Error generating activity statistics: {str(e)}")
        return {
            'recent_creations': [],
            'disabled_users': [],
            'inactive_users_3months': [],
            'locked_users': [],
            'empty_groups': []
        }
