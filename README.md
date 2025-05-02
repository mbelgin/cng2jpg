# cng2jpg
Convert "Complete National Geographic" CNG files to JPG for use under Linux

## Basic usage

### copying from CD into local hard drive:

```sh
cng2jpg.py --src /run/media/_user_/CNG_DISC1/disc1/images --dst ~/CNG/discs/images
```

### convert a hard drive copy

```sh
cng2jpg.py --src ~/CNG/discs [--remove]
```
Use --remove to get rid of .cng files as they are converted, to avoid needing extra 40+Gb of space for both jpg and cng.

## PDF binding

After converting .cng files to .jpg using cng2jpg.py, you can optionally bind all images from a given issue into a single PDF using ngm_bind.py.

### bind a specific issue into a PDF

```sh
python3 ngm_bind.py /path/to/source YYYYMM 
```

E.g. 

```sh
python3 ngm_bind.py ./NGM_Disc3 199408 
```

This will search for a folder inside NGM_Disc3 that starts with 199408, collect all .jpg files, and create NGM_199408.pdf in the current directory.

Files matching the format NGM_YYYY_MM_###_#.jpg (with optional letter suffixes like 051B) are sorted and added first. Remaining .jpg files (e.g. inserts, foldouts, maps) are added after.

Requires the Pillow Python package:

```sh
pip install pillow
```


## References

"The cng files are all jpegs, XOR'd bitwise with 239"

http://www.subdude-site.com/WebPages_Local/RefInfo/Computer/Linux/LinuxGuidesByBlaze/appsImagePhotoTools/cng2jpgGuide/cng2jpg_guide.htm
