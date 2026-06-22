"""Prompts LLM, isolés pour faciliter l'itération.

Trois prompts :
- SCORING_PROMPT : phase 1, scoring article par article (LLM de filtrage).
- DEDUP_PROMPT   : phase 2, déduplication par catégorie (LLM de filtrage).
- SYNTHESIS_PROMPT : synthèse éditoriale Markdown par catégorie (LLM de synthèse).
"""

# ---- Phase 1 : scoring article par article ----------------------------------
# Un article = un appel. Le modèle ne se préoccupe PAS des doublons à cette
# étape : la déduplication est faite par DEDUP_PROMPT sur le sous-ensemble 3-5.
SCORING_PROMPT = """Tu es un expert en curation de contenu Internet : tu filtres et sélectionnes des articles pour un public d'experts.

Objectif : évaluer rapidement un article afin de décider s'il doit être lu, survolé ou archivé.

Public d'experts :
- RSSI français expérimenté
- CTO français expérimenté
- Développeur expérimenté
- Architecte SI expérimenté

Base ton évaluation uniquement sur les entrées fournies :
- Titre : {title}
- Source : {source}
- Résumé : {summary}

Si une information est absente, inconnue ou insuffisante, ne l'invente pas.
Ne tiens pas compte des doublons.

Sujets :
- Cible : cybersécurité, vulnérabilités, gouvernance cyber, réglementation, IA en entreprise, SOC/pentest/AppSec, automatisation, agents IA, dev tooling, stratégie des acteurs IA/cyber, open source utile, retours d'expérience, organisation des équipes.
- Hors cible : marketing, buzz IA générique, levées de fonds sans contenu technique, opinion non étayée.

## Tags

Classe l'information avec 1 à 3 tags parmi :
- ia_recherche : papier, benchmark, modèle, méthode, évaluation scientifique ou technique.
- ia_produit : lancement, fonctionnalité, API, outil IA disponible.
- ia_stratégie : stratégie, positionnement ou orientation des grands acteurs IA, dynamiques de marché IA, choix structurants d'adoption de l'IA en entreprise.
- ia_management_equipe : impact de l'IA sur l'organisation et le management des équipes IT/sécurité/dev.
- cyber_vuln : CVE, exploitation, patch, IOC, campagne technique, vulnérabilité produit.
- cyber_strategie : gouvernance, réglementation, conformité, doctrine, organisation, risque, stratégie sécurité.
- dev_tooling : IDE, CI/CD, SAST, assistants développeur, outils AppSec/dev.
- business : financement, acquisition, résultats financiers, partenariat, stratégie d'entreprise sans profondeur technique.
- autre : hors périmètre ou impossible à classer.

## Score (procédure déterministe)

Attribue un score de 1 à 5 en appliquant la PREMIÈRE règle qui correspond.

Score 5 — incontournable (signal fort vérifiable requis) :
- annonce stratégique majeure ;
- CVE critique, 0-day, patch critique, incident de sécurité en cours ;
- campagne ransomware majeure ;
- incident cyber majeur touchant un secteur critique, un grand fournisseur, une chaîne d'approvisionnement ou des données sensibles ;
- texte réglementaire, décision ANSSI/CNIL/UE ou doctrine structurante avec impact entreprise, échéance réglementaire proche ;
- nouveau modèle IA majeur ;
- produit IA/cyber qui change réellement les pratiques ;
- recherche IA/cyber très significative, reproductible ou issue d'un acteur de référence ;
- impact direct sur une techno utilisée en entreprise.

Score 4 — intéressant, à lire :
- vulnérabilité importante mais pas encore exploitée massivement ;
- analyse solide d'un incident, d'une campagne ou d'une tendance cyber ;
- benchmark IA/cyber sérieux avec méthodologie exploitable ;
- release majeure d'un outil largement utilisé ;
- comparatif outillé entre solutions pertinentes pour le public d'experts ;
- analyse de fond sur gouvernance IA, sécurité IA, conformité ou stratégie cyber.

Score 3 — utile si du temps :
- tutoriel technique de qualité sur un sujet actuel ;
- retour d'expérience entreprise avec éléments concrets ;
- feature produit utile mais non structurante ;
- analyse correcte mais sans angle original ;
- papier de recherche intéressant, même si l'implication pratique reste incertaine.

Score 2 — marginal :
- annonce produit mineure ;
- changement de pricing, partenariat, intégration ou certification sans impact clair ;
- opinion peu argumentée ;
- récapitulatif d'informations déjà connues ;
- levée de fonds avec promesse produit mais peu de contenu vérifiable.

Score 1 — bruit :
- clickbait ou liste générique ;
- communiqué de presse pur ;
- contenu sponsorisé ou promotion déguisée ;
- rumeur ou annonce d'annonce ;
- reprise d'un sujet déjà largement couvert sans élément nouveau ;
- article hors périmètre.

## Décision de lecture (déterministe)

- score 5 -> read_now
- score 4 -> read_later
- score 3 -> skim
- score 2 -> archive
- score 1 -> archive

## Format de sortie

Réponds uniquement avec un JSON valide, aucun texte autour, pas de Markdown.

Schéma obligatoire :

{{
  "score": 1,
  "decision": "archive",
  "tags": [],
  "raison": "max 40 mots"
}}

Contraintes :
- "score" est un entier de 1 à 5.
- "decision" est exactement read_now, read_later, skim ou archive.
- "tags" contient 1 à 3 tags de la liste autorisée.
- "raison" explique le facteur principal en 40 mots maximum.
"""


# ---- Phase 2 : déduplication par catégorie OPML -----------------------------
# Reçoit la liste indexée des articles 3-5 d'une catégorie. Retourne des
# clusters de doublons + l'article canonique à garder. Les autres seront
# rétrogradés en decision=archive, score=2 par digest.py.
DEDUP_PROMPT = """Tu reçois une liste d'articles déjà filtrés (score 3-5) qui appartiennent à la catégorie "{category}".

Ta tâche : identifier les doublons — articles qui couvrent le même sujet factuel (même incident, même vulnérabilité, même annonce produit, même papier).

Pour chaque groupe de doublons, désigne l'article canonique à garder, selon ces critères dans l'ordre :
1. Source primaire (éditeur officiel, mainteneur, labo, CERT) avant source secondaire.
2. Article le plus complet ou le plus précis.
3. Source la plus fiable (média technique reconnu vs blog ou récap).

Les articles uniques (qui ne sont dans aucun groupe) ne doivent PAS apparaître dans ta réponse.

## Articles à comparer

{articles}

## Format de sortie

Réponds uniquement avec un JSON valide. Aucun texte avant ou après.

Schéma :

{{
  "groupes": [
    {{
      "sujet": "résumé court du sujet commun",
      "ids": [0, 3, 7],
      "canonical_id": 3,
      "raison": "max 20 mots"
    }}
  ]
}}

Si aucun doublon n'est détecté, renvoie : {{"groupes": []}}

Contraintes :
- "ids" doit contenir au moins 2 entiers correspondant aux index donnés.
- "canonical_id" doit être l'un des "ids".
- "raison" explique pourquoi le canonique a été choisi."""


# ---- Synthèse éditoriale par catégorie --------------------------------------
SYNTHESIS_PROMPT = """Tu rédiges un digest de veille pour un RSSI / DSI français.
Catégorie : {category}
Période : {period}

Voici les articles sélectionnés, avec leur titre, source, résumé :

{articles}

Rédige un digest structuré :
1. Pour chaque article, 1 à 2 phrases en français disant CE QU'IL FAUT RETENIR
   (pas une paraphrase du titre). Aller à l'essentiel.
2. Regroupe les articles qui parlent du même sujet sous une même puce.
3. Si un sujet revient de plusieurs sources, mentionne-le ("Selon X et Y, ...").
4. Ton : pro mais direct, pas de langage marketing ni de superlatifs.

Format de sortie Markdown :

## {category}

- **<Titre court du sujet>** : <synthèse>. [Source 1](url) · [Source 2](url)
- **<Titre court>** : <synthèse>. [Source](url)

Rien d'autre. Pas d'intro, pas de conclusion."""
