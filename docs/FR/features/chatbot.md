# Chatbot

## Ce que ça fait

Le chatbot encapsule un LLM derrière un workflow piloté par la configuration, avec historique, exécution d’outils et intégration optionnelle au normalizer.

## Pourquoi c’est important

Les développeurs n’ont pas envie de reconstruire la même pile de conversation à chaque projet. Le chatbot centralise l’accès au modèle, l’usage des outils et le comportement de session.

## Exemple

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")
reply = app.chat("salam, chkoun nta?", session_id="demo")
print(reply.text)
```

## Clés de config

Les valeurs typiques de configuration comprennent :

- `chatbot.enabled`
- `chatbot.system_prompt`
- `chatbot.enable_tools`
- `chatbot.max_history_turns`
- `chatbot.use_normalizer`
- `chatbot.use_audit_log`

## Bénéfices

- intégration LLM plus simple
- continuité de session
- workflows basés sur des outils
- opérations de production plus propres
