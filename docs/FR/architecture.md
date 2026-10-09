# Architecture MIM

## Objectif

MIM est conçu comme une pile d’application Darija config-first. Le développeur configure un seul fichier YAML, puis le package construit les composants nécessaires.

## Blocs principaux

### 1. Couche config

L’objet de configuration est la racine de l’application. Il contient :

- paramètres du normalizer
- paramètres d’audit et de logging
- paramètres du chatbot
- paramètres des intents
- paramètres de la voix, STT et TTS

Cela est chargé par la classe `MimConfig` et utilisé par le wrapper d’exécution `Mim`.

### 2. Normalizer

Le normalizer est la fonctionnalité la plus basse dans la pile. Il nettoie le Darija réel avant qu’il n’atteigne un modèle.

Il contient :

- couche de nettoyage
- couche de règles Darija
- couche optionnelle de raffinement LLM

### 3. Chatbot

Le chatbot encapsule un LLM compatible avec le standard OpenAI, gère l’usage d’outils, stocke l’historique de session et peut s’intégrer au normalizer et au système d’audit.

### 4. Pipeline vocal

Le pipeline vocal comprend :

- transcription STT
- éventuel passage dans le normalizer
- matching d’intents
- tour chatbot
- réponse TTS

### 5. Audit et logs

Les logs d’audit et les logs du normalizer sont séparés mais complémentaires. L’audit sert à la conformité et à la traçabilité, tandis que le normalizer log est plus opérationnel et diagnostique.

## Modèle d’exécution

L’application suit un modèle de composition hiérarchique :

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")
```

À l’exécution, les sous-systèmes sont créés à la demande. Si une fonctionnalité est désactivée dans la config, elle n’est pas construite.

## Pourquoi ce design fonctionne

- onboarding plus simple pour les développeurs
- déploiement plus sûr car le comportement est défini dans la config
- échange plus facile des fournisseurs et backends
- séparation claire entre logique applicative et infrastructure

## Déploiements de production

Ce package est conçu pour fonctionner avec :

- SQLite pour le dev/local
- PostgreSQL, MySQL ou MongoDB pour les déploiements durables
- endpoints de modèles compatibles OpenAI
- fournisseurs STT/TTS locaux ou cloud
