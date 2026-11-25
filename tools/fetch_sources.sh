#!/bin/bash
# Download the corresponding source code (source RPMs) for every package in a Credo OS ISO, to
# publish next to the ISO. GPL and LGPL licences require offering this source with the binaries.
#
#   bash tools/fetch_sources.sh out/v3/Credo-OS-45-x86_64.iso.packages.tsv out/v3/sources
#
# Run it on a Fedora system (or the Fedora WSL build environment) soon after building, while the
# same package versions are still in Fedora's repositories. Expect several GB.
set -euo pipefail
LIST=${1:?package list (.packages.tsv from the build)}
DEST=${2:?output folder}
REL=$(awk -F'\t' '$1=="generic-release"||$1=="fedora-release-common"{split($2,a,"-"); print a[1]; exit}' "$LIST")
mkdir -p "$DEST/SRPMS"
# Column 4 is the source RPM file name, e.g. bash-5.2.37-1.fc45.src.rpm
cut -f4 "$LIST" | sort -u | grep '\.src\.rpm$' | sed 's/\.src\.rpm$//' > "$DEST/srpm-list.txt"
echo "$(wc -l < "$DEST/srpm-list.txt") source packages (Fedora ${REL:-?})"
cd "$DEST/SRPMS"
missing=0
while read -r nvr; do
  [ -f "$nvr.src.rpm" ] && continue
  if ! dnf download --source --releasever="${REL:-45}" -q "$nvr" 2>/dev/null; then
    echo "  not found in the repositories: $nvr" | tee -a ../missing.txt
    missing=$((missing + 1))
  fi
done < ../srpm-list.txt
sha256sum ./*.src.rpm > ../SHA256SUMS
echo "Done: $(ls | wc -l) source RPMs in $DEST/SRPMS ($missing missing; see missing.txt)."
echo "Missing ones were updated in Fedora since the build: get them from https://koji.fedoraproject.org"
