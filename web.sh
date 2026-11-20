#!/bin/bash
cd "$(dirname "$0")/web" && python3 -m http.server --bind 0.0.0.0 8000
