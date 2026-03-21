/**
 * French UI copy (product UI language). Centralized for consistency.
 * [Source: architecture — Localization & UI language]
 */
export const fr = {
  appTitle: "semanticut",
  pageHeading: "État du backend",
  backendOk: "API : opérationnelle (base de données OK)",
  backendUnavailable:
    "API : indisponible ou erreur. Vérifiez que les services Docker sont démarrés.",
  homeLinkAdmin: "Administration",
  adminTitle: "Vidéos enregistrées",
  adminSubtitle: "État d’ingestion et progression",
  adminBackHome: "Accueil",
  adminLoading: "Chargement de la liste…",
  adminLoadError:
    "Impossible de charger les vidéos. Vérifiez l’API et réessayez.",
  adminInvalidPayload: "Réponse inattendue du serveur.",
  adminEmpty: "Aucune vidéo enregistrée pour le moment.",
  adminColLabel: "Libellé",
  adminColStatus: "Statut d’ingestion",
  adminColPhase: "Phase",
  adminColProgress: "Progression",
  /** Em dash placeholder when phase/progress unknown */
  adminDash: "—",
  adminNoProgress: "non disponible",
} as const;
