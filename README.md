# Chorus audio samples

Static demo page for the Chorus paper (anonymous supplementary material).

Build:

```
python3 build_demo.py --bundle /path/to/bundle [--sssd-recordings]
```

`build_demo.py` reads `bundle/manifest.json`, copies the referenced audio into `audio/`, and writes `index.html`.
No dependencies beyond the Python standard library.
Open `index.html` directly in a browser, or serve the folder with any static file server.
