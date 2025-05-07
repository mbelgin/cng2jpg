#!/usr/bin/env python3
import os
import re
import sys
import argparse
import time
from pathlib import Path
from PIL import Image
from multiprocessing import Pool, cpu_count


def fast_find_dirs(root_path):
    found_dirs = []
    for entry in os.scandir(root_path):
        if entry.is_dir():
            found_dirs.append(entry.path)
            found_dirs.extend(fast_find_dirs(entry.path))
    return found_dirs


def extract_yyyymm(foldername):
    match = re.search(r'(\d{6})', os.path.basename(foldername))
    return match.group(1) if match else None


def check_existing_pdf(folder, output_dir):
    yyyymm = extract_yyyymm(folder)
    if not yyyymm:
        return False, None
    output_pdf = f"NGM_{yyyymm}.pdf"
    output_path = os.path.join(output_dir, output_pdf)
    temp_path = output_path + ".chk"
    if os.path.exists(output_path):
        return True, output_path
    if os.path.exists(temp_path):
        os.remove(temp_path)
    return False, output_path


def get_jpg_files(folder):
    try:
        files = sorted(f for f in os.listdir(folder) if f.lower().endswith('.jpg'))
        return [os.path.join(folder, f) for f in files]
    except Exception:
        return []


def build_pdf(jpg_list, output_path):
    tmp_path = output_path + ".chk"
    try:
        images = []
        for file in jpg_list:
            with Image.open(file) as im:
                images.append(im.convert('RGB'))
        if images:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            images[0].save(tmp_path, save_all=True, append_images=images[1:], format="PDF")
            os.rename(tmp_path, output_path)
            return True
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return False


def process_folder(args):
    index, folder, total, output_dir = args
    folder_name = os.path.basename(folder)
    yyyymm = extract_yyyymm(folder)
    if not yyyymm:
        return index, folder_name, "⏭️ Skipped"

    has_pdf, output_path = check_existing_pdf(folder, output_dir)
    if has_pdf:
        return index, folder_name, "🟦 Existing"

    jpgs = get_jpg_files(folder)
    if not jpgs:
        return index, folder_name, "⏭️ Skipped"

    success = build_pdf(jpgs, output_path)
    return index, folder_name, "✅ Converted" if success else "❌ Failed"


def run_batch(root, output_dir, jobs):
    print(f"Scanning directory tree under '{root}'... please wait")
    start = time.time()
    folders = fast_find_dirs(root)
    print(f"Found {len(folders)} folders in {time.time() - start:.2f} seconds.\n")

    total = len(folders)
    args_list = [(i + 1, folder, total, output_dir) for i, folder in enumerate(folders)]

    with Pool(processes=jobs) as pool:
        for index, foldername, status in pool.imap_unordered(process_folder, args_list):
            print(f"Processed {index}/{total} - [{foldername}] - Status: {status}")


def main():
    parser = argparse.ArgumentParser(description='Bind National Geographic JPG scans into a single PDF file.')
    parser.add_argument('--all', metavar='ROOT', help='Scan all subfolders with JPGs under ROOT and convert to PDF')
    parser.add_argument('--output', metavar='OUTPUTDIR', default=os.getcwd(), help='Directory to write output PDFs')
    parser.add_argument('--jobs', type=int, default=cpu_count(), help='Number of parallel jobs to run')
    args = parser.parse_args()

    if args.all:
        run_batch(args.all, args.output, args.jobs)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()

