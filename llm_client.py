"""Mini-abstraction LLM : route les appels vers Anthropic ou OpenRouter.

Le nom de modèle porte le provider en préfixe :
- "anthropic/<model>"   → SDK Anthropic natif (lit ANTHROPIC_API_KEY)
- "openrouter/<model>"  → SDK OpenAI pointé sur OpenRouter (lit OPENROUTER_API_KEY)

Exemple de configuration dans digest.py :
    FILTERING_MODEL = "anthropic/claude-haiku-4-5-20251001"
    SYNTHESIS_MODEL = "openrouter/openai/gpt-5"

L'interface est volontairement minimale : un seul point d'entrée
`complete(model, prompt, max_tokens)` qui retourne le texte de la réponse.
Si besoin de fonctionnalités plus avancées (streaming, tool use, vision…),
étendre cette interface en gardant le routage par préfixe.
"""

import os

from anthropic import Anthropic
from openai import OpenAI

# Clients initialisés à la demande pour éviter de demander une clé qui n'est
# pas utilisée si tu n'emploies qu'un seul fournisseur.
_anthropic_client: Anthropic | None = None
_openrouter_client: OpenAI | None = None


def _anthropic() -> Anthropic:
    """Singleton Anthropic. Lit ANTHROPIC_API_KEY depuis l'environnement."""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = Anthropic()
    return _anthropic_client


def _openrouter() -> OpenAI:
    """Singleton OpenRouter via SDK OpenAI. Lit OPENROUTER_API_KEY."""
    global _openrouter_client
    if _openrouter_client is None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY non défini — requis pour les modèles préfixés "
                "'openrouter/'."
            )
        _openrouter_client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
    return _openrouter_client


def complete(model: str, prompt: str, max_tokens: int) -> str:
    """Appelle le LLM désigné par `model` et retourne le texte de la réponse.

    Args:
        model: nom au format "<provider>/<modèle>".
            Exemples : "anthropic/claude-haiku-4-5-20251001",
                       "openrouter/openai/gpt-5",
                       "openrouter/google/gemini-2.5-flash".
        prompt: contenu utilisateur unique (un seul message role=user).
        max_tokens: cap sur la sortie du modèle.

    Returns:
        Le texte de la réponse, strippé.

    Raises:
        ValueError: si `model` ne porte pas de préfixe provider connu.
        RuntimeError: si la clé API requise est absente.
    """
    if model.startswith("anthropic/"):
        model_name = model.removeprefix("anthropic/")
        resp = _anthropic().messages.create(
            model=model_name,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()

    if model.startswith("openrouter/"):
        # Côté OpenRouter, le `model` porte déjà son propre slug "<vendeur>/<nom>".
        # Notre préfixe "openrouter/" est juste un routeur côté client : on le retire.
        model_name = model.removeprefix("openrouter/")
        resp = _openrouter().chat.completions.create(
            model=model_name,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()

    raise ValueError(
        f"Modèle '{model}' sans préfixe provider connu. "
        f"Utiliser 'anthropic/...' ou 'openrouter/...'."
    )
