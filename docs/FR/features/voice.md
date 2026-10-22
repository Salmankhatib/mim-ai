# Pipeline vocal

## Ce que ça fait

Le pipeline vocal gère la transcription, la normalisation optionnelle, la détection d’intents, la conversation et la synthèse vocale.

## Démarrage rapide

Installez le support vocal et ses dépendances audio Python :

```bash
pip install "mim-ai[voice]"
```

La voix utilise les périphériques microphone et haut-parleur par défaut. Le système peut également nécessiter des bibliothèques audio (par exemple PortAudio sous Linux). Configurez des endpoints STT/TTS accessibles dans `config.yaml`, puis définissez dans l’environnement les clés API indiquées par `stt.api_key_env` et `tts.api_key_env`. Si le pipeline vocal utilise le chatbot, définissez également `chatbot.llm_api_key_env`.

```python
from mim_ai import Mim

app = Mim.from_config("config.yaml")
reply = app.listen_and_reply(session_id="demo")
print(reply.transcript, reply.reply_text)
```

La capture utilise une détection VAD par énergie RMS. `voice.vad.threshold` est une amplitude RMS normalisée (valeur par défaut : `0.015`) ; `min_speech_ms` filtre les sons brefs, `min_silence_ms` termine une phrase, `pre_roll_ms` conserve son début, et `start_timeout_ms` évite l’appel STT si aucun son n’est détecté (`reply.status == "no_speech"`). `max_record_seconds` limite la durée. Cette méthode utilise un seuil, pas un classificateur vocal ; augmentez-le dans les environnements bruyants.

En l’absence de microphone ou de haut-parleur, les opérations audio lèvent `AudioError` au lieu d’envoyer du silence artificiel ou d’ignorer l’échec.

## Pourquoi c’est important

La voix est l’un des moyens les plus naturels d’interagir avec une application, particulièrement dans les centres d’appels ou les flux terrain.

## Exemple

```python
from mim_ai import Mim

app = Mim.from_config("config.yaml")
reply = app.listen_and_reply(session_id="demo")
print(reply.transcript)
print(reply.reply_text)
```

## Clés de config

- `voice.enabled`
- `voice.use_normalizer`
- `voice.use_intents`
- `voice.use_audit_log`
- `voice.max_record_seconds`
- `voice.vad.*`
- `voice.audio.*`
- `stt.*`
- `tts.*`

## Bénéfices

- un seul pipeline vocal pour plusieurs fournisseurs
- facile à intégrer dans des flux IVR ou centres d’appels
- cohérence de l’application via la configuration
