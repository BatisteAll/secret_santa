# 🎄 Secret Santa familial : mode d'emploi

Le script tire au sort qui offre à qui, génère une page web par adulte (avec une roue qui tourne, mais le résultat est déjà décidé) et ouvre un petit tableau de bord pour copier les liens à envoyer.

## Règles du tirage

- Les **adultes** donnent ET reçoivent. Les **enfants** reçoivent seulement.
- Chaque adulte donneur reçoit si possible 1 adulte + 1 enfant à qui offrir.
- S'il n'y a pas assez de monde : 2 adultes, sinon 2 enfants. Au pire, le script signale qui n'a pioché que 1 ou 0 receveur.
- S'il reste des receveurs en trop, ils sont répartis au hasard. Le script signale si certains donneurs en ont plus que les autres.
- Personne ne se tire soi-même et personne n'a le même receveur deux fois.
- Les affinités (`A_EVITER`) sont un « de préférence pas », ignoré seulement si c'est impossible autrement.

## Chaque année : étapes

### 1. Mettre à jour le script

Ouvre `generateur_santa.v2.py` et modifie le début du fichier :

| Paramètre | À quoi ça sert |
|---|---|
| `CADEAUX_PAR_RECEVEUR` | Nombre de cadeaux que chaque personne reçoit (ex. `2`). |
| `URL_GITHUB` | Adresse de ton GitHub Pages, **sans `/` à la fin**. Ex. `https://monpseudo.github.io/monrepo` |
| `ADULTES` | Les donneurs (ils reçoivent aussi). Un nom, une photo, une couleur. |
| `ENFANTS` | Ceux qui reçoivent seulement. |
| `A_EVITER` | Affinités : `"Chloé": ["Léo", "Mia"]` = Chloé ne tire pas Léo ni Mia, sauf impossibilité. |

À savoir :
- Les noms doivent être **uniques**.
- Pour un couple, écris un seul nom : `"nom": "Alice & Bob"` (les noms longs passent à la ligne dans la roue).
- Les noms dans `A_EVITER` doivent être écrits exactement comme dans les listes, sinon le script s'arrête avec un message.
- Chaque photo (`alice.jpg`, etc.) doit être dans le même dossier que le script.
- Si le script dit « trop de cadeaux par rapport au nombre de participants », baisse `CADEAUX_PAR_RECEVEUR`.

### 2. Lancer le script

Dans le Terminal, va dans le dossier du script puis :

```bash
python3 generateur_santa.v2.py
```

Résultat :
- un fichier `tirage_<prénom>.html` par adulte est créé à côté du script ;
- une page s'ouvre dans le navigateur avec un bouton « Copier le lien » par adulte, les alertes éventuelles, et une section **Debug** repliée (qui donne à qui) ;
- les liens sont aussi affichés dans le Terminal.

⚠️ **Ne relance pas le script après avoir envoyé les liens** : chaque lancement refait un nouveau tirage, et les anciens liens ne correspondraient plus.

### 3. Mettre les fichiers sur GitHub

Dépose dans le dépôt GitHub Pages **les fichiers `tirage_*.html` ET les photos** (même dossier, à la racine du dépôt).

**Par le site web** (le plus simple) :
1. Va sur ton dépôt GitHub → **Add file** → **Upload files**.
2. Glisse-dépose les `tirage_*.html` et les photos.
3. Clique sur **Commit changes**.

**Ou en ligne de commande**, depuis le dossier du dépôt :

```bash
git add .
git commit -m "Secret Santa"
git push
```

Si GitHub Pages n'est pas encore activé : dépôt → **Settings** → **Pages** → choisis la branche `main` et le dossier `/ (root)`.

Attends une à deux minutes, puis ouvre un des liens pour vérifier que la roue s'affiche (rafraîchis sans cache avec Cmd+Shift+R).

### 4. Envoyer les liens

Dans la page du tableau de bord, clique sur le bouton d'un adulte (le lien est copié), puis colle-le dans WhatsApp (Cmd+V) pour cette personne. Recommence pour chaque adulte.

## Bon à savoir

- **Debug** : la section « Debug » du tableau de bord montre qui donne à qui, avec ⚠️ pour les affinités non respectées. Ne l'ouvre pas si tu participes et veux garder la surprise. La page est enregistrée dans le dossier temporaire du Mac, jamais à côté des `.html`, donc elle ne part pas sur GitHub.
- **Les résultats sont lisibles** : les receveurs sont écrits dans le code de chaque page. Quelqu'un qui fait « afficher le code source » peut les voir.
- **Ancien tirage** : avant de déposer de nouveaux fichiers, supprime ceux de l'an dernier sur GitHub. Si le nom du fichier contient un code (`tirage_alice_4f2a9c1e.html`), les nouveaux ne remplacent pas les anciens. Sans code (`tirage_alice.html`), ils les écrasent. Dans les deux cas, rafraîchis sans cache avant de tester.
- **Plus de Tkinter** : le tableau de bord est une page web, plus une fenêtre. Seul Python 3 est nécessaire, sans installation de paquet.
