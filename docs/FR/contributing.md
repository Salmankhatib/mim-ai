# Contribuer à MIM

Merci de contribuer à l’amélioration de MIM.

## 1. Installation de l’environnement

```bash
python -m venv .venv
. .venv/bin/activate  # ou .venv\Scripts\activate sur Windows
pip install -e .
pip install pytest
```

## 2. Lancer les tests

```bash
pytest -q
```

## 3. Règles de contribution

- garder les changements petits et ciblés
- préserver la logique config-driven
- préférer un comportement optionnel plutôt que des hypothèses codées en dur
- documenter les nouveaux champs de configuration
- tester avec de vrais cas d’usage, pas seulement des mocks

## 4. Attentes avant un pull request

- expliquer clairement le problème et la solution
- mentionner les changements de configuration
- ajouter des exemples si le comportement change
- valider avec les tests adaptés

## 5. Directives de conception des fonctionnalités

Les fonctionnalités doivent rester :

- agnostiques vis-à-vis des fournisseurs
- pilotées par la configuration
- faciles à désactiver
- sûres en production

Merci de contribuer à une pile IA Darija pensée pour les développeurs marocains.
