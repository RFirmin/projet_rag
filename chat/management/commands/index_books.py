"""
Commande Django pour indexer les documents du dossier books_to_index/.

Usage :
    python manage.py index_books
    python manage.py index_books --output chunks_index_all.json
    python manage.py index_books --reset
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from Rag_1_1 import RAGPipeline


class Command(BaseCommand):
    help = "Indexe tous les documents du dossier books_to_index/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Chemin du fichier d'index de sortie (défaut: RAG_INDEX_PATH)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime l'index existant avant de réindexer",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=None,
            help="Taille des chunks (défaut: 1000 pour PDF, 1500 pour Excel)",
        )
        parser.add_argument(
            "--chunk-overlap",
            type=int,
            default=None,
            help="Chevauchement des chunks (défaut: 200 pour PDF, 300 pour Excel)",
        )

    def handle(self, *args, **options):
        # 1. Déterminer le dossier source
        books_dir = Path(settings.BASE_DIR) / "books_to_index"

        if not books_dir.exists():
            raise CommandError(
                f"Le dossier '{books_dir}' n'existe pas.\n"
                f"Créez-le et placez-y vos documents."
            )

        # 2. Lister les fichiers supportés
        supported_extensions = {
            ".pdf",
            ".xlsx",
            ".xls",
            ".docx",
            ".doc",
            ".csv",
            ".txt",
            ".md",
        }

        files = [
            f
            for f in books_dir.iterdir()
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]

        if not files:
            self.stdout.write(
                self.style.WARNING(f"Aucun document trouvé dans {books_dir}")
            )
            self.stdout.write(
                f"Extensions supportées : {', '.join(sorted(supported_extensions))}"
            )
            return

        # 3. Déterminer le fichier de sortie
        output_path = options["output"] or str(settings.RAG_INDEX_PATH)

        # 4. Supprimer l'ancien index si --reset
        if options["reset"] and Path(output_path).exists():
            Path(output_path).unlink()
            self.stdout.write(
                self.style.WARNING(f"Ancien index supprimé : {output_path}")
            )

        # 5. Afficher le résumé
        self.stdout.write(
            self.style.SUCCESS(f"\n{'=' * 60}\n" f"INDEXATION\n" f"{'=' * 60}")
        )
        self.stdout.write(f"Dossier source : {books_dir}")
        self.stdout.write(f"Fichier index  : {output_path}")
        self.stdout.write(f"Documents      : {len(files)}\n")

        for f in files:
            size_mb = f.stat().st_size / (1024 * 1024)
            self.stdout.write(f"  • {f.name} ({size_mb:.2f} Mo)")

        # 6. Construire la liste des configs
        file_configs = []
        for f in files:
            metadata = {
                "title": f.stem,  # Nom sans extension
                "author": "Unknown",
            }

            config = {
                "file_path": str(f),
                "metadata": metadata,
            }

            # Ajouter les options de chunking si précisées
            if options["chunk_size"]:
                config["chunk_size"] = options["chunk_size"]
            if options["chunk_overlap"]:
                config["chunk_overlap"] = options["chunk_overlap"]

            file_configs.append(config)

        # 7. Lancer l'indexation
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Traitement en cours...")
        self.stdout.write("=" * 60 + "\n")

        try:
            pipeline = RAGPipeline(index_path=output_path)
            all_chunks = pipeline.index_documents(
                file_configs=file_configs,
                output_path=output_path,
            )

        except Exception as e:
            raise CommandError(f"Erreur lors de l'indexation : {e}")

        # 8. Afficher le résumé final
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✓ INDEXATION TERMINÉE"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total de chunks : {len(all_chunks)}")
        self.stdout.write(f"Fichier index   : {output_path}")

        # Statistiques par source
        sources = {}
        for chunk in all_chunks:
            source = chunk.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

        self.stdout.write("\nDétail par document :")
        for source, count in sorted(sources.items()):
            self.stdout.write(f"  • {source} : {count} chunks")

        self.stdout.write("")
