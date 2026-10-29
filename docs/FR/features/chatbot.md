# Chatbot

## Ce que ça fait

Le chatbot encapsule un LLM derrière un workflow piloté par la configuration, avec historique, exécution d’outils et intégration optionnelle au normalizer.

## Pourquoi c’est important

Les développeurs n’ont pas envie de reconstruire la même pile de conversation à chaque projet. Le chatbot centralise l’accès au modèle, l’usage des outils et le comportement de session.

## Exemple

```python
from mim_ai import Mim

app = Mim.from_config("mim_config.yaml")
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

## Outils limités par intention

Quand les outils et les intentions sont activés ensemble, chaque intention peut autoriser un ou plusieurs noms d’outils (`tools` dans le fichier d’intentions). L’ancien champ singulier `tool` reste pris en charge. Le modèle ne reçoit que les outils autorisés pour l’intention reconnue, et cette autorisation est vérifiée à nouveau avant l’exécution. Si des permissions par intention sont configurées, une intention non reconnue ne reçoit aucun outil. Une intention sert au routage, pas à l’autorisation : chaque outil doit vérifier lui-même les droits de l’appelant.

Le registre applicatif peut être injecté dans la façade MIM :

```python
from mim_ai import Mim
from mim_ai.chatbot import ToolRegistry, tool

tools = ToolRegistry()

@tool(
    "lookup_order",
    "Read an order belonging to the authenticated customer.",
    params={"order_id": {"type": "string"}},
    registry=tools,
)
def lookup_order(order_id: str) -> str:
    row = connection.execute(
        "SELECT status FROM orders WHERE id = ? AND customer_id = ?",
        (order_id, authenticated_customer_id),
    ).fetchone()
    return row["status"] if row else "not found"

app = Mim.from_config("mim_config.yaml", tool_registry=tools)
```

Les arguments du modèle sont non fiables : les types, les champs obligatoires et les champs supplémentaires sont validés avant l’appel. La fonction de l’application doit aussi vérifier les autorisations et les règles métier. Pour SQL, utilisez des paramètres liés pour les valeurs et des identifiants fixes ou autorisés par liste ; n’insérez jamais directement du texte utilisateur dans une requête. Le SDK ne fournit pas d’outil SQL générique et ne peut pas sécuriser automatiquement les fonctions fournies par l’application.

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
