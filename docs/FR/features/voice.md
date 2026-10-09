# Pipeline vocal

## Ce que ça fait

Le pipeline vocal gère la transcription, la normalisation optionnelle, la détection d’intents, la conversation et la synthèse vocale.

## Pourquoi c’est important

La voix est l’un des moyens les plus naturels d’interagir avec une application, particulièrement dans les centres d’appels ou les flux terrain.

## Exemple

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")
reply = app.listen_and_reply(session_id="demo")
print(reply.transcript)
print(reply.reply_text)
```

## Clés de config

- `voice.enabled`
- `voice.use_normalizer`
- `voice.use_intents`
- `voice.use_audit_log`
- `stt.*`
- `tts.*`

## Bénéfices

- un seul pipeline vocal pour plusieurs fournisseurs
- facile à intégrer dans des flux IVR ou centres d’appels
- cohérence de l’application via la configuration
