# image_stitcher

A simple Python GUI (Tkinter + Pillow) to stitch images vertically or horizontally. It supports **proportional edge alignment, max/min reference edge, spacing, background color, live preview (toggleable), single/direct export, and auto reset**.

## Features
- Drag & drop multiple images or folders
- Vertical/Horizontal stitching with proportional alignment (vertical: same width / horizontal: same height; choose max/min edge)
- Set spacing and background color
- **Live Preview panel** (zoomable, scrollable; can be shown/hidden)
- Export modes
  - Single export: show a save dialog
  - Direct export: choose output folder & extension; filenames auto-increment `1,2,3…` (text-only success message)
- **Auto reset**: after a successful export, clears the list and resets the direct-export index to 1

## Install
```bash
pip install -r requirements.txt
# On Linux you may need Tkinter:
# Ubuntu/Debian: sudo apt-get install python3-tk
```

## Run
```bash
python image_stitcher.py
```

## License
MIT
