```mermaid
graph TB
    UI[UI Components]
    PWA[Progressive Web App]
    Static[Static Assets]
    Routes[Routes]
    Auth[Authentication]
    LDAP[LDAP Utils]
    Models[Data Models]
    Logs[Audit Logging]
    Users[User Management]
    Groups[Group Management]
    Profiles[Service Profiles]
    Settings[LDAP Settings]
    Stats[Statistics]

    UI --> PWA
    UI --> Static
    Routes --> Auth
    Routes --> LDAP
    Routes --> Models
    Routes --> Logs
    Users --> Routes
    Groups --> Routes
    Profiles --> Routes
    Settings --> Routes
    Stats --> Routes
```

```mermaid
graph LR
    A[app.py] --> B[routes]
    B --> C[templates]
    B --> D[static]
    A --> E[models.py]
    A --> F[ldap_utils.py]
    A --> G[audit_log.py]
    H[babel.cfg] --> I[translations]
    D --> K[CSS]
    D --> L[JavaScript]
    D --> M[Icons]
```

# Project Structure Explained

## Core Components

1. **Backend (Python/Flask)**
   - `app.py`: Main application entry point
   - `models.py`: Database models
   - `ldap_utils.py`: LDAP integration utilities
   - `audit_log.py`: Logging functionality

2. **Routes**
   - User management (`routes/users.py`)
   - Group management (`routes/groups.py`)
   - Authentication (`routes/auth.py`) 
   - Service profiles (`routes/service_profiles.py`)
   - Settings (`routes/settings.py`)
   - Logs (`routes/logs.py`)

3. **Frontend**
   - HTML templates in `templates/`
   - Static assets in `static/`
     - CSS styles
     - JavaScript modules
     - Icons for PWA
   - Progressive Web App support (`sw.js`, `manifest.json`)

4. **Internationalization**
   - Support for English and French
   - Translation files in `translations/`

## Key Features

1. **User Management**
   ![User Management](screenshot/Create_User.png)
   - Create, edit, and search users
   - Manage user attributes and permissions

2. **Group Management** 
   ![Group Management](screenshot/Manage_groups.png)
   - Create and manage groups
   - Assign members to groups

3. **Service Profiles**
   - Template-based profile management
   - Profile creation and editing

4. **LDAP Settings**
   ![LDAP Settings](screenshot/Settings_ldap.png)
   - Configure LDAP connection
   - Manage LDAP structure

5. **Monitoring**
   - Audit logging
   - Statistics dashboard
   ![Statistics](screenshot/stats.png)
