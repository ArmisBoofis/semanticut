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
  adminColActions: "Actions",
  adminDelete: "Supprimer",
  adminDeleteDialogTitle: "Supprimer cette vidéo ?",
  adminDeleteDialogBody:
    "Cette action est irréversible. La vidéo et les données d’ingestion associées seront supprimées.",
  adminDeleteCancel: "Annuler",
  adminDeleteConfirm: "Supprimer",
  adminDeleteSuccess: "La vidéo a été supprimée.",
  adminDeleteError:
    "Impossible de supprimer la vidéo. Vérifiez l’API et réessayez.",
  adminRegisterTitle: "Enregistrer une nouvelle vidéo",
  adminRegisterHint:
    "Choisissez un fichier vidéo et un libellé, puis validez pour lancer l’ingestion.",
  adminRegisterLabel: "Libellé",
  adminRegisterLabelPlaceholder: "Libellé affiché dans la liste",
  adminRegisterFile: "Fichier vidéo",
  adminRegisterSubmit: "Enregistrer",
  adminRegisterSubmitting: "Enregistrement…",
  adminRegisterSuccess: "Vidéo enregistrée. L’ingestion va démarrer.",
  adminRegisterLabelRequired: "Indiquez un libellé.",
  adminRegisterFileRequired: "Choisissez un fichier vidéo.",
  adminRegisterError:
    "Impossible d’enregistrer la vidéo. Vérifiez le fichier et réessayez.",
} as const;
