#!/usr/bin/env bash
# Install/remove the exact verified-model workaround. Never invokes suspend or SOCW.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
helper=/usr/local/libexec/macbook-touchbar-wake
dropin=/etc/systemd/system/systemd-suspend.service.d/90-macbook-touchbar-wake.conf
mode=${1:-}
case "$mode" in
  ''|--yes|--uninstall) ;;
  *) echo 'Usage: sudo bash install.sh [--yes|--uninstall]' >&2; exit 2 ;;
esac
(( $# <= 1 )) || { echo 'Too many arguments' >&2; exit 2; }
(( EUID == 0 )) || { echo 'Run from a terminal with sudo bash install.sh' >&2; exit 1; }

if [[ $mode == --uninstall ]]; then
  # Refuse to remove symlinks or locally changed files.
  for pair in "bin/macbook-touchbar-wake:$helper" "systemd/90-macbook-touchbar-wake.conf:$dropin"; do
    source=${pair%%:*}; destination=${pair#*:}
    if [[ -e $destination || -L $destination ]]; then
      [[ ! -L $destination ]] && cmp -s "$root/$source" "$destination" || {
        echo "Refusing to remove changed file: $destination" >&2; exit 1;
      }
    fi
  done
  rm -f -- "$dropin" "$helper"
  systemctl daemon-reload
  echo 'Removed automatic wake workaround. No sleep or ACPI call performed.'
  exit 0
fi

command -v python3 >/dev/null
command -v timeout >/dev/null
command -v systemctl >/dev/null
[[ -f /usr/lib/systemd/system/systemd-suspend.service ]] || {
  echo 'Expected systemd suspend service not found; refusing installation.' >&2; exit 1;
}
python3 "$root/bin/macbook-touchbar-wake" --check
python3 -c 'import ast,sys; ast.parse(open(sys.argv[1]).read())' "$root/bin/macbook-touchbar-wake"

for pair in "bin/macbook-touchbar-wake:$helper" "systemd/90-macbook-touchbar-wake.conf:$dropin"; do
  source=${pair%%:*}; destination=${pair#*:}
  if [[ -e $destination || -L $destination ]]; then
    [[ ! -L $destination ]] && cmp -s "$root/$source" "$destination" || {
      echo "Refusing to overwrite existing file: $destination" >&2; exit 1;
    }
  fi
done

printf '\nThis enables one SOCW(1) + HID-awake attempt after each system suspend.\n'
printf 'ACPI firmware calls can hang affected machines. Save your work before testing.\n'
printf 'Only the model and firmware fingerprint verified in this repo are accepted.\n'
printf 'Files: %s\n       %s\n' "$helper" "$dropin"
if [[ $mode != --yes ]]; then
  read -r -p 'Type INSTALL to enable (does not sleep now): ' answer
  [[ $answer == INSTALL ]] || { echo 'Cancelled.'; exit 1; }
fi
install -D -o root -g root -m 0755 "$root/bin/macbook-touchbar-wake" "$helper"
install -D -o root -g root -m 0644 "$root/systemd/90-macbook-touchbar-wake.conf" "$dropin"
systemctl daemon-reload
echo 'Installed. Applies on the next system suspend/resume; no sleep or ACPI call performed now.'
echo 'Inspect: systemctl cat systemd-suspend.service'
echo 'Logs: journalctl -b -u systemd-suspend.service --no-pager -n 60'
