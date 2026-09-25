# TODO

- Library search, `ast/__init__.py:143`: `OPENSCADPATH` replaces the default libraries folder
  instead of being searched before it; Windows hard-codes `~\Documents` (wrong under OneDrive
  Known Folder Move); libraries beside the binary are never searched. Same bug fixed in
  openscad_cpp_parser #10
