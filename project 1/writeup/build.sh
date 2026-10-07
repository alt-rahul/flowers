#!/bin/sh
# Rebuild writeup.pdf from writeup.md (needs pandoc and Node's playwright).
cd "$(dirname "$0")"
pandoc writeup.md -s --mathml --embed-resources -c style.css -o writeup.html
NODE_PATH="${NODE_PATH:-$(npm root -g)}" node build_pdf.js
