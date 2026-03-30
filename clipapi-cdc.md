**ClipAI**

Cahier des charges --- MVP

Outil de clipping YouTube automatisé par IA

Usage personnel · 2 utilisateurs

Mars 2026

**1. Contexte & objectif**

ClipAI est un outil web personnel permettant de transformer
automatiquement n\'importe quelle vidéo YouTube en clips courts
optimisés pour TikTok et Instagram Reels (format 9:16).

L\'outil est destiné à un usage strictement personnel par 2
utilisateurs. Il n\'est pas conçu pour être commercialisé ou hébergé
publiquement.

+-----------------------------------------------------------------------+
| **Problème résolu**                                                   |
+-----------------------------------------------------------------------+
| → Extraire manuellement des clips d\'une longue vidéo est fastidieux  |
|                                                                       |
| → Ajouter des sous-titres incrustés prend du temps                    |
|                                                                       |
| → Recadrer en 9:16 nécessite un logiciel de montage                   |
|                                                                       |
| → ClipAI automatise l\'intégralité de ce pipeline en quelques minutes |
+-----------------------------------------------------------------------+

**2. Périmètre fonctionnel**

**2.1 Source vidéo**

- YouTube uniquement (URL standard ou shorts)

- Durée maximale recommandée : 3 heures

- Langues supportées : français et anglais

**2.2 Mode automatique (IA)**

L\'utilisateur colle une URL YouTube et lance l\'analyse. Le système :

- Télécharge la vidéo et extrait l\'audio

- Transcrit l\'audio avec timestamps mot par mot

- Envoie la transcription à l\'API Claude pour identifier 5 à 10 moments
  viraux

- Propose les clips avec score, type et justification

- Génère les fichiers MP4 finaux pour les clips sélectionnés

**2.3 Mode manuel**

En complément du mode automatique, l\'utilisateur peut :

- Saisir des timestamps manuellement (format mm:ss)

- Modifier les timestamps des clips détectés par l\'IA

- Supprimer ou ajouter des clips à la sélection

- Prévisualiser chaque clip avant export

**2.4 Traitement vidéo**

- Recadrage automatique en 9:16 (1080×1920px)

- Sous-titres incrustés, toujours actifs, style TikTok (texte centré,
  fond semi-transparent)

- Durée max par clip : 90 secondes

- Format de sortie : MP4 H.264

- Qualité : 1080p si disponible, sinon meilleure qualité disponible

**3. Architecture technique**

**3.1 Vue d\'ensemble**

  ---------------- --------------------- ------------------ -------------------
  **Couche**       **Technologie**       **Rôle**           **Hébergement**

  Frontend         React + Vite          Interface          Vercel (gratuit)
                                         utilisateur        

  Backend          Python + FastAPI      Orchestration du   Render (gratuit)
                                         pipeline           

  Téléchargement   yt-dlp                Download YouTube   Sur le serveur
                                                            backend

  Transcription    faster-whisper        Audio → texte +    Sur le serveur
                   (local)               timestamps         backend

  IA               API Claude            Détection des      Cloud Anthropic
                   (Anthropic)           meilleurs moments  

  Montage          FFmpeg                Découpe +          Sur le serveur
                                         sous-titres + 9:16 backend

  Stockage         Système de fichiers   Clips générés (TTL Sur le serveur
                   temporaire            1h)                backend
  ---------------- --------------------- ------------------ -------------------

**3.2 Pipeline détaillé**

Le flux de traitement suit ces étapes dans l\'ordre :

1.  L\'utilisateur soumet une URL YouTube via l\'interface

2.  Le backend télécharge la vidéo et extrait l\'audio (yt-dlp)

3.  faster-whisper transcrit l\'audio avec timestamps précis par mot

4.  La transcription est envoyée à l\'API Claude pour analyse

5.  Claude retourne un JSON avec les clips, timestamps et scores

6.  L\'utilisateur sélectionne et ajuste les clips sur le frontend

7.  FFmpeg découpe, recadre en 9:16 et incruste les sous-titres

8.  Les clips MP4 sont disponibles au téléchargement

**4. Spécifications frontend**

**4.1 Pages / vues**

- Page unique (SPA) --- pas de routing complexe nécessaire

- Responsive desktop en priorité, mobile acceptable

**4.2 Composants principaux**

**Formulaire de soumission**

- Champ URL YouTube avec validation (regex)

- Bouton « Analyser » --- déclenche le pipeline complet

- Indicateur de progression par étape (téléchargement / transcription /
  analyse IA / rendu)

**Liste des clips détectés**

- Carte par clip : titre, timestamps, durée, score, type (hook / insight
  / story)

- Checkbox de sélection par clip

- Champs modifiables : start et end en secondes

- Bouton « Prévisualiser » --- charge le segment dans le player

- Bouton « Supprimer »

**Ajout manuel de clip**

- Deux champs mm:ss (début / fin)

- Bouton « Ajouter »

**Export**

- Bouton « Générer les clips sélectionnés »

- Barre de progression pendant le rendu FFmpeg

- Liste de téléchargement des fichiers MP4 générés

**5. Spécifications backend**

**5.1 Endpoints API**

  ------------- --------------------- --------------- ---------------------------------
  **Méthode**   **Route**             **Entrée**      **Sortie**

  POST          /analyze              { url: string } { job_id, clips: \[\...\] }

  GET           /status/{job_id}      ---             { step, progress, message }

  POST          /render               { job_id,       { render_id }
                                      clips: \[\...\] 
                                      }               

  GET           /download/{file_id}   ---             Fichier MP4 binaire
  ------------- --------------------- --------------- ---------------------------------

**5.2 Structure d\'un clip (JSON)**

  --------------- ------------- ------------------------------------------
  **Champ**       **Type**      **Description**

  id              string        Identifiant unique du clip

  title           string        Titre court généré par Claude (≤ 8 mots)

  start           float         Timestamp de début en secondes

  end             float         Timestamp de fin en secondes

  type            string        hook \| insight \| story \| highlight

  score           int           Score de viralité estimé (0--100)

  reason          string        Justification en une phrase

  subtitles       array         Liste de { word, start, end } issus de
                                Whisper
  --------------- ------------- ------------------------------------------

**5.3 Traitement FFmpeg**

- Recadrage 9:16 : crop intelligent centré ou blur des bords si format
  original trop éloigné

- Résolution cible : 1080×1920px

- Sous-titres : fichier .ass généré depuis les timestamps Whisper, style
  Arial Bold blanc avec contour noir

- Codec : H.264 (libx264), AAC audio, CRF 23

- Fichiers temporaires supprimés après 1 heure (TTL via tâche cron)

**5.4 Prompt Claude**

Le prompt envoyé à l\'API Claude doit inclure :

- La transcription complète avec timestamps

- La durée totale de la vidéo

- La consigne de retourner uniquement du JSON (pas de markdown)

- Le nombre de clips souhaités (5 à 10)

- La répartition demandée : clips distribués sur l\'ensemble de la
  vidéo, pas seulement le début

**6. Sous-titres**

**6.1 Génération**

- faster-whisper retourne un tableau de segments avec timestamps par mot

- Le backend génère un fichier .ass (Advanced SubStation Alpha) pour
  FFmpeg

- Les mots sont regroupés par blocs de 5 à 8 mots maximum

**6.2 Style**

- Police : Arial Bold, taille 14 (relative à 1080p)

- Couleur texte : blanc (#FFFFFF)

- Contour : noir 2px (style TikTok standard)

- Position : centrée horizontalement, 80% de la hauteur verticale

- Fond : semi-transparent noir (alpha 40%)

**7. Coûts estimés**

  --------------------- ------------------ -------------------------------
  **Composant**         **Coût**           **Notes**

  Hébergement backend   0 €/mois           Free tier --- cold start
  (Render)                                 possible

  Hébergement frontend  0 €/mois           Free tier illimité
  (Vercel)                                 

  faster-whisper        0 €                Open source, tourne sur le
                                           serveur

  API Claude            \~0,01 € / vidéo   Sonnet 4 --- très économique

  yt-dlp                0 €                Open source

  FFmpeg                0 €                Open source

  TOTAL pour 100 vidéos \~1 €              Uniquement coût API Claude
  --------------------- ------------------ -------------------------------

+-----------------------------------------------------------------------+
| **Limite du free tier Render**                                        |
+-----------------------------------------------------------------------+
| → Le plan gratuit de Render a 512 MB de RAM --- faster-whisper        |
| (modèle small) en consomme \~300 MB                                   |
|                                                                       |
| → Si la RAM est insuffisante, utiliser le modèle tiny (moins précis)  |
| ou passer au plan Starter à 7 \$/mois                                 |
|                                                                       |
| → Alternative : héberger le backend en local sur ton propre           |
| ordinateur avec ngrok pour l\'exposer                                 |
+-----------------------------------------------------------------------+

**8. Contraintes & limitations**

**8.1 Légales**

- L\'outil utilise yt-dlp pour télécharger des vidéos YouTube, ce qui
  est contraire aux CGU de YouTube

- Étant donné l\'usage strictement personnel et non commercial, le
  risque est négligeable

- Ne pas rendre l\'outil public ou accessible à des tiers non autorisés

**8.2 Techniques**

- Le free tier Render impose un cold start de \~30 secondes après
  inactivité

- Les fichiers vidéo volumineux (\>2 Go) peuvent dépasser les limites de
  stockage temporaire

- faster-whisper modèle « small » recommandé pour équilibrer précision
  et RAM

- Le recadrage 9:16 automatique sera imparfait pour les vidéos avec
  plusieurs locuteurs éloignés

**8.3 Sécurité**

- Pas d\'authentification nécessaire (usage local/personnel)

- Optionnel : protéger l\'accès avec un token statique dans les headers

- Ne jamais exposer la clé API Claude côté frontend

**9. Stack recommandée pour Claude Code**

**9.1 Backend**

- Python 3.11+

- FastAPI --- framework API moderne, async natif

- faster-whisper --- transcription locale (modèle : small)

- yt-dlp --- téléchargement YouTube

- FFmpeg (via subprocess ou ffmpeg-python) --- montage vidéo

- python-dotenv --- gestion des variables d\'environnement

- httpx --- appels HTTP vers l\'API Claude

**9.2 Frontend**

- React 18 + Vite

- Tailwind CSS --- styling rapide

- Axios ou fetch natif --- appels API

- Pas de state manager complexe nécessaire (useState suffit)

**9.3 Variables d\'environnement requises**

  ------------------------ ----------------------------------------------
  **Variable**             **Description**

  ANTHROPIC_API_KEY        Clé API Claude --- ne jamais committer en
                           clair

  WHISPER_MODEL            Modèle Whisper : tiny \| small \| medium
                           (défaut : small)

  MAX_VIDEO_DURATION       Durée max en secondes (défaut : 10800 = 3h)

  CLIP_TTL_SECONDS         Durée de vie des fichiers générés (défaut :
                           3600)

  CORS_ORIGIN              URL du frontend autorisé (ex:
                           https://clipai.vercel.app)
  ------------------------ ----------------------------------------------

**10. Ordre de développement recommandé**

Séquence optimale pour Claude Code avec Opus :

9.  **Backend --- setup FastAPI + endpoint /health**

    - Structure de projet, requirements.txt, .env

10. **Intégration yt-dlp --- téléchargement et extraction audio**

    - Tester avec une vidéo courte de 2 minutes

11. **Intégration faster-whisper --- transcription avec timestamps**

    - Valider la qualité sur FR et EN

12. **Appel API Claude --- analyse et retour JSON**

    - Prompt engineering --- itérer jusqu\'à un JSON propre et fiable

13. **Pipeline FFmpeg --- découpe + 9:16 + sous-titres**

    - Étape la plus complexe --- tester les cas limites (format
      portrait, landscape)

14. **Frontend React --- UI complète connectée au backend**

    - Commencer par un formulaire simple, enrichir ensuite

15. **Déploiement --- Render (backend) + Vercel (frontend)**

    - Configurer les variables d\'environnement en production

**11. Prompt d\'amorçage pour Claude Code**

Copie-colle ce prompt au démarrage de ta session Claude Code avec Opus :

+-----------------------------------------------------------------------+
| Tu vas m\'aider à construire ClipAI, un outil de clipping YouTube.    |
|                                                                       |
| Stack : Python + FastAPI (backend) · React + Vite (frontend)          |
|                                                                       |
| Le backend tourne sur Render, le frontend sur Vercel.                 |
|                                                                       |
| Pipeline : yt-dlp → faster-whisper (local, modèle small) → API Claude |
| → FFmpeg                                                              |
|                                                                       |
| Output : clips MP4 9:16 avec sous-titres incrustés style TikTok.      |
|                                                                       |
| Commence par le backend. Crée la structure de projet complète,        |
|                                                                       |
| le requirements.txt, le .env.example, et l\'endpoint /health.         |
+-----------------------------------------------------------------------+
