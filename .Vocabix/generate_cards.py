#!/usr/bin/env python3
import argparse
import pathlib
import shutil
import subprocess
import sys
import time
from typing import Iterable, List, Optional, Tuple

from generate_outils import generate_outils_cards

try:
    from mlconjug3 import Conjugator
    CONJUGATOR = Conjugator(language='fr')
except ImportError:
    CONJUGATOR = None

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}

# Mapping dossier -> couleur
FOLDER_COLORS = {
    "Noms": "blue",
    "Verbes": "red",
    "Adjectifs": "DarkGreen",
    "Expressions": "black",
}


def conjugate_verb(verb: str) -> Optional[Tuple[str, str]]:
    """
    Retourne un tuple (3ème singulier, 3ème pluriel) d'un verbe
    Retourne None si la conjugaison échoue
    """
    if not CONJUGATOR:
        return None
    
    try:
        conjugated = CONJUGATOR.conjugate(verb)
        
        # Accéder à full_forms ou conjug_info (même contenu)
        # Structure: full_forms['Indicatif']['Présent']['il (elle, on)'] et ['ils (elles)']
        if hasattr(conjugated, 'full_forms'):
            forms = conjugated.full_forms
        elif hasattr(conjugated, 'conjug_info'):
            forms = conjugated.conjug_info
        else:
            return None
        
        try:
            # Accéder aux conjugaisons au présent de l'indicatif
            present_forms = forms['Indicatif']['Présent']
            third_singular = present_forms['il (elle, on)']
            third_plural = present_forms['ils (elles)']
            return (third_singular, third_plural)
        except (KeyError, TypeError):
            # Fallback: essayer avec d'autres noms possibles (variantes)
            return None
    except Exception:
        return None


def get_gender_from_lefff(word: str, lefff_file_path: pathlib.Path) -> Optional[Tuple[Optional[str], Optional[str]]]:
    """
    Retourne un tuple (genre, nombre) d'un nom
    genre: 'm', 'f', ou None (non spécifié)
    nombre: 's' (singulier) ou 'p' (pluriel)
    """
    if not lefff_file_path.exists():
        return None
    
    try:
        with open(lefff_file_path, encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    inflected_form = parts[0]
                    pos = parts[1]
                    misc = parts[3]
                    
                    if inflected_form == word.lower() and pos == 'nc':
                        # Extraire le genre et nombre du champ misc
                        if len(misc) == 2:
                            genre = misc[0]  # 'm' ou 'f'
                            nombre = misc[1]  # 's' ou 'p'
                            return (genre, nombre)
                        elif len(misc) == 1:
                            nombre = misc[0]  # 's' ou 'p'
                            return (None, nombre)  # Genre non spécifié
    except Exception:
        pass
    
    return None


def get_adjective_forms(word: str, lefff_file_path: pathlib.Path) -> Optional[Tuple[str, str]]:
    """
    Retourne un tuple (masculin_singulier, féminin_singulier) d'un adjectif
    """
    if not lefff_file_path.exists():
        return None
    
    try:
        lemmas_found = set()
        forms_by_lemma = {}  # {lemma: {'m': form_masc, 'f': form_fem}}
        
        # Première passe: collecte tous les lemmas et formes pour les adjectifs
        with open(lefff_file_path, encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    inflected_form = parts[0]
                    pos = parts[1]
                    lemma = parts[2]
                    misc = parts[3]
                    
                    if pos != 'adj':
                        continue
                    
                    # Si c'est notre mot (en tant qu'adjectif), noter le lemma
                    if inflected_form == word.lower():
                        lemmas_found.add(lemma)
                    
                    # Initialiser le dict pour ce lemma s'il n'existe pas
                    if lemma not in forms_by_lemma:
                        forms_by_lemma[lemma] = {'m': None, 'f': None}
                    
                    # Extraire le genre et nombre du misc
                    if len(misc) >= 1:
                        # Gérer les formats: ms, fs, mp, fp (2 chars) ou Kms, Kfs, Kmp, Kfp (3 chars avec K pour participes passés)
                        gender = None
                        is_plural = False
                        
                        if len(misc) == 3 and misc[0] == 'K':
                            # Format Kms, Kfs, Kmp, Kfp (participe passé utilisé comme adjectif)
                            gender = misc[1]
                            is_plural = (misc[2] == 'p')
                        elif len(misc) == 2:
                            # Format ms, fs, mp, fp (adjectif standard)
                            gender = misc[0]
                            is_plural = (misc[1] == 'p')
                        elif len(misc) == 1 and misc[0] in ['m', 'f']:
                            # Format m ou f (genre seul)
                            gender = misc[0]
                            is_plural = False
                        
                        # Ajouter la forme si c'est singulier et qu'on a un genre
                        if gender in ['m', 'f'] and not is_plural:
                            if forms_by_lemma[lemma][gender] is None:
                                forms_by_lemma[lemma][gender] = inflected_form
        
        # Deuxième passe: pour chaque lemma trouvé, récupérer les formes
        masc_singular = None
        fem_singular = None
        
        for lemma in lemmas_found:
            if lemma in forms_by_lemma:
                if forms_by_lemma[lemma]['m'] is not None:
                    masc_singular = forms_by_lemma[lemma]['m']
                if forms_by_lemma[lemma]['f'] is not None:
                    fem_singular = forms_by_lemma[lemma]['f']
        
        # Si on n'a toujours pas trouvé les formes, utiliser le mot original
        if masc_singular is None:
            masc_singular = word
        if fem_singular is None:
            fem_singular = word
        
        return (masc_singular, fem_singular)
    except Exception:
        pass
    
    return None


def convert_webp_if_needed(image_path: pathlib.Path, output_dir: pathlib.Path) -> pathlib.Path:
    """
    Convertit un fichier WebP en JPG si nécessaire.
    Retourne le chemin du fichier à utiliser (original ou converti).
    """
    if image_path.suffix.lower() != '.webp':
        return image_path
    
    if not PILLOW_AVAILABLE:
        print(f"[warn] Pillow not available, cannot convert WebP: {image_path}")
        return image_path
    
    # Créer le dossier de conversion s'il n'existe pas
    converted_dir = output_dir / "converted_images"
    converted_dir.mkdir(parents=True, exist_ok=True)
    
    # Nom du fichier JPG converti
    jpg_path = converted_dir / f"{image_path.stem}.jpg"
    
    # Convertir seulement si nécessaire
    if not jpg_path.exists() or jpg_path.stat().st_mtime < image_path.stat().st_mtime:
        try:
            with Image.open(image_path) as img:
                # Convertir en RGB si nécessaire (WebP peut avoir un canal alpha)
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    rgb_img.save(jpg_path, 'JPEG', quality=95)
                else:
                    img.convert('RGB').save(jpg_path, 'JPEG', quality=95)
        except Exception as e:
            print(f"[error] Failed to convert WebP {image_path}: {e}")
            return image_path
    
    return jpg_path


def iter_image_files(folder: pathlib.Path) -> List[pathlib.Path]:
    if not folder.exists():
        return []
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    return sorted(files, key=lambda p: p.name.lower())


def pick_logo(logo_dir: pathlib.Path) -> Optional[pathlib.Path]:
    logos = iter_image_files(logo_dir)
    return logos[0] if logos else None


def latex_escape(text: str) -> str:
    repl = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "^": r"\textasciicircum{}",
        "~": r"\textasciitilde{}",
    }
    return "".join(repl.get(ch, ch) for ch in text)


def parse_noun_filename_markers(word_stem: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Extrait les marqueurs optionnels de fin de nom de fichier pour les noms.

    Suffixes pris en charge (en fin de stem uniquement):
    - _m : force le genre masculin
    - _f : force le genre féminin
    - _p : force le pluriel

    Retourne (mot_nettoye, genre_override, nombre_override)
    """
    parts = word_stem.split("_")
    gender_override: Optional[str] = None
    number_override: Optional[str] = None

    while parts and parts[-1] in {"m", "f", "p"}:
        marker = parts.pop()
        if marker in {"m", "f"} and gender_override is None:
            gender_override = marker
        elif marker == "p" and number_override is None:
            number_override = "p"

    cleaned_word = "_".join(parts) if parts else word_stem
    return cleaned_word, gender_override, number_override


def build_latex(theme_name: str, logo_path: Optional[pathlib.Path], images_with_colors: List[Tuple[pathlib.Path, str, Optional[str], Optional[str], str, Optional[Tuple[str, str]]]], vocabix_dir: pathlib.Path, output_dir: pathlib.Path) -> str:
    page_w = 210
    page_h = 297
    margin = 5
    card_gap = 1
    card_w = 66
    card_h = 93
    top_h = 16
    mid_h = 59
    bot_h = 18
    pad = 2

    lines = []
    lines.append(r"\documentclass[a4paper]{article}")
    lines.append(r"\usepackage[utf8]{inputenc}")
    lines.append(r"\usepackage[T1]{fontenc}")
    lines.append(r"\usepackage{helvet}")
    lines.append(r"\renewcommand{\familydefault}{\sfdefault}")
    lines.append(r"\usepackage{graphicx}")
    lines.append(r"\usepackage[dvipsnames]{xcolor}")
    lines.append(r"\definecolor{DarkGreen}{RGB}{0,100,0}")
    lines.append(r"\usepackage{tikz}")
    lines.append(rf"\usepackage[margin={margin}mm]{{geometry}}")
    lines.append(r"\pagestyle{empty}")
    lines.append(r"\setlength\parindent{0pt}")
    lines.append(r"\setlength\parskip{0pt}")
    lines.append(r"\setlength{\fboxsep}{0pt}")
    lines.append(r"\newcommand{\img}[2][]{\includegraphics[#1]{\detokenize{#2}}}")
    lines.append(r"\begin{document}")

    # Page de garde
    lines.append(r"\vspace*{50mm}")
    lines.append(r"\begin{center}")
    lines.append(r"{\LARGE Cartes de vocabulaire}\\[30mm]")
    lines.append(r"{\Huge\bfseries \MakeUppercase{" + latex_escape(theme_name) + r"}}\\[10mm]")
    if logo_path:
        logo_str = logo_path.resolve().as_posix()  # Chemin absolu pour Windows
        lines.append(r"\vspace{1cm}\img[height=60mm,keepaspectratio]{" + logo_str + r"}\\")
    lines.append(r"\vfill")
    lines.append(r"{\Large Vocabix}")
    lines.append(r"\end{center}")
    lines.append(r"\newpage")

    image_list = list(images_with_colors)
    cards_on_page = 0
    cards_in_row = 0
    current_color = None
    
    for card_idx, (image_path, word_color, gender, number, folder_name, adjective_forms) in enumerate(image_list):
        raw_stem = image_path.stem
        if folder_name == "Noms":
            display_stem, _, _ = parse_noun_filename_markers(raw_stem)
        else:
            display_stem = raw_stem
        vocab = latex_escape(display_stem)
        
        # Préparer le texte du bas selon le type de mot
        if folder_name == "Verbes":
            # Conjuguer le verbe
            conjugations = conjugate_verb(image_path.stem)
            if conjugations:
                third_singular, third_plural = conjugations
                bottom_text_1 = latex_escape(third_singular)
                bottom_text_2 = latex_escape(third_plural)
            else:
                bottom_text_1 = vocab
                bottom_text_2 = vocab
        elif folder_name == "Adjectifs":
            # Afficher les formes d'adjectif au masculin et féminins
            if adjective_forms:
                masc_form, fem_form = adjective_forms
                bottom_text_1 = latex_escape(masc_form)
                bottom_text_2 = latex_escape(fem_form)
            else:
                bottom_text_1 = vocab
                bottom_text_2 = vocab
        else:
            # Pour les autres mots, afficher en bas comme avant
            bottom_text_1 = vocab
            bottom_text_2 = None
        
        # Vérifier si newpage est nécessaire
        newpage_needed = False
        
        # Cas 1: 9 cartes sur la page
        if cards_on_page > 0 and cards_on_page % 9 == 0:
            newpage_needed = True
        
        # Cas 2: changement de couleur avec cartes sur la page
        if current_color is not None and word_color != current_color and cards_on_page > 0:
            # Si on n'a pas 9 cartes, remplir jusqu'à 9 d'abord
            if cards_on_page % 9 != 0:
                remaining = 9 - (cards_on_page % 9)
                for _ in range(remaining):
                    lines.append(
                        rf"\begin{{tikzpicture}}[x=1mm,y=1mm,baseline=0mm]"
                    )
                    lines.append(rf"\draw[white] (0,0) rectangle ({card_w},{card_h});")
                    lines.append(r"\end{tikzpicture}%")
                    cards_in_row += 1
                    if cards_in_row % 3 == 0:
                        lines.append(r"\\")
                        cards_in_row = 0
                    else:
                        lines.append(rf"\hspace{{{card_gap}mm}}%")
            newpage_needed = True
        
        if newpage_needed:
            lines.append(r"\newpage")
            cards_in_row = 0
            cards_on_page = 0
        
        # Commencer une nouvelle ligne si nécessaire
        if cards_in_row == 0:
            lines.append(r"\noindent%")
        
        current_color = word_color

        lines.append(
            rf"\begin{{tikzpicture}}[x=1mm,y=1mm,baseline=0mm]"
        )
        lines.append(rf"\draw[thick] (0,0) rectangle ({card_w},{card_h});")
        lines.append(rf"\draw[dashed] (0,{bot_h}) -- ({card_w},{bot_h});")
        lines.append(rf"\draw[dashed] (0,{bot_h + mid_h}) -- ({card_w},{bot_h + mid_h});")

        if logo_path:
            logo_actual_path = convert_webp_if_needed(logo_path, output_dir)
            logo_str = logo_actual_path.resolve().as_posix()  # Chemin absolu pour Windows
            lines.append(
                r"\node[anchor=north west] at (" +
                rf"{pad},{card_h - pad + 1})" +
                r" {\img[height=" +
                rf"{top_h - 2 * pad}mm,keepaspectratio]" +
                r"{" + logo_str + r"}};"
            )
        
        # Afficher l'image de pluriel si applicable
        if number == 'p':
            plural_file = vocabix_dir / "p.png"
            if plural_file.exists():
                plural_str = plural_file.resolve().as_posix()  # Chemin absolu pour Windows
                # Position à gauche en haut à droite
                lines.append(
                    r"\node[anchor=north west] at (" +
                    rf"{card_w - pad - 24},{card_h - pad})" +
                    r" {\img[height=" +
                    rf"{top_h - 2 * pad}mm,keepaspectratio]" +
                    r"{" + plural_str + r"}};"
                )
        
        # Afficher l'image de genre si applicable
        if gender:
            # Mapper 'm' → 'masculin', 'f' → 'feminin'
            gender_name = "masculin" if gender == 'm' else "feminin"
            gender_file = vocabix_dir / f"{gender_name}.png"
            if gender_file.exists():
                gender_str = gender_file.resolve().as_posix()  # Chemin absolu pour Windows
                # Position à droite (ou seule si pas de p.png)
                lines.append(
                    r"\node[anchor=north west] at (" +
                    rf"{card_w - pad - 8},{card_h - pad + 1})" +
                    r" {\img[height=" +
                    rf"{top_h - 2 * pad}mm,keepaspectratio]" +
                    r"{" + gender_str + r"}};"
                )
        
        # Afficher le verbe en haut à droite si applicable
        if folder_name == "Verbes":
            # Adapter la taille de police pour le verbe en haut selon la longueur
            top_text_length = len(vocab)
            if top_text_length < 12:
                top_font_size = r"\Large"
            elif top_text_length < 20:
                top_font_size = r"\normalsize"
            else:
                top_font_size = r"\scriptsize"
            
            lines.append(
                r"\node[anchor=center, text width=20mm, align=center] at (" +
                rf"{card_w - 30},{card_h - 8})" +
                r" {" + top_font_size + r"\bfseries \textcolor{" + word_color + "}{\MakeUppercase{" + vocab + r"}}};"
            )        
        # Afficher l'image blabla.jpg pour les expressions
        if folder_name == "Expressions":
            blabla_file = vocabix_dir / "blabla.jpg"
            if blabla_file.exists():
                blabla_str = blabla_file.resolve().as_posix()  # Chemin absolu pour Windows
                lines.append(
                    r"\node[anchor=north east] at (" +
                    rf"{card_w - pad},{card_h - pad + 1})" +
                    r" {\img[height=" +
                    rf"{top_h - 2 * pad}mm,keepaspectratio]" +
                    r"{" + blabla_str + r"}};"
                )
        # Convertir WebP en JPG si nécessaire
        actual_image_path = convert_webp_if_needed(image_path, output_dir)
        img_str = actual_image_path.resolve().as_posix()  # Chemin absolu pour Windows
        lines.append(
            r"\node[anchor=center] at (" +
            rf"{card_w / 2},{bot_h + mid_h / 2})" +
            r" {\img[width=" +
            rf"{card_w - 2 * pad}mm,height={mid_h - 2 * pad}mm,keepaspectratio]" +
            r"{" + img_str + r"}};"
        )

        # Afficher le texte du bas selon le type de mot
        if folder_name == "Verbes":
            # Adapter la taille de police pour les conjugaisons selon la longueur
            text1_length = len(bottom_text_1)
            text2_length = len(bottom_text_2)
            
            # Taille pour 3e singulier
            if text1_length < 13:
                font_size_1 = r"\Large"
            elif text1_length < 16:
                font_size_1 = r"\normalsize"
            else:
                font_size_1 = r"\small"
            
            # Taille pour 3e pluriel
            if text2_length < 13:
                font_size_2 = r"\Large"
            elif text2_length < 16:
                font_size_2 = r"\normalsize"
            else:
                font_size_2 = r"\small"
            
            # Ajouter ts.png (3e singulier) et le texte
            ts_file = vocabix_dir / "ts.png"
            if ts_file.exists():
                ts_str = ts_file.resolve().as_posix()  # Chemin absolu pour Windows
                lines.append(
                    r"\node[anchor=east] at (" +
                    rf"{10},{bot_h - 5})" +
                    r" {\img[height=6mm,keepaspectratio]{" + ts_str + r"}};"
                )
            
            # Afficher la conjugaison 3e singulier
            lines.append(
                r"\node[anchor=west] at (" +
                rf"{card_w / 2 - 15},{bot_h - 5})" +
                r" {" + font_size_1 + r"\bfseries \textcolor{" + word_color + "}{\MakeUppercase{" + bottom_text_1 + r"}}};"
            )
            
            # Ajouter tp.png (3e pluriel) et le texte
            tp_file = vocabix_dir / "tp.png"
            if tp_file.exists():
                tp_str = tp_file.resolve().as_posix()  # Chemin absolu pour Windows
                lines.append(
                    r"\node[anchor=east] at (" +
                    rf"{10},{bot_h - 12})" +
                    r" {\img[height=6mm,keepaspectratio]{" + tp_str + r"}};"
                )
            
            # Afficher la conjugaison 3e pluriel
            lines.append(
                r"\node[anchor=west] at (" +
                rf"{card_w / 2 - 15},{bot_h - 12})" +
                r" {" + font_size_2 + r"\bfseries \textcolor{" + word_color + "}{\MakeUppercase{" + bottom_text_2 + r"}}};"
            )
        elif folder_name == "Adjectifs":
            # Adapter la taille de police pour les adjectifs selon la longueur
            text1_length = len(bottom_text_1)
            text2_length = len(bottom_text_2)
            
            # Taille pour forme masculine
            if text1_length < 13:
                font_size_1 = r"\Large"
            elif text1_length < 16:
                font_size_1 = r"\normalsize"
            else:
                font_size_1 = r"\small"
            
            # Taille pour forme féminine
            if text2_length < 13:
                font_size_2 = r"\Large"
            elif text2_length < 16:
                font_size_2 = r"\normalsize"
            else:
                font_size_2 = r"\small"
            
            # Ajouter masculin.png et la forme masculine
            masc_file = vocabix_dir / "masculin.png"
            if masc_file.exists():
                masc_str = masc_file.resolve().as_posix()  # Chemin absolu pour Windows
                lines.append(
                    r"\node[anchor=east] at (" +
                    rf"{10},{bot_h - 5})" +
                    r" {\img[height=6mm,keepaspectratio]{" + masc_str + r"}};"
                )
            
            # Afficher la forme au masculin
            lines.append(
                r"\node[anchor=west] at (" +
                rf"{card_w / 2 - 15},{bot_h - 5})" +
                r" {" + font_size_1 + r"\bfseries \textcolor{" + word_color + "}{\MakeUppercase{" + bottom_text_1 + r"}}};"
            )
            
            # Ajouter féminin.png et la forme féminine
            fem_file = vocabix_dir / "feminin.png"
            if fem_file.exists():
                fem_str = fem_file.resolve().as_posix()  # Chemin absolu pour Windows
                lines.append(
                    r"\node[anchor=east] at (" +
                    rf"{10},{bot_h - 12})" +
                    r" {\img[height=6mm,keepaspectratio]{" + fem_str + r"}};"
                )
            
            # Afficher la forme au féminin
            lines.append(
                r"\node[anchor=west] at (" +
                rf"{card_w / 2 - 15},{bot_h - 12})" +
                r" {" + font_size_2 + r"\bfseries \textcolor{" + word_color + "}{\MakeUppercase{" + bottom_text_2 + r"}}};"
            )
        else:
            # Afficher le mot au centre du bas
            # Adapter la taille de police pour les expressions en fonction de la longueur
            if folder_name == "Expressions":
                text_length = len(bottom_text_1)
                if text_length < 15:
                    font_size = r"\LARGE"
                elif text_length < 20:
                    font_size = r"\Large"
                elif text_length < 25:
                    font_size = r"\normalsize"
                else:
                    font_size = r"\small"
                
                # Si plus de 22 caractères, permettre le retour à la ligne
                if text_length > 22:
                    lines.append(
                        r"\node[anchor=center, text width=" + rf"{card_w - 2 * pad}mm, align=center] at (" +
                        rf"{card_w / 2},{bot_h / 2})" +
                        r" {" + font_size + r"\bfseries \textcolor{" + word_color + r"}{\MakeUppercase{" + bottom_text_1 + r"}}};"
                    )
                else:
                    lines.append(
                        r"\node[anchor=center] at (" +
                        rf"{card_w / 2},{bot_h / 2})" +
                        r" {" + font_size + r"\bfseries \textcolor{" + word_color + r"}{\MakeUppercase{" + bottom_text_1 + r"}}};"
                    )
            else:
                # Pour les noms, adapter la taille de police selon la longueur
                text_length = len(bottom_text_1)
                if text_length < 15:
                    font_size = r"\huge"
                elif text_length < 18:
                    font_size = r"\LARGE"
                else:
                    font_size = r"\large"
                
                lines.append(
                    r"\node[anchor=center] at (" +
                    rf"{card_w / 2},{bot_h / 2})" +
                    r" {" + font_size + r"\bfseries \textcolor{" + word_color + r"}{\MakeUppercase{" + bottom_text_1 + r"}}};"
                )
        
        lines.append(r"\end{tikzpicture}%")
        
        cards_in_row += 1
        cards_on_page += 1
        
        # Ajouter un espace horizontal ou retour à la ligne
        if cards_in_row % 3 == 0:
            lines.append(r"\\")  # Aller à la ligne
            cards_in_row = 0
        else:
            lines.append(rf"\hspace{{{card_gap}mm}}%")
    
    # Remplir la dernière ligne si incomplète
    if cards_in_row > 0:
        for _ in range(3 - cards_in_row):
            lines.append(
                rf"\begin{{tikzpicture}}[x=1mm,y=1mm,baseline=0mm]"
            )
            lines.append(rf"\draw[white] (0,0) rectangle ({card_w},{card_h});")
            lines.append(r"\end{tikzpicture}%")
            if _ < 2:
                lines.append(rf"\hspace{{{card_gap}mm}}%")

    lines.append(r"\end{document}")
    return "\n".join(lines)


def generate_for_theme(theme_dir: pathlib.Path, output_dir: pathlib.Path, engine: str, vocabix_dir: pathlib.Path) -> None:
    theme_name = theme_dir.name
    logo_dir = theme_dir / "logo"
    
    logo = pick_logo(logo_dir)
    if not logo:
        print(f"[warn] No logo found in {logo_dir}")

    # Charger le fichier LEFFF pour extraire les genres
    lefff_path = vocabix_dir / "french_lefff_lemmatizer" / "data" / "lefff-3.4.mlex"

    # Collecter les images avec leurs couleurs, genres et nombres selon le dossier
    images_with_colors: List[Tuple[pathlib.Path, str, Optional[str], Optional[str], str, Optional[Tuple[str, str]]]] = []
    
    for folder_name, color in FOLDER_COLORS.items():
        folder_path = theme_dir / folder_name
        images = iter_image_files(folder_path)
        for image_path in images:
            gender = None
            number = None
            adjective_forms = None
            
            # Si c'est un nom, extraire le genre et nombre de LEFFF
            if folder_name == "Noms":
                clean_word, gender_override, number_override = parse_noun_filename_markers(image_path.stem)

                # Détection LEFFF uniquement pour les dimensions non forcées par suffixes
                detected_gender, detected_number = (None, None)
                needs_gender_detection = gender_override is None
                needs_number_detection = number_override is None
                if needs_gender_detection or needs_number_detection:
                    gender_number = get_gender_from_lefff(clean_word, lefff_path)
                    if gender_number:
                        detected_gender, detected_number = gender_number

                gender = gender_override if gender_override is not None else detected_gender
                number = number_override if number_override is not None else detected_number
                
                # Si genre non spécifié, ajouter deux fiches (féminin et masculin)
                if gender is None:
                    images_with_colors.append((image_path, color, 'f', number, folder_name, None))
                    images_with_colors.append((image_path, color, 'm', number, folder_name, None))
                    continue
            
            # Si c'est un adjectif, extraire les formes masculin et féminin
            elif folder_name == "Adjectifs":
                adj_forms = get_adjective_forms(image_path.stem, lefff_path)
                if adj_forms:
                    adjective_forms = adj_forms
                else:
                    adjective_forms = (image_path.stem, image_path.stem)
            
            images_with_colors.append((image_path, color, gender, number, folder_name, adjective_forms))
    
    # Trier les images par couleur pour que les changements de couleur marquent les newpage
    images_with_colors.sort(key=lambda x: list(FOLDER_COLORS.values()).index(x[1]))
    
    if not images_with_colors:
        print(f"[skip] No images in {theme_dir}")
        return
    
    # Générer dans .output/theme_name
    temp_out = output_dir / theme_name
    temp_out.mkdir(parents=True, exist_ok=True)
    tex_path = temp_out / f"{theme_name}.tex"
    
    # Écrire le fichier .tex avec gestion des erreurs Windows
    try:
        tex_path.write_text(build_latex(theme_name, logo, images_with_colors, vocabix_dir, temp_out), encoding="utf-8")
        print(f"[ok] Wrote {tex_path}")
    except (PermissionError, OSError) as e:
        print(f"[error] Failed to write {tex_path}: {e}")
        return
    
    # Pause pour laisser Windows libérer le verrou sur le fichier
    time.sleep(1)

    cmd = [
        engine,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-output-directory",
        str(temp_out),
        str(tex_path),
    ]
    print("[run]", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    
    # Copier uniquement le PDF dans le dossier du thème
    pdf_path = temp_out / f"{theme_name}.pdf"
    if pdf_path.exists():
        dest_pdf = theme_dir / f"{theme_name}.pdf"
        shutil.copy2(pdf_path, dest_pdf)
        print(f"[ok] PDF copied to {dest_pdf}")
    else:
        print(f"[error] PDF not generated at {pdf_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate vocab cards PDFs per theme folder."
    )
    parser.add_argument(
        "--themes-dir",
        default="../Thèmes",
        help="Base themes directory (default: ../Thèmes)",
    )
    parser.add_argument(
        "--output-dir",
        default="../.output",
        help="Temp directory for LaTeX build files (default: ../.output)",
    )
    parser.add_argument(
        "--engine",
        default="pdflatex",
        help="LaTeX engine (pdflatex, lualatex, xelatex)",
    )
    args = parser.parse_args()

    themes_dir = pathlib.Path(args.themes_dir)
    output_dir = pathlib.Path(args.output_dir)
    vocabix_dir = pathlib.Path(__file__).parent  # Répertoire où se trouve generate_cards.py

    # Génération des cartes mots outils au tout début.
    base_dir = themes_dir.parent
    generate_outils_cards(base_dir, output_dir, args.engine, vocabix_dir)
    
    if not themes_dir.exists():
        print(f"[error] Themes dir not found: {themes_dir}")
        return 1

    # Créer le dossier NOUVEAU avec ses sous-dossiers s'il n'existe pas
    nouveau_dir = themes_dir / "NOUVEAU"
    if not nouveau_dir.exists():
        print(f"[info] Creating NOUVEAU template folder at {nouveau_dir}")
        nouveau_dir.mkdir(parents=True, exist_ok=True)
        
        # Créer les sous-dossiers
        for subfolder in ["Adjectifs", "Expressions", "logo", "Noms", "Verbes"]:
            subfolder_path = nouveau_dir / subfolder
            subfolder_path.mkdir(exist_ok=True)
        
        print(f"[ok] NOUVEAU template folder created with subfolders")

    theme_dirs = [p for p in themes_dir.iterdir() if p.is_dir()]
    if not theme_dirs:
        print(f"[error] No theme folders in {themes_dir}")
        return 1

    for theme_dir in sorted(theme_dirs, key=lambda p: p.name.lower()):
        generate_for_theme(theme_dir, output_dir, args.engine, vocabix_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
