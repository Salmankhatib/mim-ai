# Audit et logging

## Ce que ça fait

MIM comprend un journal d’audit orienté conformité et un journal du normalizer. Ils sont conçus pour la traçabilité et le diagnostic opérationnel.

## Pourquoi c’est important

Les systèmes IA de production ont besoin de responsabilité. Les logs d’audit permettent la revue de conformité et le debug opérationnel.

## Exemple

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")
app.chat("salam", session_id="demo")
```

Les loggers d’audit et de normalizer sont configurés via l’objet principal de configuration et peuvent cibler différents backends.

## Bénéfices

- conforme par conception
- facile à interroger ensuite
- meilleur support pour la revue de production et le debugging
