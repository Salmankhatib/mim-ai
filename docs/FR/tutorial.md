# Tutoriel MIM

Ce guide est destiné aux développeurs qui veulent installer le package, charger la configuration et construire une application Darija en quelques minutes.

## 1. Installer

```bash
pip install mim-ai
```

Si vous travaillez depuis le dépôt local :

```bash
pip install -e .
```

## 2. Démarrer avec la config fournie

Le package est conçu pour fonctionner en mode config-first. Le fichier d’exemple par défaut est `mimExemple.yaml`.

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")
```

## 3. Normaliser le texte Darija

```python
text = "salam wa7ed 3la ekher, bghit n3ref kifach nt3amro app?"
clean = app.normalizer.normalize(text)
print(clean)
```

Cela est utile avant d’envoyer du texte utilisateur vers un LLM ou un workflow downstream.

## 4. Utiliser le chatbot

```python
reply = app.chat("salam, chkoun nta?", session_id="demo-user")
print(reply.text)
```

Cela appelle le LLM configuré et utilise le backend d’historique de session configuré.

## 5. Utiliser le pipeline vocal

```python
voice_reply = app.listen_and_reply(session_id="demo-user")
print(voice_reply.transcript)
print(voice_reply.reply_text)
```

Cela nécessite un microphone réel et une configuration STT/TTS fonctionnelle.

## 6. Bonnes pratiques

Conservez un seul fichier de configuration et changez les valeurs de fournisseur dans ce fichier au lieu de modifier le code. Cela simplifie les déploiements selon l’environnement.

## 7. Idée d’application minimale

Une petite application peut être construite avec :

- normalizer pour nettoyer l’arabe / l’Arabizi
- chatbot pour les conversations métier
- audit logger pour la traçabilité réglementaire
- pipeline vocal pour centre d’appels ou IVR

---

## Exemple de flux de projet

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")

raw = "salam, 3ndna 9a9a"
clean = app.normalizer.normalize(raw)
reply = app.chat(clean, session_id="demo")
print(reply.text)
```
