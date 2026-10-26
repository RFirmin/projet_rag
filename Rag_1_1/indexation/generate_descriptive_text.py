import pandas as pd


def generate_descriptive_text(excel_path: str) -> str:
    """
    Génère un texte descriptif à partir du tableau Excel Canal+.

    Structure du fichier :
    - Ligne 0 : en-têtes fusionnés (INFO CHAINE, FORMULES, etc.)
    - Ligne 1 : sous-en-têtes (NUMERO, NOM DE LA CHAINE, ACCESS, etc.)
    - Ligne 2+ : données
    """

    # Charger avec la ligne 1 comme en-tête
    df = pd.read_excel(excel_path, header=1)

    # Nettoyer les noms de colonnes
    df.columns = [str(c).strip() for c in df.columns]

    # Identifier les colonnes clés
    col_numero = "NUMERO OU CANAL DE LA CHAINE"
    col_nom = "NOM DE LA CHAINE"

    # Vérifier que les colonnes existent
    if col_numero not in df.columns:
        raise KeyError(
            f"Colonne '{col_numero}' introuvable. Colonnes : {df.columns.tolist()}"
        )
    if col_nom not in df.columns:
        raise KeyError(
            f"Colonne '{col_nom}' introuvable. Colonnes : {df.columns.tolist()}"
        )

    # Colonnes de formules (toutes sauf numero et nom)
    cols_formules = [c for c in df.columns if c not in [col_numero, col_nom]]

    # Nettoyer les données
    df = df.dropna(subset=[col_nom])  # Ignorer les lignes sans nom de chaîne
    df[col_nom] = df[col_nom].astype(str).str.strip()

    # Générer le texte
    text = "# Chaînes Canal+ - Guide de référence\n\n"
    text += (
        f"*Document généré automatiquement depuis : {excel_path.split('/')[-1]}*\n\n"
    )
    text += f"*Nombre total de chaînes : {df[col_nom].nunique()}*\n\n"
    text += "---\n\n"

    # Grouper par nom de chaîne
    grouped = df.groupby(col_nom, sort=True)

    for entity, group in grouped:
        text += f"## {entity}\n\n"

        # Numéros
        numeros = group[col_numero].dropna().tolist()
        if numeros:
            numeros_str = ", ".join(str(int(n)) for n in numeros if pd.notna(n))
            text += f"**Numéros** : {numeros_str}\n\n"

        # Formules (colonnes où la valeur est "O")
        formules_incluses = []
        for col in cols_formules:
            valeurs = group[col].dropna().astype(str).str.strip().str.upper()
            if "O" in valeurs.tolist():
                formules_incluses.append(col)

        if formules_incluses:
            text += "**Formules incluses** :\n"
            for formule in formules_incluses:
                text += f"- {formule}\n"
            text += "\n"

        text += "---\n\n"

    return text


# text = generate_descriptive_text(
#     "books_to_index/TABLEAU FORMULE&CHAINES CANAL+.xlsx"
# )

# # Sauvegarder
# with open("guide_canal_plus.txt", "w", encoding="utf-8") as f:
#     f.write(text)

# print(f"✅ {len(text)} caractères générés")
# print(text[:2000])

df = pd.read_excel("books_to_index/TABLEAU FORMULE&CHAINES CANAL+.xlsx", header=1)

# Afficher les 5 premières lignes
print(df.head())

# Afficher les chaînes uniques
print(f"\nChaînes uniques : {df['NOM DE LA CHAINE'].nunique()}")
print(df["NOM DE LA CHAINE"].dropna().unique()[:20])
