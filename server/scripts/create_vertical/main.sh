#!/usr/bin/env bash

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_SCRIPTS_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

source "${ROOT_SCRIPTS_DIR}/lib/bash/io.sh"
source "${ROOT_SCRIPTS_DIR}/lib/bash/validation.sh"
source "${SCRIPT_DIR}/context.sh"
source "${SCRIPT_DIR}/templates.sh"
source "${SCRIPT_DIR}/django.sh"
source "${SCRIPT_DIR}/infra.sh"

main() {
  echo "************ SPDB: Vertical generator ************"
  echo

  init_context
  read_context_inputs "${1:-}"
  build_context
  print_context_summary
  echo

  confirm_or_exit "Create this vertical? [y/N]: "

  create_target_dir
  create_django_project
  create_django_app
  write_dockerfile

  pause "Django files will now be patched. Press Enter to continue..."
  patch_django_files

  pause "Infra files will now be patched. Press Enter to continue..."
  patch_infra_files

  echo
  echo "✅ Created: server/verticals/${VERTICAL}/ and patched infra files."
}