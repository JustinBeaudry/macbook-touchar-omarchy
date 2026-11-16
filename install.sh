#!/usr/bin/env bash
# Never invokes suspend, SOCW or the SPI pulse during installation.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
yes=0
with_spi=0
remove=''
for arg in "$@"; do
  case "$arg" in
    --yes) yes=1 ;;
    --with-spi-pulse) with_spi=1 ;;
    --uninstall|--uninstall-spi-pulse)
      [[ -z $remove ]] || { echo 'Specify only one removal mode' >&2; exit 2; }
      remove=$arg ;;
    *) echo 'Usage: sudo bash install.sh [--yes] [--with-spi-pulse] | --uninstall | --uninstall-spi-pulse' >&2; exit 2 ;;
  esac
done
[[ -z $remove || $with_spi == 0 ]] || { echo 'Cannot install and uninstall together' >&2; exit 2; }
(( EUID == 0 )) || { echo 'Run from a terminal with sudo bash install.sh' >&2; exit 1; }

base=(
  'bin/macbook-touchbar-wake:/usr/local/libexec/macbook-touchbar-wake'
  'systemd/90-macbook-touchbar-wake.conf:/etc/systemd/system/systemd-suspend.service.d/90-macbook-touchbar-wake.conf'
)
spi=(
  'bin/macbook-spi-wake-pulse:/usr/local/libexec/macbook-spi-wake-pulse'
  'systemd/macbook-spi-wake-pulse.service:/etc/systemd/system/macbook-spi-wake-pulse.service'
  'systemd/80-macbook-spi-wake-pulse.conf:/etc/systemd/system/systemd-suspend.service.d/80-macbook-spi-wake-pulse.conf'
)

check_collisions() {
  local pair source destination
  for pair in "$@"; do
    source=${pair%%:*}; destination=${pair#*:}
    if [[ -e $destination || -L $destination ]]; then
      [[ ! -L $destination ]] && cmp -s "$root/$source" "$destination" || {
        echo "Refusing to overwrite/remove changed file: $destination" >&2; return 1;
      }
    fi
  done
}

if [[ -n $remove ]]; then
  files=("${spi[@]}")
  [[ $remove != --uninstall ]] || files+=("${base[@]}")
  check_collisions "${files[@]}"
  # Stop new triggers first, then invoke the unit's independent restoration.
  rm -f -- /etc/systemd/system/systemd-suspend.service.d/80-macbook-spi-wake-pulse.conf
  systemctl daemon-reload
  if [[ -f /etc/systemd/system/macbook-spi-wake-pulse.service ]]; then
    systemctl stop macbook-spi-wake-pulse.service
  fi
  if [[ -f /usr/local/libexec/macbook-spi-wake-pulse ]]; then
    /usr/local/libexec/macbook-spi-wake-pulse --restore
  fi
  for pair in "${files[@]}"; do rm -f -- "${pair#*:}"; done
  rmdir /run/macbook-spi-wake-pulse 2>/dev/null || true
  systemctl daemon-reload
  echo 'Removed selected workaround files. No sleep or wake operation performed.'
  exit 0
fi

command -v python3 >/dev/null
command -v timeout >/dev/null
command -v systemctl >/dev/null
[[ -f /usr/lib/systemd/system/systemd-suspend.service ]] || {
  echo 'Expected systemd suspend service not found; refusing installation.' >&2; exit 1;
}
python3 "$root/bin/macbook-touchbar-wake" --check
files=("${base[@]}")
if (( with_spi )); then
  python3 "$root/bin/macbook-spi-wake-pulse" --check
  files+=("${spi[@]}")
fi
check_collisions "${files[@]}"
for pair in "${files[@]}"; do
  source=${pair%%:*}
  if [[ $source == bin/* ]]; then
    python3 -c 'import ast,sys; ast.parse(open(sys.argv[1]).read())' "$root/$source"
  fi
done

printf '\nEnable verified-model Touch Bar recovery after system suspend.\n'
if (( with_spi )); then
  printf 'Also enable the OPTIONAL 2-second SPI pulse with independent systemd restoration.\n'
  printf 'Original idle-power settings are restored, not permanently forced on.\n'
fi
printf 'ACPI calls can hang affected machines. Save work before sleep/wake testing.\n'
printf 'Files:\n'
for pair in "${files[@]}"; do printf '  %s\n' "${pair#*:}"; done
if (( ! yes )); then
  read -r -p 'Type INSTALL to enable (does not sleep now): ' answer
  [[ $answer == INSTALL ]] || { echo 'Cancelled.'; exit 1; }
fi
for pair in "${files[@]}"; do
  source=${pair%%:*}; destination=${pair#*:}
  mode=0644
  [[ $source != bin/* ]] || mode=0755
  install -D -o root -g root -m "$mode" "$root/$source" "$destination"
done
systemctl daemon-reload
echo 'Installed for the next suspend/resume. No sleep, ACPI call or SPI pulse performed now.'
echo 'Inspect: systemctl cat systemd-suspend.service'
echo 'Logs: journalctl -b -u systemd-suspend.service -u macbook-spi-wake-pulse.service --no-pager -n 80'
