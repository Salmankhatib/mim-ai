# Chatbot

## Ce que ça fait

Le chatbot encapsule un LLM derrière un workflow piloté par la configuration, avec historique, exécution d’outils et intégration optionnelle au normalizer.

## Pourquoi c’est important

Les développeurs n’ont pas envie de reconstruire la même pile de conversation à chaque projet. Le chatbot centralise l’accès au modèle, l’usage des outils et le comportement de session.

## Exemple

```python
from mim_ai import Mim

app = Mim.from_config("config.yaml")
reply = app.chat("salam, chkoun nta?", session_id="demo")
print(reply.text)
if reply.error:
    print(f"Échec de la requête : {reply.error}")
```

La configuration générée active par défaut le chat texte, sans exécution d’outils ni classification d’intentions. Personnalisez le prompt système dans la configuration, ou utilisez `system_prompt_file` et `system_prompt_extra` pour organiser des instructions plus longues :

```yaml
chatbot:
  enabled: true
  enable_tools: false
  use_intents: false
  system_prompt: |
    Vous êtes un assistant de support client serviable.
    Répondez dans la langue du client et n'inventez pas de règles.
  system_prompt_extra: |
    Si vous ne connaissez pas la réponse, dites-le et proposez un transfert à un humain.
```

Configurez `llm_endpoint`, `llm_model` et `llm_api_key_env` pour le service compatible avec l’API OpenAI. Si elle est définie, la variable d’environnement indiquée par `llm_api_key_env` est envoyée comme jeton Bearer. `app.chat()` renvoie un `ChatReply` ; utilisez `reply.text` pour obtenir le texte et vérifiez `reply.error` en cas d’échec du fournisseur.

## Clés de config

Les valeurs typiques de configuration comprennent :

- `chatbot.enabled`
- `chatbot.system_prompt`
- `chatbot.system_prompt_file`
- `chatbot.system_prompt_extra`
- `chatbot.llm_endpoint`
- `chatbot.llm_model`
- `chatbot.llm_api_key_env`
- `chatbot.enable_tools`
- `chatbot.use_intents`
- `chatbot.max_history_turns`
- `chatbot.use_normalizer`
- `chatbot.use_audit_log`

## Bénéfices

- intégration LLM plus simple
- continuité de session
- workflows basés sur des outils
- opérations de production plus propres
