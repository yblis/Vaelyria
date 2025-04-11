# Vaelyria - Active Directory Management Application

A complete Flask application for managing Active Directory accounts with advanced features including user management, group control, profile management, and Excel export capabilities.

## Feature Overview

### Dashboard

![Dashboard](screenshot/dashboard.png)

- Real-time overview of Active Directory status
- Quick access to all main features through an intuitive interface
- Quick search bar for users
- Shortcuts for user creation and group management

### Statistics

![Statistics](screenshot/stats.png)

- Detailed user statistics:
  - Total number of users
  - Active and inactive users
  - Disabled and expired accounts
- Group statistics:
  - Total number of groups
  - Distribution of security/distribution groups
  - Average members per group
  - Empty groups
- Interactive charts:
  - User distribution by OU
  - Top groups by number of members
- Activity metrics:
  - Recent logins
  - Password changes
  - Locked accounts
  - Recently created users
- Excel export for each statistics category

### User Management

![User Management](screenshot/Manage_users.png)

- Complete user list with advanced search capabilities
- Multiple filters:
  - Account status (active, disabled, locked, etc.)
  - Organizational unit
  - Domain
  - Email presence
- Dynamic column sorting
- Bulk user actions
- Export search results to Excel

#### User Creation

![User Creation](screenshot/Create_User.png)

- Streamlined user creation process
- Service profile selection for pre-filling attributes
- Automatic username generation according to configured rules
- Real-time username availability validation
- Extended attribute support:
  - Personal information
  - Professional contact details
  - Group membership
  - Email configuration

#### User Edition

![User Edition](screenshot/Edit_User.png)

- Complete user profile editing interface
- Personal and professional information management
- Account status control:
  - Enable/disable
  - Lock/unlock
- Group management with drag-and-drop interface
- Manager selection via dynamic search
- Action history and last login
- Password reset with advanced options

### Group Management

![Group Management](screenshot/Manage_groups.png)

- Intuitive group management interface
- Group search and filtering
- Creation of new groups with advanced parameters
- Member overview
- Export members to Excel with attribute selection

#### Group Creation

![Group Creation](screenshot/Create_Group.png)

- Intuitive group creation interface
- Group type selection:
  - Security group
  - Distribution group
- Scope configuration:
  - Domain local
  - Global
  - Universal
- Location (OU) selection via LDAP tree

#### Group Administration

![Group Administration](screenshot/Manage_Group.png)

- Complete member management:
  - Add/remove members
  - Dynamic user search
  - Multiple additions in a single operation
- Member export with attribute selection
- Group deletion or moving
- Moving interface with OU selection

### Profile Management

![Profile Management](screenshot/Manage_Profils.png)

- Service profile template management
- Profile list with quick actions
- Duplication of existing profiles
- Intuitive creation and editing interface

#### Profile Creation

![Profile Creation](screenshot/Create_Profil.png)

- Complete user attribute configuration:
  - Default OU
  - AD Groups
  - Domain
  - Manager
  - Function and service
- Attribute transformation rules:
  - sAMAccountName suffixes
  - Common name formats
  - Email configuration
- Support for additional JSON parameters

#### Profile Edition

![Profile Edition](screenshot/Edit_Profil.png)

- Modification of all profile parameters
- Interface identical to creation
- Transformation preview
- JSON parameter validation

### LDAP Configuration

![LDAP Settings](screenshot/Settings_ldap.png)

- Recycle Bin OU configuration
- Default password management with encryption
- AD domain configuration
- Microsoft 365 tenant settings
- Username format configuration:
  - Order (LASTNAME_FIRSTNAME or FIRSTNAME_LASTNAME)
  - Number of characters
  - Custom separator
- Email format configuration:
  - Order (LASTNAME_FIRSTNAME or FIRSTNAME_LASTNAME)
  - Number of characters
  - Custom separator
- Real-time format preview

### Activity Logging

![Activity Logs](screenshot/Logs.png)

- Complete action logging
- Multiple filters:
  - Period (24h, 7d, 30d, all)
  - Level (info, warning, error, critical)
  - Action type
  - User
- Result pagination
- Detailed display:
  - Timestamp
  - User
  - Action
  - Details
  - Level
  - IP Address

## Environment Variables

The application uses the following environment variables, defined in the `.env` file:

*   `FLASK_SECRET_KEY`: The secret key for signing session cookies.
*   `LDAP_SERVER`: The IP address or hostname of the LDAP server.
*   `BASE_DN`: The base Distinguished Name (DN) for the LDAP directory.
*   `LDAP_PORT`: The LDAP server port (default: 636 for LDAPS, 389 for LDAP).
*   `LDAP_USE_SSL`: Enables/disables SSL/TLS use for LDAP connection (true/false).
*   `AUTHORIZED_AD_GROUP`: The DN of the Active Directory group authorized to access the application.
*   `LOG_RETENTION_MONTH`: The number of months to retain logs (minimum: 1).

## Installation

1. Clone the repository

   ```bash
   git clone https://github.com/yblis/Vaelyria.git
   ```
2. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables

   - Copy `.env.exemple` to `.env`
   - Update variables according to your environment
4. Launch the application

   ```bash
   python app.py
   ```

## Docker

The application can be run in a Docker container using the provided `Dockerfile` and `docker-compose.yml` files.

To build the Docker image:

```bash
docker build -t vaelyria .
```

To run the application with Docker Compose:

```bash
docker-compose up -d
```

The `docker-compose.yml` file also includes configuration for Traefik, a modern HTTP reverse proxy with automatic HTTPS certificate management.

## System Requirements

- Python 3.8+
- Active Directory/LDAP Server
- Modern web browser with JavaScript enabled
- Network connectivity to AD server

## Main Dependencies

The application uses the following dependencies:

*   `Flask`: Python web framework.
*   `flask-sqlalchemy`: Flask extension for SQLAlchemy.
*   `flask-babel`: Internationalization and localization.
*   `ldap3`: Python LDAP client.
*   `openpyxl`: Excel file library.
*   `pandas`: Data analysis library.
*   `Werkzeug`: WSGI web library.
*   `flask-login`: User session management.
*   `python-dotenv`: Environment variable reading.
*   `cryptography`: Cryptography library.
*   `Flask-APScheduler`: Task scheduling.

## Security Features

- Secure LDAP communication via SSL/TLS (LDAPS)
- Role-based access control
- Complete action logging and auditing
- Secure session management
- Password encryption with Fernet
- User input validation
- CSRF attack protection
- Secure temporary password management

## Contributing

Contributions are welcome!

## 🛠️ License

This project is licensed under **AGPLv3**.  
You are allowed to use, modify and distribute it, provided you comply with the license terms, including the obligation to mention the original author.

**Vaelyria** - Active Directory Management Application is developed by **Djamal Boussefsaf**.  
[🔗 View full license here](LICENSE).

## Support

For support and feature requests, please open an issue in the project repository.
