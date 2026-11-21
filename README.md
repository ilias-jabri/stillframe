# Stillframe

Stillframe is a native GTK desktop tool for taking screenshots, editing them, and recording the screen. It is built for Linux Mint with Cinnamon on X11. Captures, edits, and recordings stay local. At startup, the app asks Linux to block every socket family except Unix-domain sockets, which GTK uses to talk to the local desktop.

## Install on Linux

Download the `.deb` from [GitHub Releases](https://github.com/ilias-jabri/stillframe/releases/latest). The package is built for Linux Mint and Ubuntu-based desktops running an X11 session. From the download directory, run:

```sh
sudo apt install ./stillframe_1.0.0_all.deb
```

Open **Stillframe** from the application menu or run `stillframe`. To set up **Super+Shift+S** on Cinnamon, add a custom shortcut under **System Settings → Keyboard → Shortcuts → Custom Shortcuts** with the command `stillframe --capture region`.

## Run from source

Run `./stillframe` with system Python. The app uses GTK 3, PyGObject, Cairo, libwnck, and libseccomp. Recording uses the local GStreamer X11 capture and WebM plugins with VP9 or VP8 encoding.

Run `./install --shortcut` for a user-local installation with **Super+Shift+S** when the combination is free in Cinnamon. Omit `--shortcut` to install only the application menu entry.

## Capture and edit

- **New snip** takes a rectangle, a freehand outline, a window, or the entire desktop. Select a 3-, 5-, or 10-second delay when you need time to open a menu. The window mode captures the desktop pixels visible inside the selected window's frame. Fullscreen includes every connected monitor.
- **Super+Shift+S**, when registered, opens an immediate rectangle selector. Press **Esc** to cancel. **Ctrl+N** uses the mode and delay selected in the app.
- The **Pen** is first in the editing toolbar and is selected when a new image opens. Use **Eraser** (**D**) to click or drag across whole annotations, then undo the gesture if needed. The toolbar also has a highlighter, arrow, rectangle, ellipse, text, solid redaction, and crop. Use **Ink** to change color and stroke width.
- New screenshots and edits copy automatically by default. The clipboard updates after annotations, crops, undo, and redo. Change this in **Preferences**, or press **Ctrl+C** to copy manually. **Ctrl+S** saves a PNG or JPEG. PNG preserves transparency from freehand captures.
- **Ctrl+O** opens a local image. Use **Ctrl+0** to fit it to the window, **Ctrl+1** for actual size, or hold **Ctrl** while scrolling to zoom.

## Record the screen

Choose **Record**, select a rectangle or all displays, and choose a destination. The floating recording control shows elapsed time. Use **Stop** to finalize the WebM. A full-desktop recording includes the control while it is visible. You can minimize it and restore it from the taskbar, or run `stillframe --stop-recording` to stop a packaged build. Recordings contain video only.

Video uses the selected region's native pixel dimensions and targets 30 frames per second. VP9 retains full color resolution for sharp text and interface details.

## Build the package

Run `./packaging/build-deb 1.0.0` with `dpkg-deb` available. The package is written to `dist/`. Pass a second argument to choose an output directory.
