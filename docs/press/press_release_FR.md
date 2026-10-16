# COMMUNIQUÉ DE PRESSE

**POUR DIFFUSION IMMÉDIATE**

---

## Un Développeur Marocain Lance MIM-AI : Le SDK Open Source qui Connecte les Nouveaux Modèles IA Darija aux Applications de Production

**Premier kit de développement Python conçu spécifiquement pour le développement en Darija marocaine — aligné avec la convention MTNRA–Mistral et la feuille de route nationale Maroc IA 2030**

---

**Casablanca, Maroc — Octobre 2026** — Salman KHATIB, développeur logiciel marocain, annonce aujourd'hui la publication publique de **MIM-AI** (`pip install mim-ai`), un SDK Python open source qui comble le chaînon manquant entre les nouveaux modèles IA en Darija marocaine et les applications réelles.

Cette publication intervient en réponse directe à la **convention MTNRA–Mistral AI** signée en septembre 2025, qui a produit deux outils open source fondamentaux : un classificateur de dialecte Darija marocain et un modèle de reconnaissance vocale basé sur la technologie Voxtral de Mistral. MIM-AI est conçu pour s'intégrer nativement à ces deux outils.

---

### Le Problème que MIM-AI Résout

La feuille de route nationale **Maroc IA 2030** — visant 100 milliards de dirhams de contribution au PIB, 50 000 emplois et 200 000 talents formés — a accéléré la disponibilité de modèles IA en langue marocaine. Pourtant, un fossé critique persistait entre ces modèles fondamentaux et les applications de niveau production dont les citoyens, les entreprises et les services gouvernementaux ont besoin.

« Un développeur qui souhaite aujourd'hui construire une application vocale en Darija — un bot pour un centre d'appels, un assistant pour les services aux citoyens, une intégration vocale pour Idarati AI — doit encore résoudre cinq ou six problèmes d'infrastructure avant d'écrire sa première ligne de logique métier », déclare Khatib. « MIM-AI comble ce fossé entièrement. »

---

### Ce que MIM-AI Apporte

MIM-AI est un SDK Python *configuration-first* composé de cinq modules intégrés :

**🧹 Normaliseur Darija** — Traite les textes marocains réels en moins de 5 millisecondes, sans GPU. Gère l'Arabizi (arabe romanisé), le code-switching entre l'arabe, le Darija, le français et l'anglais, ainsi que l'orthographe irrégulière. Utilise un dictionnaire Arabizi artisanal plutôt qu'une translittération caractère par caractère, source d'ambiguïtés.

**🛡️ Anonymiseur PII** — Masque les données personnelles avec des patterns marocains natifs, notamment le format CIN (Carte d'Identité Nationale) et les numéros de téléphone marocains. Basé sur Microsoft Presidio avec des reconnaisseurs spécifiques au Maroc.

**🤖 Module Chatbot** — Enveloppe n'importe quel point de terminaison LLM compatible OpenAI — y compris l'API Darija de MNTRA/Mistral — avec gestion de session, détection d'intention et appel d'outils.

**🎙️ Pipeline Vocal** — Un pipeline complet reconnaissance vocale → normalisation → chatbot → synthèse vocale en un seul appel de méthode, configurable pour le modèle Voxtral de MNTRA.

**📜 Journal d'Audit** — Un journal d'événements à chaîne de hachage aligné sur la **Loi 09-08** marocaine sur la protection des données et la norme **ISO 42001** de management de l'IA. La conformité est activée par défaut.

---

### Alignement Stratégique

MIM-AI est explicitement conçu pour s'intégrer à l'écosystème IA souverain du Maroc :

- Pré-configuré pour les points de terminaison API MNTRA/Mistral
- L'implémentation du journal d'audit satisfait aux exigences de protection des données de la Loi 09-08
- Le pipeline vocal prend en charge le modèle ASR Voxtral publié dans le cadre de la convention MTNRA–Mistral
- L'architecture est conçue pour une future intégration avec la Marketplace Souveraine de l'IA et la plateforme de services publics Idarati AI

« Le gouvernement marocain a correctement identifié que l'IA souveraine nécessite à la fois des modèles fondamentaux et un écosystème local de développeurs, » précise Khatib. « MIM-AI est une contribution à cet écosystème — la couche de liaison qui transforme les modèles open source marocains en produits déployés. »

---

### Disponibilité

MIM-AI v0.1.0 est disponible immédiatement sous licence MIT :

- **PyPI :** `pip install mim-ai`
- **GitHub :** https://github.com/salmankhatib06/mim-ai
- **Documentation :** https://github.com/salmankhatib06/mim-ai/tree/main/docs/FR

Le package est compatible Python 3.9 à 3.12 et fonctionne sur toutes les plateformes. Les fonctionnalités principales (normalisation et anonymisation) fonctionnent entièrement hors ligne, sans API externe.

---

### À Propos du Développeur

Salman KHATIB est un développeur logiciel marocain spécialisé dans les outils IA de niveau production. MIM-AI est un projet open source développé indépendamment et publié au bénéfice de la communauté des développeurs marocains.

---

### Contact Médias

**Salman KHATIB**  
E-mail : slamankhatib06@gmail.com  
GitHub : https://github.com/salmankhatib06/mim-ai

---

*Les supports du dossier de presse, incluant la fiche technique et la présentation du projet, sont disponibles à l'adresse :*  
*https://github.com/salmankhatib06/mim-ai/tree/main/docs/press*

---

**###**