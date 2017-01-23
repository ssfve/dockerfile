# Welcome to MkDocs

For full documentation visit [mkdocs.org](http://mkdocs.org).

## Commands

* `mkdocs new [dir-name]` - Create a new project.
* `mkdocs serve` - Start the live-reloading docs server.
* `mkdocs build` - Build the documentation site.
* `mkdocs help` - Print this help message.

## Project layout

    mkdocs.yml    # The configuration file.
    docs/
        index.md  # The documentation homepage.
        ...       # Other markdown pages, images and other files.

-----------------------------------------------------

# Welcome to RTA4HC
## Todo Doc
* (Installation):
  * spark startup
  * Cassandra create keyspace and table(voir command dans installation.md).
* code source layout à documenter
  * where is java code (les 2 version)
  * where is python code
* Finir de nettoyer et copier InstallConfig-Kairosdb.md (if needed)
* Des choses à recuperer dans Test-cases.md ?

## Todo Engineering
* (VP) Code github apres demo (Cleanup)
* (VP) s’assurer de l’alignement des rta.properties, log.properties, rta_constants.py entre les 2 systems.
*	(VP) Tester sans le rta_dataset le demarrage de novelty_detect. Virer le module
*	(VP) Documenter le kairosdb-env.sh dans le bin et le mettre sur github
* (VP) documenter la config kafka qui est dans OneNote Testing > Integration-Activity
* (VP) Corriger dans novelty_detect ligne 627. Lorsque je recois un novelty_rate = 0 je pousse neanmoins la value dans kairosdb-env. Actuellement ca ne m'affiche rien et je crois que ca marche pas.
