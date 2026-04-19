"""Prompts Claude, isolés pour faciliter l'itération."""

# Scoring avec Haiku : est-ce que l'article mérite d'aller dans le digest ?
# Sortie JSON stricte pour parsing fiable.
SCORING_PROMPT = """Tu évalues la pertinence d'articles pour un RSSI / DSI
français passionné d'IA. Profil : cybersécurité, IA appliquée entreprise,
recherche IA, outils développeur (Claude Code, agents).

Pour chaque article, note de 1 à 5 :
- 5 : incontournable (nouveau modèle majeur, CVE critique, annonce stratégique)
- 4 : intéressant (nouveau produit, étude, analyse de fond)
- 3 : utile si du temps (tutorial, retour d'expérience)
- 2 : marginal (annonce mineure, opinion peu fondée)
- 1 : bruit (clickbait, promo déguisée, redondant)

Tags disponibles : ia_recherche, ia_produit, cyber_vuln, cyber_strategie,
dev_tooling, business, autre.

Article :
Titre : {title}
Source : {source}
Résumé : {summary}

Réponds UNIQUEMENT avec un JSON valide, aucun texte avant ou après :
{{"score": <1-5>, "tag": "<un des tags>", "raison": "<max 10 mots>"}}"""


# Synthèse Sonnet par catégorie. On donne 5-15 articles groupés.
SYNTHESIS_PROMPT = """Tu rédiges un digest de veille pour un RSSI / DSI français.
Catégorie : {category}
Période : {period}

Voici les articles sélectionnés (score ≥ 3), avec leur titre, source, résumé :

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
