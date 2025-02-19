# Flask-Babel Translation Guide

## Directory Structure
```
translations/
├── fr/
│   └── LC_MESSAGES/
│       ├── messages.po  (Translation file)
│       └── messages.mo  (Compiled translations)
└── en/
    └── LC_MESSAGES/
        ├── messages.po
        └── messages.mo
```

## Translation Workflow

1. Extract messages from your code to create or update the .pot file:
```bash
pybabel extract -F babel.cfg -o translations/messages.pot .
```

2. Create a new language catalog (first time only):
```bash
pybabel init -i translations/messages.pot -d translations -l fr  # For French
pybabel init -i translations/messages.pot -d translations -l en  # For English
```

3. Update existing translations:
```bash
pybabel update -i translations/messages.pot -d translations
```

4. Compile translations (after updating .po files):
```bash
pybabel compile -d translations
```

## Adding New Languages

1. Add the language code to LANGUAGES in app.py
2. Initialize the translation files for the new language:
```bash
pybabel init -i translations/messages.pot -d translations -l <language-code>
```
3. Edit the .po file in translations/<language-code>/LC_MESSAGES/
4. Compile the translations
