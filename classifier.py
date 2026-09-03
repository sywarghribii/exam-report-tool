def classify_defect(fails_text):
    """
    Analyse le texte d'échec et suggère une classe de défaut probable,
    en se basant sur des mots-clés caractéristiques.
    Retourne (classe_suggérée, raison, confiance).
    """
    if not fails_text:
        return ("Unclassified", "No failure text to analyze.", "low")

    text = fails_text.lower()

    # Règle 1 : problèmes de calibration/normalisation → souvent liés au banc de test
    if "nicht normiert" in text or "normiert=1" in text or "calibrat" in text:
        return (
            "Environment",
            "The failure mentions calibration/normalization ('nicht normiert'), "
            "which typically points to a test bench setup issue rather than a real product defect.",
            "medium"
        )

    # Règle 2 : timeout / délai dépassé → souvent un vrai problème de performance produit
    if "timeout" in text or "delai" in text or "exceeded" in text or "depasse" in text:
        return (
            "Product defect",
            "The failure mentions a timing/timeout issue, which often indicates "
            "a real performance problem in the tested software.",
            "medium"
        )

    # Règle 3 : capteur non détecté / communication perdue → environnement/matériel
    if "non detecte" in text or "not detected" in text or "communication" in text or "connexion" in text:
        return (
            "Environment",
            "The failure mentions a detection/communication issue, "
            "which often indicates a test bench or wiring problem.",
            "medium"
        )

    # Règle 4 : mots indiquant un comportement déjà documenté ailleurs
    if "known" in text or "jira" in text or "ticket" in text:
        return (
            "Known Issue",
            "The failure text references a known ticket/issue.",
            "high"
        )

    # Par défaut : pas assez d'indices clairs
    return (
        "Unclassified",
        "No strong keyword match found — manual review recommended.",
        "low"
    )