#!/usr/bin/env python3

"""
Bind National Geographic JPG scans into a single PDF file.

Usage:
    ngm_bind.py /path/to/images 197103

This script searches for JPG files corresponding to a specific issue (based on year and month)
and combines them into a single PDF file named 'NGM_YYYYMM.pdf' in the current directory.
"""

import os
import re
import argparse
from pathlib import Path
from PIL import Image

def get_target_folder(rootdir, yyyymm):
    print("Searching for folders starting with '{}' under '{}'...".format(yyyymm, rootdir))
    candidates = []
    for path in Path(rootdir).rglob(f'{yyyymm}*'):
        if path.is_dir():
            candidates.append(str(path))

    if not candidates:
        print("No matching folders found that match given date: {}".format(yyyymm)) 
        exit(1)
    elif len(candidates) == 1:
        print("Found folder: {}".format(candidates[0]))
        return candidates[0]
    else:
        print("Multiple folders found:")
        for i, path in enumerate(candidates):
            print("{}: {}".format(i + 1, path))
        choice = int(input("Select one: "))
        print("Selected folder: {}".format(candidates[choice - 1]))
        return candidates[choice - 1]

def get_jpg_files(folder, yyyymm):
    print("Scanning for JPG files in '{}'...".format(folder))
    pattern = re.compile(r'^NGM_{}_{}_\d{{3}}[A-Z]?_\d\.jpg$'.format(yyyymm[:4], yyyymm[4:6]), re.IGNORECASE)
    page_files = []
    extra_files = []
    for file in sorted(os.listdir(folder)):
        fullpath = os.path.join(folder, file)
        if not os.path.isfile(fullpath):
            continue
        if not file.lower().endswith('.jpg'):
            continue
        try:
            with Image.open(fullpath) as im:
                im.verify()
            if pattern.match(file):
                page_files.append(fullpath)
            else:
                extra_files.append(fullpath)
        except:
            continue
    all_files = page_files + extra_files
    print("Found {} JPG files (all verified as images)".format(len(all_files)))
    return all_files

def build_pdf(jpg_list, output_path):
    image_list = []
    print("Converting images to PDF pages...")
    for i, f in enumerate(jpg_list):
        try:
            img = Image.open(f).convert("RGB")
            image_list.append(img)
            print("[{}/{}] {}".format(i + 1, len(jpg_list), os.path.basename(f)))
        except:
            print("[{}/{}] Skipped unreadable: {}".format(i + 1, len(jpg_list), f))
    if image_list:
        print("Writing PDF to: {}".format(output_path))
        image_list[0].save(output_path, save_all=True, append_images=image_list[1:])
        print("[OK] PDF created successfully.")
    else:
        print("No valid images to save. Exiting.")

def main():
    parser = argparse.ArgumentParser(description='Bind National Geographic JPG scans into a single PDF file.')
    parser.add_argument('src', help='Root folder to search')
    parser.add_argument('yyyymm', help='Year and month in the format YYYYMM (e.g., 197103)')
    args = parser.parse_args()

    output_file = 'NGM_{}.pdf'.format(args.yyyymm)
    output_path = os.path.abspath(output_file)

    folder = get_target_folder(args.src, args.yyyymm)
    jpgs = get_jpg_files(folder, args.yyyymm)

    if not jpgs:
        print("No JPGs found. Exiting.")
        return

    build_pdf(jpgs, output_path)

if __name__ == '__main__':
    main()

