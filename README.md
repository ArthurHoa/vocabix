# Vocabix

Vocabix permet de générer automatiquement des fiches et des cartes PDF à partir de dossiers d'images.
L'objectif est simple : vous déposez vos images au bon endroit, puis vous lancez `Vocabix` en double-cliquant.

## 0) Installer LaTeX

**Vocabix** a besoin de LaTeX pour générer ses cartes, le plus simple est d'installer [MikTEX](https://miktex.org/download) (C'est très simple).

## 1) Télécharger Vocabix

Télécharger Vocabix pour [Linux](https://github.com/ArthurHoa/vocabix/archive/refs/heads/linux.zip), [Windows](https://github.com/ArthurHoa/vocabix/archive/refs/heads/windows.zip) ou [Mac].

Attention, la première fois que vous lancerez **Vocabix**, des installations LaTex seront requises, il faudra accepter ces installations.
Le premier lancement peut être un peu plus long, le temps d'installer les dépendances.

## 2) Fonctionnement global (très simple)

1. Double-cliquez sur l'exécutable **Vocabix**.
2. Vocabix lit les images dans les dossiers.
3. Vocabix génère les PDF automatiquement.
4. Si le dossier `Thèmes/NOUVEAU` n'existe pas, il est créé.

Ensuite, vous pouvez ajouter vos images dans les dossiers ci-dessous, puis refaire un double-clic sur **Vocabix** pour régénérer les PDF.

## 3) Un Exemple de projet 

```text
Vocabix/
├── Élèves/
│   ├── images/
│   │   ├── Prénom 1.jpg
│   │   ├── Prénom 2.jpg
│   │   ├── Prénom 3.jpg
│   │   ├── Prénom 4.jpg
|   |   ├── Prénom 5.jpg
│   │   └── Prénom 6.jpg
│   └── Élèves.pdf
├── Outils/
│   ├── gris/
│   ├── jaune/
│   ├── marron/
│   │   ├── la_f.webp
│   │   ├── le_m.jpg
│   │   └── les_p.jpg
│   ├── orange/
│   ├── violet/
│   │   ├── elle_f.jpg
│   │   ├── il_m.jpeg
│   │   ├── je.jpg
│   │   └── tu.jpg
│   └── Outils.pdf
└── Thèmes/
    ├── Sports/
    │   ├── Adjectifs/
    │   │   ├── agile.png
    │   │   ├── concentré.jpg
    │   │   ├── courageux.png
    │   │   ├── rapide.jpg
    │   ├── Expressions/
    │   │   ├── Allonger sa foulée.jpg
    │   │   ├── être en nage.jpg
    │   │   ├── être rapide comme l'éclair.jpg
    │   │   ├── jouer fair-play.webp
    │   │   └── nager comme un dauphin.jpg
    │   ├── Noms/
    │   │   ├── arbitre_f.jpg
    │   │   ├── arbitre_m.jpg
    │   │   ├── ballon.jpg
    │   │   ├── sportif_m.jpg
    │   │   ├── sportive_f.webp
    |   |   ├── victoire.webp
    │   │   └── échauffements.jpeg
    │   ├── Verbes/
    │   │   ├── courir.jpg
    │   │   ├── dribbler.jpg
    │   │   ├── lancer.jpg
    │   │   ├── ramper.jpg
    │   │   ├── sauter.jpg
    │   │   └── surfer.jpg
    │   ├── logo/
    │   │   └── logo.jpeg
    │   └── Sports.pdf
    ├── Aliments/
    │   ├── Adjectifs/
    │   │   ├── acide.png
    │   │   ├── crémeux.jpg
    │   │   ├── dur.png
    │   │   ├── mou.webp
    │   │   ├── salé.jpg
    │   │   └── sucré.jpg
    │   ├── Expressions/
    │   │   ├── Avoir les yeux plus gros que le ventre.jpg
    │   │   ├── Avoir une faim de loup.jpeg
    │   │   ├── Être rassasié.jpg
    │   │   └── Mettre du beurre dans les épinards.jpg
    │   ├── Noms/
    │   │   ├── beurre.jpg
    │   │   ├── chocolat.jpg
    │   │   ├── cookies_m_p.jpg
    │   │   ├── dîner.jpg
    │   │   ├── framboises_f_p.webp
    │   │   ├── petit-déjeuner_m.webp
    │   │   ├── soupe.webp
    │   │   └── souper.jpeg
    │   ├── Verbes/
    │   │   ├── avaler.jpg
    │   │   ├── croquer.jpg
    │   │   ├── cuisiner.jpg
    │   │   ├── éplucher.jpg
    │   │   ├── mâcher.jpg
    │   │   └── tartiner.jpg
    │   ├── logo/
    │   │   └── logo.jpeg
    │   └── Aliments.pdf
    └── NOUVEAU/
        ├── Adjectifs/
        ├── Expressions/
        ├── Noms/
        ├── Verbes/
        └── logo/
```

Comme vous le voyez, il y a 3 dossiers : `Élèves`, `Outils` et `Thèmes`.
En double cliquant sur Vocabix, trois fichiers `.pdf` sont générés. Dans `Élèves`, le fichier `Élèves.pdf` suivant est généré :

<p>
  <img src="images/%C3%89l%C3%A8ves.jpg" alt="Eleves" width="30%" />
</p>

Dans `Outils`, le fichier `Outils.pdf` suivant est généré :

<p>
  <img src="images/Outils_1.jpg" alt="Outils 1" width="30%" />
  <img src="images/Outils_2.jpg" alt="Outils 2" width="30%" />
</p>

Dans `Thèmes/Sports`, le fichier `Sports.pdf` suivant est généré :

<p>
  <img src="images/Sports1.jpg" alt="Sports 1" width="30%" />
  <img src="images/Sports2.jpg" alt="Sports 2" width="30%" />
  <img src="images/Sports3.jpg" alt="Sports 3" width="30%" />
  <img src="images/Sports4.jpg" alt="Sports 4" width="30%" />
  <img src="images/Sports5.jpg" alt="Sports 4" width="30%" />
</p>

Enfin, dans `Thèmes/Aliments`, le fichier `Aliments.pdf` suivant est généré :

<p>
  <img src="images/Aliments1.jpg" alt="Aliments 1" width="30%" />
  <img src="images/Aliments2.jpg" alt="Aliments 2" width="30%" />
  <img src="images/Aliments3.jpg" alt="Aliments 3" width="30%" />
  <img src="images/Aliments4.jpg" alt="Aliments 4" width="30%" />
  <img src="images/Aliments5.jpg" alt="Aliments 5" width="30%" />
</p>

## 4) Détail par dossier

### Élèves
- Déposez vos images dans `Élèves/images`.
- Au double-clic sur **Vocabix**, le PDF est généré : `Élèves/Élèves.pdf`.

En clair : vous mettez les images dans `images`, vous relancez **Vocabix**, et vous récupérez directement le PDF des élèves.

### Outils
- Déposez vos images de mots outils dans les sous-dossiers couleur :
  - `Outils/gris`
  - `Outils/jaune`
  - `Outils/marron`
  - `Outils/orange`
  - `Outils/violet`
- Au double-clic sur **Vocabix**, les cartes sont générées et regroupées dans : `Outils/Outils.pdf`.

### Thèmes > Marche Nordique
Dans `Thèmes/Marche Nordique`, vous avez :
- `Adjectifs`
- `Expressions`
- `Noms`
- `Verbes`
- `logo`

Quand vous remplissez ces dossiers avec vos images puis que vous double-cliquez sur **Vocabix**, le PDF est généré ici :
- `Thèmes/Marche Nordique/Marche Nordique.pdf`

## 5) Dossier NOUVEAU

Le dossier `Thèmes/NOUVEAU` sert de modèle pour créer un nouveau thème avec la bonne structure :
- `Adjectifs`
- `Expressions`
- `Noms`
- `Verbes`
- `logo`

Il est prêt à être rempli avec vos images.

## 6) Résumé en une phrase

- Je range mes images dans les bons dossiers.
- Je double-clique sur **Vocabix**.
- Je récupère mes PDF générés automatiquement.
