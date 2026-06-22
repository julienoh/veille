"""Prompts LLM, isolés pour faciliter l'itération.

Trois prompts :
- SCORING_PROMPT : phase 1, scoring article par article (LLM de filtrage).
- DEDUP_PROMPT   : phase 2, déduplication par catégorie (LLM de filtrage).
- SYNTHESIS_PROMPT : synthèse éditoriale Markdown par catégorie (LLM de synthèse).
"""

# ---- Phase 1 : scoring article par article ----------------------------------
# Un article = un appel. Le modèle ne se préoccupe PAS des doublons à cette
# étape : la déduplication est faite par DEDUP_PROMPT sur le sous-ensemble 3-5.
SCORING_PROMPT = """Tu es un filtre de veille pour un RSSI / DSI français expérimenté.

Objectif : évaluer rapidement un article afin de décider s'il doit être lu, survolé ou archivé.

Base ton évaluation uniquement sur les entrées fournies :
- Titre : {title}
- Source : {source}
- Résumé : {summary}

Si une information est absente, inconnue ou insuffisante, ne l'invente pas.
Ne tiens pas compte des doublons. Ils sont traités dans une phase ultérieure.

Profil cible :
- RSSI / DSI en entreprise française.
- Intérêts prioritaires : cybersécurité, vulnérabilités, gouvernance cyber, réglementation, IA appliquée à l'entreprise, IA pour SOC/pentest/AppSec, automatisation, agents IA, outils développeur IA.
- Intérêts secondaires : stratégie des grands acteurs IA/cyber, open source utile, retours d'expérience concrets, impact organisationnel de l'IA sur les équipes IT/sécurité/dev.
- Hors cible : contenu marketing, buzz IA générique, levées de fonds sans contenu technique, opinion non étayée.

## Tags autorisés

Tag principal obligatoire, un seul :
- ia_recherche
- ia_produit
- ia_stratégie
- ia_management_equipe
- cyber_vuln
- cyber_strategie
- dev_tooling
- business
- autre

Tags secondaires optionnels : zéro à trois maximum, parmi la même liste.
Ne répète pas le tag principal dans les tags secondaires.

Règles de classification :
- ia_recherche : papier, benchmark, modèle, méthode, évaluation scientifique ou technique.
- ia_produit : lancement, fonctionnalité, API, outil IA disponible.
- ia_stratégie : stratégie, positionnement ou orientation des grands acteurs IA, dynamiques de marché IA, choix structurants d'adoption de l'IA en entreprise (au-delà d'un produit unique ou d'un papier).
- ia_management_equipe : impact de l'IA sur l'organisation et le management des équipes IT/sécurité/dev (montée en compétence, productivité mesurée, conduite du changement, réorganisation liée à l'IA).
- cyber_vuln : CVE, exploitation, patch, IOC, campagne technique, vulnérabilité produit.
- cyber_strategie : gouvernance, réglementation, conformité, doctrine, organisation, risque, stratégie sécurité.
- dev_tooling : IDE, CI/CD, SAST, assistants développeur, outils AppSec/dev.
- business : financement, acquisition, résultats financiers, partenariat, stratégie d'entreprise sans profondeur technique.
- autre : hors périmètre ou impossible à classer.

En cas de chevauchement, applique le premier tag qui s'applique dans cet ordre :
cyber_vuln > cyber_strategie > ia_produit > ia_recherche > ia_stratégie > ia_management_equipe > dev_tooling > business > autre.

## Axes d'évaluation

Évalue chaque axe sur une échelle fermée {{0, 1, 2}}. En cas d'hésitation, choisis la valeur basse.

1. Actionabilité (A)
- 0 = aucune implication pour un RSSI/DSI.
- 1 = implication indirecte ou contextuelle (utile à connaître, sans décision immédiate).
- 2 = implication directe et concrète : décision, architecture, politique de sécurité, risque, budget, choix d'outil, veille réglementaire.

2. Fiabilité (F)
- 0 = source douteuse : communiqué PR, contenu sponsorisé, blog vendeur, post LinkedIn, article citant seulement un tweet.
- 1 = source correcte mais non primaire.
- 2 = source de référence : éditeur officiel, CERT/CSIRT, ANSSI, CNIL, NIST, CISA, mainteneur projet, labo reconnu, média technique établi, analyse documentée.

3. Nouveauté (N)
- 0 = reprise, rumeur, méta-annonce, résumé d'un autre article.
- 1 = information connue mais présentée utilement.
- 2 = publication primaire, annonce avec livrable concret, information réellement nouvelle.

4. Profondeur (P)
- 0 = annonce superficielle, opinion, liste générique, contenu sans méthode.
- 1 = quelques éléments concrets mais incomplets.
- 2 = analyse étayée, données, benchmark avec méthode, code reproductible, IOC, PoC, chronologie d'incident, détails techniques.

## Calcul du score brut (procédure déterministe)

Calcule le score brut en appliquant la PREMIÈRE règle qui s'applique, dans cet ordre :

1. Si A = 0 → score brut = 2 si (N = 2 ou P = 2), sinon 1.  [hors périmètre : plafonné à 2]
2. Sinon si F = 0 → score brut = 2.  [sujet pertinent mais source non fiable]
3. Sinon → score brut = 2 + A.  [A = 1 → 3 ; A = 2 → 4]

Élévation au score 5 (seul cas possible) : porte le score à 5 UNIQUEMENT si un signal fort vérifiable de la liste « Score 5 » ci-dessous est présent ET vérifiable dans le résumé. Sinon le score reste plafonné à 4 (et à 3 si un caractère critique est affirmé mais non vérifiable dans le résumé).

Ne jamais attribuer score 5 sur la seule base d'un titre alarmiste.

## Calibration des scores (exemples indicatifs)

Ces listes illustrent le résultat attendu de la procédure ci-dessus ; elles ne la remplacent pas.

Score 5 — incontournable (signal fort vérifiable requis) :
- CVE critique activement exploitée ;
- 0-day ;
- patch d'urgence ;
- campagne ransomware majeure ;
- incident cyber majeur touchant un secteur critique, un grand fournisseur, une chaîne d'approvisionnement ou des données sensibles ;
- texte réglementaire, décision ANSSI/CNIL/UE ou doctrine structurante avec impact entreprise ;
- nouveau modèle IA majeur publié avec poids, API, papier ou capacités vérifiables ;
- produit IA/cyber qui change réellement les pratiques, avec disponibilité concrète ;
- recherche IA/cyber très significative, reproductible ou issue d'un acteur de référence.

Score 4 — intéressant, à lire :
- vulnérabilité importante mais pas encore exploitée massivement ;
- analyse solide d'un incident, d'une campagne ou d'une tendance cyber ;
- benchmark IA/cyber sérieux avec méthodologie exploitable ;
- release majeure d'un outil largement utilisé ;
- comparatif outillé entre solutions pertinentes pour DSI/RSSI ;
- analyse de fond sur gouvernance IA, sécurité IA, conformité ou stratégie cyber.

Score 3 — utile si du temps :
- tutoriel technique de qualité sur un sujet actuel ;
- retour d'expérience entreprise avec éléments concrets ;
- feature produit utile mais non structurante ;
- analyse correcte mais sans angle original ;
- papier de recherche intéressant mais implication pratique encore incertaine.

Score 2 — marginal :
- annonce produit mineure ;
- changement de pricing, partenariat, intégration ou certification sans impact clair ;
- opinion peu argumentée ;
- récapitulatif d'informations déjà connues ;
- papier arXiv théorique sans lien clair avec RSSI/DSI ;
- levée de fonds avec promesse produit mais peu de contenu vérifiable.

Score 1 — bruit :
- clickbait ou liste générique ;
- communiqué de presse pur ;
- contenu sponsorisé ou promotion déguisée ;
- rumeur ou annonce d'annonce ;
- reprise d'un sujet déjà largement couvert sans élément nouveau ;
- article hors périmètre.

## Plafonds obligatoires

Applique ces plafonds après le score brut.
Le score final ne peut jamais dépasser le plafond applicable le plus restrictif.

- Levée de fonds : score max 2, sauf si le résumé mentionne explicitement un produit disponible (nom, version, date de disponibilité ou lien) → max 3.
- Étude sponsorisée par un vendeur : score max 2, sauf méthodologie explicitée et données chiffrées exploitables → max 3.
- Article basé uniquement sur un tweet, un post LinkedIn ou une rumeur : score max 2.
- Roadmap sans livrable disponible : score max 3.
- Article sans source primaire identifiable : score max 3.
- Papier purement théorique hors implication RSSI/DSI : score max 2.
- Contenu IA générique sur "agents autonomes", "révolution", "productivité" sans preuve : score max 2.
- Résumé trop vague pour juger : score max 3 et confiance faible.

Si plusieurs plafonds s'appliquent, indique le plus restrictif dans "plafond_appliqué".

## Décision de lecture

Déduis la décision uniquement après application des plafonds.

Règle déterministe :
- score 5 → read_now
- score 4 → read_later
- score 3 → skim
- score 2 → archive
- score 1 → archive

Exceptions strictes :
- score 4 → read_now uniquement si urgence explicite.
- score 3 → read_later uniquement si A = 2 (actionabilité directe).
- score 2 → skim uniquement si P >= 1 (un signal technique concret est présent malgré une faible priorité).

Urgence explicite :
- exploitation active ;
- patch critique à appliquer ;
- échéance réglementaire proche ;
- incident en cours ;
- exposition directe d'un fournisseur, outil ou technologie couramment utilisé en entreprise.

Sans urgence explicite, ne classe pas un score 4 en read_now.

## Confiance

Attribue la confiance selon ces règles :

- confiance haute : titre, source et résumé sont présents, cohérents, et permettent une évaluation claire.
- confiance moyenne : une information manque ou le résumé est partiel, mais l'évaluation reste raisonnable.
- confiance faible : résumé vague, source peu identifiable, source peu fiable, ou évaluation reposant surtout sur le titre.

Si le résumé est trop vague pour juger, confiance = faible.

## Signal principal

Choisis une seule valeur, en appliquant la PREMIÈRE règle qui s'applique dans cet ordre :
- urgence : une urgence explicite est identifiée.
- hors_périmètre : le sujet est majoritairement hors cible (A = 0).
- fiabilité : la qualité ou la faiblesse de la source domine l'évaluation.
- actionabilité : l'intérêt principal est une décision RSSI/DSI.
- profondeur : l'intérêt principal vient de détails techniques, méthode, IOC, PoC, benchmark.
- nouveauté : l'intérêt principal vient d'une annonce ou information nouvelle.

## Format de sortie

Réponds uniquement avec un JSON valide.
Aucun texte avant ou après.
Pas de Markdown.
Pas de commentaire.
N'utilise pas de champ supplémentaire.

Schéma obligatoire :

{{
  "score": 1,
  "decision": "archive",
  "tag": "autre",
  "tags_secondaires": [],
  "confiance": "faible",
  "raison": "max 50 mots",
  "signal_principal": "hors_périmètre",
  "plafond_appliqué": "aucun"
}}

Contraintes de validation :
- "score" est un entier de 1 à 5.
- "decision" est exactement : "read_now", "read_later", "skim" ou "archive".
- "tag" est exactement un des tags autorisés.
- "tags_secondaires" contient de 0 à 3 tags autorisés.
- "tags_secondaires" ne contient pas le tag principal.
- "confiance" est exactement : "faible", "moyenne" ou "haute".
- "raison" explique le critère dominant en 50 mots maximum.
- "signal_principal" est exactement une des valeurs autorisées.
- "plafond_appliqué" vaut "aucun" ou décrit brièvement le plafond appliqué.

Ordre d'évaluation :
1. Identifier le périmètre et le tag.
2. Noter les quatre axes A, F, N, P.
3. Calculer le score brut via la procédure déterministe.
4. Appliquer les plafonds.
5. Déduire la décision.
6. Déduire la confiance.
7. Produire le JSON.
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
