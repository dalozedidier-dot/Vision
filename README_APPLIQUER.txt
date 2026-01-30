Implantation

Choisir un seul repo orchestrateur (recommandé: Vision).
Dans ce repo, à la racine:
- orchestrate_workflows.py
- targets.yml
- .github/workflows/orchestrate_all_modules.yml

Lancer dans GitHub web
- Actions
- Orchestrate all modules
- Run workflow

Secret recommandé
- GH_PAT

Pourquoi
- Le token github.token a souvent des limitations cross-repo.
- Sans PAT, tu risques des erreurs 403 / Resource not accessible / workflow not found.

Debug
- Le run produit _orchestrate_out/preflight avec la liste des workflows par repo.
- Télécharge l'artefact orchestrate_out et ouvre summary.json pour voir exactement quel appel a échoué.
