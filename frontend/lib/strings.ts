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
  homeReadyVideosHeading: "Vidéos prêtes pour la recherche",
  homeReadyVideosHelper:
    "Seules les vidéos dont l’ingestion est terminée sont disponibles ici.",
  homeReadyVideosLoading: "Chargement des vidéos prêtes…",
  homeReadyVideosError:
    "Impossible de charger les vidéos. Vérifiez l’API puis réessayez.",
  homeReadyVideosEmpty:
    "Aucune vidéo prête pour la recherche. Lancez l’ingestion depuis la page Administration.",
  homeSearchHeading: "Recherche sémantique",
  homeSearchQueryLabel: "Requête",
  homeSearchQueryPlaceholder: "Décrivez ce que vous cherchez…",
  homeSearchSubmit: "Rechercher",
  homeSearchSubmitting: "Recherche en cours…",
  homeSearchNoVideoSelected:
    "Sélectionnez une vidéo prête dans la liste ci-dessus pour lancer une recherche.",
  homeSearchSnippetTitle: "Extrait trouvé",
  /** Full coarse context around the fine match (two-pass retrieval). */
  homeSearchMacroContextTitle: "Contexte oral",
  homeSearchMatchQualityStrong: "Pertinence : correspondance forte",
  homeSearchMatchQualityPartial: "Pertinence : correspondance partielle",
  homeSearchMatchQualityWeak: "Pertinence : correspondance faible",
  /** Screen reader hint for the highlighted fine span inside macro text. */
  homeSearchPassageHighlightAria: "Passage retenu pour la lecture",
  homeSearchPlaybackFromPrefix: "Lecture à partir de ",
  homeSearchNoMatch:
    "Aucun passage pertinent trouvé. Reformulez ou essayez une autre vidéo.",
  homeSearchMalformedResponse: "Réponse serveur inattendue.",
  homeSearchGenericError:
    "La recherche a échoué. Vérifiez l’API puis réessayez.",
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
