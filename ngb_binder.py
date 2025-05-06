#!/usr/bin/env python3

"""
Bind National Geographic JPG scans into a single PDF file.

Usage (single issue by date):
    ngm_bind.py /root/path 199408

Usage (single issue by exact folder):
    ngm_bind.py -d /exact/path/to/folder

Usage (batch mode):
    ngm_bind.py --all /root/path [--jobs N] [--output OUTPUTDIR]
"""

import os
import re
import sys
import argparse
import threading
import time
import signal
from pathlib import Path
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor

lock = threading.Lock()
progress_state = []
start_time = None

SYMBOLS = {
    'todo': '🔘',
    'running': '🔄',
    'done': '✅',
    'fail': '❌'
}


def print_progress():
    done = progress_state.count(SYMBOLS['done'])
    fail = progress_state.count(SYMBOLS['fail'])
    total = len(progress_state)
    elapsed = time.time() - start_time if start_time else 0
    est_total_time = (elapsed / (done + fail)) * total if (done + fail) else 0
    eta = est_total_time - elapsed
    print("{}  {}/{}  Elapsed: {:.1f}s  ETA: {:.1f}s".format(''.join(progress_state), done + fail, total, elapsed, max(0, eta)), end='\r')

def update_progress(index, state):
    with lock:
        progress_state[index] = SYMBOLS[state]
        print_progress()

def extract_yyyymm(foldername):
    match = re.search(r'(\d{6})', os.path.basename(foldername))
    if not match:
        return None
    return match.group(1)

def get_target_folder(rootdir, yyyymm):
    print(f"Discovering folders for issue {yyyymm} under {rootdir}... please wait")
    candidates = []
    for path in Path(rootdir).rglob(f'{yyyymm}*'):
        if path.is_dir():
            candidates.append(str(path))
    if not candidates:
        print("No matching folders found that match given date: {}".format(yyyymm))
        exit(1)
    elif len(candidates) == 1:
        return candidates[0]
    else:
        for i, path in enumerate(candidates):
            print("{}: {}".format(i + 1, path))
        choice = int(input("Select one: "))
        return candidates[choice - 1]

def get_jpg_files(folder, yyyymm):
    pattern = re.compile(r'^NGM_{}_{}_[0-9]{{3}}[A-Z]?_[0-9]\.jpg$'.format(yyyymm[:4], yyyymm[4:6]), re.IGNORECASE)
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
    return page_files + extra_files

def build_pdf(jpg_list, output_path, fail_log=None):
    temp_output = output_path + ".chk"
    image_list = []
    failed_files = []
    for f in jpg_list:
        try:
            img = Image.open(f).convert("RGB")
            image_list.append(img)
        except:
            failed_files.append(f)
    if image_list:
        os.makedirs(os.path.dirname(temp_output), exist_ok=True)
        try:
            if not temp_output.lower().endswith('.pdf.chk'):
                raise ValueError("Temporary output file must end with .pdf.chk")
            image_list[0].save(temp_output, save_all=True, append_images=image_list[1:], format="PDF")
            os.rename(temp_output, output_path)
        except Exception as e:
            failed_files.append(f"WRITE_ERROR: {e}")
            if os.path.exists(temp_output):
                os.remove(temp_output)
    if fail_log and failed_files:
        with open(fail_log, "a") as f:
            for path in failed_files:
                f.write(path + "\n")
    return failed_files

def process_folder_indexed(index, folder, output_dir):
    update_progress(index, 'running')
    yyyymm = extract_yyyymm(folder)
    if not yyyymm:
        update_progress(index, 'fail')
        return
    output_file = f'NGM_{yyyymm}.pdf'
    output_path = os.path.join(output_dir, output_file)
    fail_log = os.path.join(output_dir, "failed.log")

    if os.path.exists(output_path):
        update_progress(index, 'done')
        return
    if os.path.exists(output_path + ".chk"):
        os.remove(output_path + ".chk")

    jpgs = get_jpg_files(folder, yyyymm)
    if not jpgs:
        update_progress(index, 'fail')
        return

    failed = build_pdf(jpgs, output_path, fail_log=fail_log)
    update_progress(index, 'fail' if failed else 'done')

def has_jpgs(p):
    try:
        return p.is_dir() and any(f.suffix.lower() == ".jpg" for f in p.iterdir())
    except:
        return False

def run_batch(root, jobs, output_dir):
    global start_time
    print("Scanning directory tree under '{}'...".format(root))
    candidates = list(Path(root).rglob("*"))
    print("Discovered {} entries, checking for folders with JPGs...".format(len(candidates)))
    with ThreadPoolExecutor(max_workers=jobs or 4) as pool:
        folders = list(filter(None, pool.map(lambda p: str(p) if has_jpgs(p) else None, candidates)))
    print("Found {} folders with JPGs. Starting PDF conversion...".format(len(folders)))
    global progress_state
    start_time = time.time()
    progress_state = [SYMBOLS['todo']] * len(folders)
    print_progress()

    shutdown_flag = threading.Event()

    def shutdown_handler(signum, frame):
        print("\n[INTERRUPT] Shutting down cleanly...")
        shutdown_flag.set()

    signal.signal(signal.SIGINT, shutdown_handler)

    with ProcessPoolExecutor(max_workers=jobs) as executor:
        try:
            futures = {executor.submit(process_folder_indexed, i, folder, output_dir): i for i, folder in enumerate(folders)}
            for future in as_completed(futures):
                if shutdown_flag.is_set():
                    break
        except KeyboardInterrupt:
            print("\n[CTRL+C] Caught KeyboardInterrupt. Cancelling all tasks.")
            executor.shutdown(wait=False, cancel_futures=True)
            raise
    print()  # final newline

def main():
    parser = argparse.ArgumentParser(description='Bind National Geographic JPG scans into a single PDF file.')
    parser.add_argument('--all', metavar='ROOT', help='Scan all subfolders with JPGs under ROOT and convert to PDF')
    parser.add_argument('--jobs', type=int, help='Limit parallel jobs (default: CPU count)')
    parser.add_argument('--output', metavar='OUTPUTDIR', default=os.getcwd(), help='Directory to write output PDFs (default: current directory)')
    parser.add_argument('-d', '--dir', metavar='DIR', help='Use exact directory (skip discovery)')
    parser.add_argument('src', nargs='?', help='Root folder to search (for single issue mode)')
    parser.add_argument('yyyymm', nargs='?', help='Year and month in format YYYYMM')
    args = parser.parse_args()

    if args.all:
        jobs = args.jobs or os.cpu_count()
        run_batch(args.all, jobs, args.output)
        return

    if args.dir:
        folder = args.dir
        yyyymm = extract_yyyymm(folder)
        if not yyyymm:
            print(f"Error: Could not extract YYYYMM from directory name: {folder}")
            sys.exit(1)
    else:
        if not args.src or not args.yyyymm:
            parser.print_help()
            sys.exit(1)
        folder = get_target_folder(args.src, args.yyyymm)
        yyyymm = args.yyyymm

    jpgs = get_jpg_files(folder, yyyymm)
    if not jpgs:
        return
    output_file = 'NGM_{}.pdf'.format(yyyymm)
    output_path = os.path.join(args.output, output_file)
    fail_log = os.path.join(args.output, "failed.log")
    if os.path.exists(output_path + ".chk"):
        os.remove(output_path + ".chk")
    failed = build_pdf(jpgs, output_path, fail_log=fail_log)
    if failed:
        print("Warning: Some images failed to process. Details logged to failed.log")

if __name__ == '__main__':
    main()

