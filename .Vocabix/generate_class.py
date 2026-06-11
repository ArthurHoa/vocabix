#!/usr/bin/env python3
import argparse
import pathlib
import shutil
import subprocess
import sys
from typing import List, Optional

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}


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


def build_latex(images: List[pathlib.Path], output_dir: pathlib.Path) -> str:
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
    lines.append(r"{\Large Cartes de classe}\\[30mm]")
    lines.append(r"{\Huge\bfseries Élèves}\\")
    lines.append(r"\vfill")
    lines.append(r"{\large Vocabix}")
    lines.append(r"\end{center}")
    lines.append(r"\newpage")

    image_list = list(images)
    pages = (len(image_list) + 8) // 9
    for page in range(pages):
        if page > 0:
            lines.append(r"\newpage")
        lines.append(r"\noindent%")
        for i in range(9):
            idx = page * 9 + i
            if idx >= len(image_list):
                # Ajouter une carte vide pour compléter la grille
                lines.append(
                    rf"\begin{{tikzpicture}}[x=1mm,y=1mm,baseline=0mm]"
                )
                lines.append(rf"\draw[white] (0,0) rectangle ({card_w},{card_h});")
                lines.append(r"\end{tikzpicture}%")
            else:
                image_path = image_list[idx]
                vocab = latex_escape(image_path.stem)

                lines.append(
                    rf"\begin{{tikzpicture}}[x=1mm,y=1mm,baseline=0mm]"
                )
                lines.append(rf"\draw (0,0) rectangle ({card_w},{card_h});")
                lines.append(rf"\draw[dashed] (0,{bot_h}) -- ({card_w},{bot_h});")
                lines.append(rf"\draw[dashed] (0,{bot_h + mid_h}) -- ({card_w},{bot_h + mid_h});")

                # Texte "CARTE ÉLÈVE" au lieu du logo
                lines.append(
                    r"\node[anchor=center] at (" +
                    rf"{card_w / 2},{card_h - top_h / 2})" +
                    r" {\scriptsize\bfseries CARTE ÉLÈVE};"
                )

                # Convertir WebP en JPG si nécessaire
                actual_image_path = convert_webp_if_needed(image_path, output_dir)
                img_str = actual_image_path.resolve().as_posix()  # Chemin absolu compatible LaTeX/Windows
                lines.append(
                    r"\node[anchor=center] at (" +
                    rf"{card_w / 2},{bot_h + mid_h / 2})" +
                    r" {\img[width=" +
                    rf"{card_w - 2 * pad}mm,height={mid_h - 2 * pad}mm,keepaspectratio]" +
                    r"{" + img_str + r"}};"
                )
                
                # Adapter la taille de police en fonction de la longueur du nom
                name_length = len(vocab)
                if name_length < 11:
                    font_size = r"\Large"
                elif name_length < 13:
                    font_size = r"\large"
                elif name_length < 16:
                    font_size = r"\normalsize"
                elif name_length < 19:
                    font_size = r"\small"
                else:
                    font_size = r"\footnotesize"
                
                lines.append(
                    r"\node[anchor=center] at (" +
                    rf"{card_w / 2},{bot_h / 2})" +
                    r" {" + font_size + r"\bfseries \MakeUppercase{" + vocab + r"}};"
                )
                lines.append(r"\end{tikzpicture}%")

            # Ajouter un espace ou retour à la ligne
            if (i + 1) % 3 == 0 and i < 8:
                lines.append(rf"\\[{card_gap}mm]%")
                lines.append(r"\noindent%")
            elif i < 8:
                lines.append(rf"\hspace{{{card_gap}mm}}%")

    lines.append(r"\end{document}")
    return "\n".join(lines)


def generate_class_cards(eleves_dir: pathlib.Path, output_dir: pathlib.Path, engine: str) -> None:
    images_dir = eleves_dir / "images"
    images = iter_image_files(images_dir)
    if not images:
        print(f"[skip] No images in {images_dir}")
        return

    # Générer dans .output/Élèves
    temp_out = output_dir / "Élèves"
    temp_out.mkdir(parents=True, exist_ok=True)
    tex_path = temp_out / "Élèves.tex"
    tex_path.write_text(build_latex(images, temp_out), encoding="utf-8")
    print(f"[ok] Wrote {tex_path}")

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
    
    # Copier uniquement le PDF dans le dossier Élèves
    pdf_path = temp_out / "Élèves.pdf"
    if pdf_path.exists():
        dest_pdf = eleves_dir / "Élèves.pdf"
        shutil.copy2(pdf_path, dest_pdf)
        print(f"[ok] PDF copied to {dest_pdf}")
    else:
        print(f"[error] PDF not generated at {pdf_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate class cards PDF from Élèves folder."
    )
    parser.add_argument(
        "--eleves-dir",
        default="../Élèves",
        help="Élèves directory (default: Élèves)",
    )
    parser.add_argument(
        "--output-dir",
        default=".output",
        help="Temp directory for LaTeX build files (default: .output)",
    )
    parser.add_argument(
        "--engine",
        default="pdflatex",
        help="LaTeX engine (pdflatex, lualatex, xelatex)",
    )
    args = parser.parse_args()

    eleves_dir = pathlib.Path(args.eleves_dir)
    output_dir = pathlib.Path(args.output_dir)
    if not eleves_dir.exists():
        print(f"[error] Élèves dir not found: {eleves_dir}")
        return 1

    generate_class_cards(eleves_dir, output_dir, args.engine)
    return 0


if __name__ == "__main__":
    sys.exit(main())
