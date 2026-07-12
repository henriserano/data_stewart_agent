# Guide utilisateur — Data Steward Agent

Ce guide vous accompagne pas à pas pour connecter l'agent Data Steward à votre compte **Claude** (recommandé) ou **ChatGPT**. Aucune connaissance technique nécessaire.

Comptez **10 minutes** la première fois.

---

## 1. Ce que fait cet agent, en clair

C'est un assistant qui vous aide à travailler avec le catalogue de données de votre entreprise (OpenMetadata). Vous discutez avec lui en langage naturel, et il peut, à votre demande :

- Trouver et décrire des tables, dashboards, pipelines
- Vous expliquer d'où vient une donnée
- Identifier les données mal documentées ou sans propriétaire
- Suggérer des règles de qualité
- Comparer plusieurs sources et proposer laquelle prendre comme "source de vérité"

Techniquement, il utilise deux briques :

- Un **MCP** (Model Context Protocol) — un connecteur qui donne à Claude/ChatGPT l'accès aux 42 outils qui interrogent le catalogue.
- Des **Skills** — des procédures écrites qui guident l'agent sur "quel outil utiliser quand".

Vous ne verrez jamais ces briques : elles fonctionnent en arrière-plan une fois branchées.

---

## 2. Ce qu'il vous faut avant de commencer

Récupérez ces trois éléments auprès de la personne qui a installé le serveur (probablement Henri chez Sia). Sans eux, l'agent ne peut pas se connecter.

| Élément                         | À quoi ça ressemble                                                        | Où le trouver                                                          |
| --------------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| **URL du serveur**          |  `https://nnkpfzmbbmzezoch5qg7mohlqe0haohf.lambda-url.eu-west-3.on.aws/mc` | Fournie par l'admin                                                     |
| **Jeton d'accès (bearer)** | Une longue chaîne de caractères aléatoires                                | Fournie par l'admin (à conserver en sécurité, comme un mot de passe) |
| **Dossier `skills/`**     | Un dossier contenant 11 fichiers`SKILL.md`                                 | Dans ce repo Git, dossier`skills/`                                    |

> **Sécurité** — Ne partagez jamais votre jeton par mail non chiffré ou sur des messageries publiques. Traitez-le comme un mot de passe.

---

## 3. Connecter à Claude Desktop (recommandé)

Claude Desktop est l'application Claude installée sur votre ordinateur. C'est la voie la plus simple.

### Étape 3.1 — Vérifier que Claude Desktop est installé

Sur Mac : cherchez "Claude" dans Spotlight (Cmd + Espace, tapez "Claude"). Sur Windows : dans le menu Démarrer.

Si pas installé, téléchargez-le sur https://claude.ai/download.

### Étape 3.2 — Ouvrir le fichier de configuration

Le fichier de config s'appelle `claude_desktop_config.json`. Il se trouve à un endroit précis selon votre système.

**Sur Mac :**

1. Ouvrez le Finder
2. Menu **Aller → Aller au dossier…** (raccourci Cmd + Maj + G)
3. Collez ce chemin et appuyez sur Entrée :
   ```
   ~/Library/Application Support/Claude/
   ```
4. Si vous voyez un fichier `claude_desktop_config.json`, ouvrez-le avec TextEdit (clic droit → Ouvrir avec → TextEdit).
5. Si le fichier n'existe pas, créez-le : clic droit dans le dossier → **Nouveau document**, nommez-le exactement `claude_desktop_config.json`.

**Sur Windows :**

1. Ouvrez l'explorateur de fichiers
2. Dans la barre d'adresse, tapez :
   ```
   %APPDATA%\Claude\
   ```
3. Puis Entrée. Ouvrez `claude_desktop_config.json` avec le Bloc-notes (créez-le s'il n'existe pas).

### Étape 3.3 — Coller la configuration

Remplacez tout le contenu du fichier par ceci :

```json
{
  "mcpServers": {
    "data-steward": {
      "url": "https://rtg5ndsskm.eu-west-1.awsapprunner.com/mcp",
      "headers": {
        "Authorization": "Bearer aa6ac21d3e5524991959d424e4771c9de2a3b90a3d3c5b9c15364affec047dc5" 
      }
    }
  }
}
(mettre 4 à la place de 5 à la fin )
```

**Deux choses à modifier** :

1. Remplacez `https://rtg5ndsskm.eu-west-1.awsapprunner.com/mcp` par l'URL que vous a donnée l'admin (attention à bien laisser le `/mcp` à la fin)
2. Remplacez `VOTRE-JETON-ICI` par votre jeton (gardez le mot `Bearer` et l'espace avant)

**Sauvegardez** le fichier (Cmd + S sur Mac, Ctrl + S sur Windows).

### Étape 3.4 — Redémarrer Claude Desktop **complètement**

Attention, fermer la fenêtre ne suffit pas. Il faut **quitter l'application**.

**Sur Mac** : Menu Claude en haut à gauche → **Quitter Claude** (ou Cmd + Q). Puis relancez Claude depuis le Dock ou Spotlight.

**Sur Windows** : Clic droit sur l'icône Claude dans la barre des tâches → **Quitter**. Puis relancez.

### Étape 3.5 — Vérifier que ça marche

1. Ouvrez Claude Desktop, démarrez une nouvelle conversation
2. En bas de la zone de saisie, vous devez voir une icône **🔧 outils** avec un chiffre à côté (42 outils)
3. Cliquez dessus — vous devez voir la liste des outils "data-steward"

Si c'est le cas : **c'est bon, l'agent est branché.**

### Étape 3.6 — Ajouter les Skills

Les skills donnent à Claude des "modes opératoires" pour bien utiliser les outils. Vous les ajoutez à votre projet Claude.

1. Dans Claude Desktop, allez dans **Projects** (menu de gauche)
2. Créez un nouveau projet nommé "Data Stewardship" (ou reprenez un existant)
3. Dans le projet, cherchez la section **Skills** ou **Instructions personnalisées**
4. Ajoutez les skills une par une : ouvrez chaque fichier `SKILL.md` dans le dossier `skills/` du repo, copiez son contenu, collez-le comme instruction ou skill du projet

Ou plus rapide : glissez-déposez tout le dossier `skills/` dans le projet Claude, il détectera les fichiers automatiquement (fonctionnalité disponible dans Claude Code et progressivement dans Claude Desktop).

### Étape 3.7 — Tester avec un vrai cas

Dans votre projet, tapez ceci :

> "Utilise la skill `review-undocumented-backlog` pour me montrer les tables sans description dans le catalogue, limite à 10 résultats."

Claude va :

1. Appliquer la procédure de la skill (repérer les tables non documentées, les prioriser)
2. Appeler l'outil `list_undocumented_assets` en coulisse
3. Vous présenter le résultat en langage naturel

Bravo, vous utilisez votre agent 🎉

---

## 4. Connecter à Claude for Work (déploiement équipe)

Si votre entreprise utilise **Claude for Work**, vous pouvez publier l'agent pour toute votre équipe en un clic.

**Réservé aux administrateurs de l'espace de travail.**

1. Allez sur https://claude.ai en admin
2. **Settings → Integrations → Add MCP Server**
3. Renseignez :
   - Nom : `Data Steward`
   - URL : celle donnée par l'admin technique
   - Header d'authentification : `Authorization: Bearer VOTRE-JETON`
4. Onglet **Availability** → **Publish to workspace**

Vos collègues voient l'agent apparaître dans leur Claude sans aucune manipulation de leur côté.

Pour les skills : dans le même admin console, **Settings → Skills → Upload SKILL.md files** pour chaque skill à publier.

---

## 5. Connecter à ChatGPT

ChatGPT supporte MCP depuis mi-2025, sur les plans **ChatGPT Plus, Pro, Team, Business et Enterprise**. Le plan gratuit ne suffit pas.

### Étape 5.1 — Vérifier votre plan

Cliquez sur votre avatar en haut à droite → **Manage subscription**. Vous devez avoir un plan payant.

### Étape 5.2 — Ajouter le connecteur MCP

1. Dans ChatGPT, cliquez sur votre avatar → **Settings**
2. Onglet **Connectors** (ou **Beta features → Model Context Protocol** selon votre version)
3. Cliquez sur **Add MCP Server** (ou **+ Connect a service**)
4. Renseignez les champs :

| Champ                   | Valeur                                                   |
| ----------------------- | -------------------------------------------------------- |
| **Name**          | `Data Steward`                                         |
| **Description**   | `Assistant OpenMetadata — 42 outils pour Data Owners` |
| **URL**           | l'URL fournie par l'admin (finit par`/mcp`)            |
| **Authorization** | `Bearer VOTRE-JETON`                                   |

5. Cliquez **Save** ou **Connect**.

### Étape 5.3 — Activer dans une conversation

1. Nouvelle conversation ChatGPT
2. Cliquez sur l'icône **+** ou **outils** à côté de la zone de saisie
3. Cochez **Data Steward** pour l'activer dans cette conversation

### Étape 5.4 — Tester

Tapez la même question qu'avec Claude :

> "Liste-moi les 5 premières tables du catalogue OpenMetadata."

Vous devriez voir un indicateur "🔧 utilise Data Steward" pendant la réponse, et un résultat basé sur les vraies tables du catalogue.

### Skills sur ChatGPT

ChatGPT n'a pas d'équivalent aux "Skills" de Claude nativement. **Contournement** : copiez le contenu du fichier `SKILL.md` que vous voulez utiliser directement dans le prompt de la conversation, ou stockez-le dans les **Custom Instructions** de votre profil ChatGPT.

Exemple : ouvrez `skills/document-asset/SKILL.md`, copiez tout le texte, collez-le en début de conversation avant votre question.

---

## 6. Problèmes fréquents

### "L'outil ne répond pas / je ne vois pas l'icône outils"

- Avez-vous bien redémarré l'application (pas seulement fermé la fenêtre) ?
- L'URL dans la config finit-elle bien par `/mcp` ?
- Le jeton (Bearer) est-il bien celui fourni, sans espace en début/fin ?

### "Le fichier claude_desktop_config.json est vide ou n'existe pas"

C'est normal si vous n'avez jamais configuré de MCP avant. Créez-le à la main avec le contenu de l'étape 3.3.

### "Claude / ChatGPT dit qu'il ne trouve aucun asset"

Le catalogue OpenMetadata connecté est peut-être vide ou pointe vers un environnement de test sans données. Demandez à l'admin de vérifier :

- Sur quel OpenMetadata l'agent est branché (sandbox public, EC2 prod, autre ?)
- Si le catalogue contient bien des tables/dashboards indexés

### "J'ai perdu / oublié mon jeton"

Le jeton n'est pas récupérable dans l'app. Demandez à l'admin technique de vous en générer un nouveau (procédure interne à l'entreprise).

### "L'agent est très lent (plusieurs secondes par réponse)"

Normal la première fois de la journée (~2 s de "démarrage à froid"), puis c'est rapide (~200 ms par appel). Si c'est lent en continu, le catalogue OpenMetadata en amont est peut-être lent. Contactez l'admin.

---

## 7. Choses utiles à demander à l'agent une fois branché

Voici des exemples de questions qui exercent bien les 42 outils :

1. **Documentation** — "Sur les tables owned par l'équipe Marketing, montre-moi celles qui n'ont pas de description, triées par usage."
2. **Traçabilité** — "D'où vient la colonne `orders.orderid` de la table `dim_orders` ?"
3. **Golden source** — "J'ai plusieurs tables `customer` dans le catalogue. Laquelle est la meilleure source de référence ?"
4. **Qualité** — "Propose-moi des règles de qualité pour la table `fact_sales`."
5. **Gouvernance** — "Liste les tables sans propriétaire dans le domaine 'Retail'."
6. **Impact** — "Si je supprime la colonne `legacy_customer_id` de `prod.crm.customer`, qui est-ce que je casse ?"

Pour aller plus loin, chaque skill du dossier `skills/` décrit un cas d'usage complet — lisez-les, c'est écrit en langage clair.

---

## 8. Contacts

- **Question technique / bug** : contactez l'admin du serveur (Henri chez Sia)
- **Question métier / bonne pratique** : lisez les skills, ou demandez directement à l'agent "explique-moi cette skill" en collant son contenu
- **Rotation du jeton d'accès** : à faire par l'admin technique tous les 3 mois environ, ou immédiatement si vous suspectez une fuite

Bonne exploration !
