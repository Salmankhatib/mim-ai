# Normalizer

## Ce que ça fait

Le normalizer nettoie le texte utilisateur avant qu’il n’atteigne un modèle. Il traite le bruit Darija comme l’Arabizi, la ponctuation incohérente, les variations d’orthographe et les mélanges de scripts.

## Pourquoi c’est important

Un modèle donne de meilleurs résultats quand l’entrée est contrôlée. Plus le texte est propre, plus le risque de confusion, de mauvaise classification et de mauvaise génération est faible.

## Comment ça fonctionne

Le normalizer est un pipeline en trois couches :

1. couche de nettoyage
2. couche Darija par règles
3. couche optionnelle de raffinement LLM

## Exemple

```python
from mim_ai import Mim

app = Mim.from_config("mimExemple.yaml")
text = "salam wa7ed 3la ekher, bghit n3ref kifach nt3amro app?"
print(app.normalizer.normalize(text))
```

## Clés de config

Dans la config, le normalizer peut être paramétré via :

- `normalizer.enabled`
- `normalizer.cleaning`
- `normalizer.rules`
- `normalizer.llm`

## Bénéfices

- plus rapide qu’un nettoyage basé uniquement sur un modèle
- compatible avec les schémas de texte Darija
- facile à ajuster avec des dictionnaires personnalisés
