#!/usr/bin/env python3
import pathlib
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image

    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}

# Ordre de rendu et couleurs LaTeX associees.
OUTILS_COLOR_ORDER = ["gris", "violet", "marron", "jaune", "orange"]
OUTILS_COLOR_LATEX: Dict[str, str] = {
    "gris": "OutilsGris",
    "violet": "OutilsViolet",
    "marron": "OutilsMarron",
    "jaune": "OutilsJaune",
    "orange": "OutilsOrange",
}


def convert_webp_if_needed(image_path: pathlib.Path, output_dir: pathlib.Path) -> pathlib.Path:
    """
    Convertit un fichier WebP en JPG si necessaire.
    Retourne le chemin du fichier a utiliser (original ou converti).
    """
    if image_path.suffix.lower() != ".webp":
        return image_path

    if not PILLOW_AVAILABLE:
        print(f"[warn] Pillow not available, cannot convert WebP: {image_path}")
        return image_path

    converted_dir = output_dir / "converted_images"
    converted_dir.mkdir(parents=True, exist_ok=True)
    jpg_path = converted_dir / f"{image_path.stem}.jpg"

    if not jpg_path.exists() or jpg_path.stat().st_mtime < image_path.stat().st_mtime:
        try:
            with Image.open(image_path) as img:
                if img.mode in ("RGBA", "LA", "P"):
                    rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                    rgb_img.save(jpg_path, "JPEG", quality=95)
                else:
                    img.convert("RGB").save(jpg_path, "JPEG", quality=95)
        except Exception as e:
            print(f"[error] Failed to convert WebP {image_path}: {e}")
            return image_path

    return jpg_path


def iter_image_files(folder: pathlib.Path) -> List[pathlib.Path]:
    if not folder.exists():
        return []
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    return sorted(files, key=lambda p: p.name.lower())


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
    Extrait les marqueurs de fin pour les mots outils.

    Suffixes pris en charge (en fin de stem uniquement):
    - _m : genre masculin
    - _f : genre feminin
    - _p : pluriel

    Retourne (mot_nettoye, genre, nombre)
    """
    parts = word_stem.split("_")
    gender: Optional[str] = None
    number: Optional[str] = None

    while parts and parts[-1] in {"m", "f", "p"}:
        marker = parts.pop()
        if marker in {"m", "f"} and gender is None:
            gender = marker
        elif marker == "p" and number is None:
            number = "p"

    cleaned_word = "_".join(parts) if parts else word_stem
    return cleaned_word, gender, number


def ensure_outils_structure(outils_dir: pathlib.Path) -> None:
    """Cree le dossier Outils et ses sous-dossiers couleur si necessaire."""
    if not outils_dir.exists():
        print(f"[info] Creating Outils folder at {outils_dir}")
        outils_dir.mkdir(parents=True, exist_ok=True)

    for color_name in OUTILS_COLOR_ORDER:
        color_dir = outils_dir / color_name
        if not color_dir.exists():
            color_dir.mkdir(parents=True, exist_ok=True)
            print(f"[ok] Created color folder: {color_dir}")


def build_latex(
    images_with_meta: List[Tuple[pathlib.Path, str, Optional[str], Optional[str]]],
    vocabix_dir: pathlib.Path,
    output_dir: pathlib.Path,
) -> str:
    margin = 5
    card_gap = 1
    card_w = 66
    card_h = 93
    mid_h = 59
    bot_h = 18
    pad = 2

    lines: List[str] = []
    lines.append(r"\documentclass[a4paper]{article}")
    lines.append(r"\usepackage[utf8]{inputenc}")
    lines.append(r"\usepackage[T1]{fontenc}")
    lines.append(r"\usepackage{helvet}")
    lines.append(r"\renewcommand{\familydefault}{\sfdefault}")
    lines.append(r"\usepackage{graphicx}")
    lines.append(r"\usepackage[dvipsnames]{xcolor}")
    lines.append(r"\definecolor{OutilsGris}{RGB}{90,90,90}")
    lines.append(r"\definecolor{OutilsViolet}{RGB}{128,0,128}")
    lines.append(r"\definecolor{OutilsMarron}{RGB}{139,69,19}")
    lines.append(r"\definecolor{OutilsJaune}{RGB}{180,130,0}")
    lines.append(r"\definecolor{OutilsOrange}{RGB}{230,120,0}")
    lines.append(r"\usepackage{tikz}")
    lines.append(rf"\usepackage[margin={margin}mm]{{geometry}}")
    lines.append(r"\pagestyle{empty}")
    lines.append(r"\setlength\parindent{0pt}")
    lines.append(r"\setlength\parskip{0pt}")
    lines.append(r"\setlength{\fboxsep}{0pt}")
    lines.append(r"\newcommand{\img}[2][]{\includegraphics[#1]{\detokenize{#2}}}")
    lines.append(r"\begin{document}")

    # Page de garde.
    lines.append(r"\vspace*{50mm}")
    lines.append(r"\begin{center}")
    lines.append(r"{\LARGE Cartes de vocabulaire}\\[30mm]")
    lines.append(r"{\Huge\bfseries MOTS OUTILS}\\[10mm]")
    lines.append(r"\vfill")
    lines.append(r"{\Large Vocabix}")
    lines.append(r"\end{center}")
    lines.append(r"\newpage")

    cards_on_page = 0
    cards_in_row = 0
    current_color: Optional[str] = None

    for image_path, word_color, gender, number in images_with_meta:
        raw_stem = image_path.stem
        display_stem, _, _ = parse_noun_filename_markers(raw_stem)
        vocab = latex_escape(display_stem)

        newpage_needed = False
        if cards_on_page > 0 and cards_on_page % 9 == 0:
            newpage_needed = True

        if current_color is not None and word_color != current_color and cards_on_page > 0:
            if cards_on_page % 9 != 0:
                remaining = 9 - (cards_on_page % 9)
                for _ in range(remaining):
                    lines.append(rf"\begin{{tikzpicture}}[x=1mm,y=1mm,baseline=0mm]")
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

        if cards_in_row == 0:
            lines.append(r"\noindent%")

        current_color = word_color

        lines.append(rf"\begin{{tikzpicture}}[x=1mm,y=1mm,baseline=0mm]")
        lines.append(rf"\draw[thick] (0,0) rectangle ({card_w},{card_h});")
        lines.append(rf"\draw[dashed] (0,{bot_h}) -- ({card_w},{bot_h});")
        lines.append(rf"\draw[dashed] (0,{bot_h + mid_h}) -- ({card_w},{bot_h + mid_h});")

        # Images de pluriel / genre uniquement si suffixes presents.
        if number == "p":
            plural_file = vocabix_dir / "p.png"
            if plural_file.exists():
                plural_str = plural_file.resolve().as_posix()
                lines.append(
                    r"\node[anchor=north west] at ("
                    + rf"{card_w - pad - 24},{card_h - pad}"
                    + r") {\img[height="
                    + rf"12mm,keepaspectratio]"
                    + r"{" + plural_str + r"}};"
                )

        if gender:
            gender_name = "masculin" if gender == "m" else "feminin"
            gender_file = vocabix_dir / f"{gender_name}.png"
            if gender_file.exists():
                gender_str = gender_file.resolve().as_posix()
                lines.append(
                    r"\node[anchor=north west] at ("
                    + rf"{card_w - pad - 8},{card_h - pad + 1}"
                    + r") {\img[height="
                    + rf"12mm,keepaspectratio]"
                    + r"{" + gender_str + r"}};"
                )

        actual_image_path = convert_webp_if_needed(image_path, output_dir)
        img_str = actual_image_path.resolve().as_posix()
        lines.append(
            r"\node[anchor=center] at ("
            + rf"{card_w / 2},{bot_h + mid_h / 2}"
            + r") {\img[width="
            + rf"{card_w - 2 * pad}mm,height={mid_h - 2 * pad}mm,keepaspectratio]"
            + r"{" + img_str + r"}};"
        )

        text_length = len(vocab)
        if text_length < 15:
            font_size = r"\huge"
        elif text_length < 18:
            font_size = r"\LARGE"
        else:
            font_size = r"\large"

        lines.append(
            r"\node[anchor=center] at ("
            + rf"{card_w / 2},{bot_h / 2}"
            + r") {"
            + font_size
            + r"\bfseries \textcolor{"
            + word_color
            + r"}{\MakeUppercase{"
            + vocab
            + r"}}};"
        )

        lines.append(r"\end{tikzpicture}%")

        cards_in_row += 1
        cards_on_page += 1

        if cards_in_row % 3 == 0:
            lines.append(r"\\")
            cards_in_row = 0
        else:
            lines.append(rf"\hspace{{{card_gap}mm}}%")

    if cards_in_row > 0:
        for idx in range(3 - cards_in_row):
            lines.append(rf"\begin{{tikzpicture}}[x=1mm,y=1mm,baseline=0mm]")
            lines.append(rf"\draw[white] (0,0) rectangle ({card_w},{card_h});")
            lines.append(r"\end{tikzpicture}%")
            if idx < 2:
                lines.append(rf"\hspace{{{card_gap}mm}}%")

    lines.append(r"\end{document}")
    return "\n".join(lines)


def generate_outils_cards(base_dir: pathlib.Path, output_dir: pathlib.Path, engine: str, vocabix_dir: pathlib.Path) -> None:
    """
    Genere un PDF de cartes mots outils depuis Outils/<couleur>.
    Le PDF final est copie dans Outils/Outils.pdf.
    """
    outils_dir = base_dir / "Outils"
    ensure_outils_structure(outils_dir)

    images_with_meta: List[Tuple[pathlib.Path, str, Optional[str], Optional[str]]] = []

    for folder_name in OUTILS_COLOR_ORDER:
        folder_path = outils_dir / folder_name
        latex_color = OUTILS_COLOR_LATEX[folder_name]
        for image_path in iter_image_files(folder_path):
            _, gender, number = parse_noun_filename_markers(image_path.stem)
            images_with_meta.append((image_path, latex_color, gender, number))

    if not images_with_meta:
        print(f"[skip] No images in {outils_dir}")
        return

    temp_out = output_dir / "Outils"
    temp_out.mkdir(parents=True, exist_ok=True)
    tex_path = temp_out / "Outils.tex"

    try:
        tex_content = build_latex(images_with_meta, vocabix_dir, temp_out)
        tex_path.write_text(tex_content, encoding="utf-8")
        print(f"[ok] Wrote {tex_path}")
    except (PermissionError, OSError) as e:
        print(f"[error] Failed to write {tex_path}: {e}")
        return

    cmd = [
        engine,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-output-directory",
        str(temp_out),
        str(tex_path),
    ]
    print("[run]", " ".join(cmd))
    subprocess.run(cmd, check=False)

    pdf_path = temp_out / "Outils.pdf"
    if pdf_path.exists():
        dest_pdf = outils_dir / "Outils.pdf"
        shutil.copy2(pdf_path, dest_pdf)
        print(f"[ok] PDF copied to {dest_pdf}")
    else:
        print(f"[error] PDF not generated at {pdf_path}")