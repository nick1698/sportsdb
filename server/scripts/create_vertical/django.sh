#!/usr/bin/env bash

create_target_dir() {
  info "Creating target directory: $TARGET_DIR"
  mkdir -p "$TARGET_DIR"
}

create_django_project() {
  info "Creating Django project: $SERVICE_PKG"
  (
    cd "$TARGET_DIR"
    django-admin startproject "$SERVICE_PKG" .
  )
}

create_django_app() {
  info "Creating Django app: $API_APP"
  (
    cd "$TARGET_DIR"
    python manage.py startapp "$API_APP"
  )
}

write_dockerfile() {
  info "Writing Dockerfile.dev"
  render_dockerfile_dev > "${TARGET_DIR}/Dockerfile.dev"
}

patch_settings_file() {
  info "Patching settings.py"

  if ! grep -qxF 'import os' "$SETTINGS_FILE"; then
    sed -i '/^from pathlib import Path$/a import os' "$SETTINGS_FILE"
  fi

  sed -i 's/^ALLOWED_HOSTS = .*/ALLOWED_HOSTS = ["*"]/' "$SETTINGS_FILE"

  sed -i "/^INSTALLED_APPS = \[/,/^]$/ {
    /\"${API_APP}\"/! {
      /^]$/i\    \"${API_APP}\",
    }
    /\"ninja\"/! {
      /^]$/i\    \"ninja\",
    }
    /\"django_extensions\"/! {
      /^]$/i\    \"django_extensions\",
    }
    /\"django.contrib.postgres\"/! {
      /^]$/i\    \"django.contrib.postgres\",
    }
  }" "$SETTINGS_FILE"

  sed -i "/^INSTALLED_APPS = \[/,/^]$/ {
    /django\.contrib\.admin/d
    /django\.contrib\.auth/d
    /django\.contrib\.sessions/d
    /django\.contrib\.messages/d
  }" "$SETTINGS_FILE"

  sed -i "/^MIDDLEWARE = \[/,/^]$/ {
    /django\.contrib\.auth\.middleware\.AuthenticationMiddleware/d
    /django\.contrib\.sessions\.middleware\.SessionMiddleware/d
    /django\.contrib\.messages\.middleware\.MessageMiddleware/d
    /django\.middleware\.csrf\.CsrfViewMiddleware/d
    /server\.libs\.spdb_shared\.api_contract\.request_id\.RequestIdMiddleware/d
  }" "$SETTINGS_FILE"

  grep -q 'shared\.api_contract\.request_id\.RequestIdMiddleware' "$SETTINGS_FILE" || \
  sed -i '/^MIDDLEWARE = \[/,/^]$/ {
    /^]$/i\    "shared.api_contract.request_id.RequestIdMiddleware",
  }' "$SETTINGS_FILE"

  sed -i "/'context_processors': \[/,/]/ {
    /django\.contrib\.auth\.context_processors\.auth/d
  }" "$SETTINGS_FILE"

  sed -i "/^DATABASES = {$/,/^}$/c\\
DATABASES = {\\
    \"default\": {\\
        \"ENGINE\": \"django.db.backends.postgresql\",\\
        \"NAME\": \"${DB_NAME}\",\\
        \"USER\": os.getenv(\"POSTGRES_USER\", \"spdb_app\"),\\
        \"PASSWORD\": os.getenv(\"POSTGRES_PASSWORD\", \"spdb\"),\\
        \"HOST\": os.getenv(\"POSTGRES_HOST\", \"postgres\"),\\
        \"PORT\": os.getenv(\"POSTGRES_PORT\", \"5432\"),\\
        \"CONN_MAX_AGE\": 60,\\
    }\\
}" "$SETTINGS_FILE"

  sed -i 's/^TIME_ZONE = .*/TIME_ZONE = "UTC"/' "$SETTINGS_FILE"
  sed -i 's/^USE_TZ = .*/USE_TZ = True/' "$SETTINGS_FILE"

  sed -i '/^# Password validation$/,/^\]$/d' "$SETTINGS_FILE"
  sed -i '/^AUTH_PASSWORD_VALIDATORS = \[$/,/^\]$/d' "$SETTINGS_FILE"
}

write_urls_file() {
  info "Writing urls.py"
  render_urls_py > "$URLS_FILE"
}

remove_default_tests() {
  info "Removing default tests.py"
  rm -f "$TESTS_FILE"
}

write_api_file() {
  info "Writing api.py"
  render_api_py > "$API_FILE"
}

patch_django_files() {
  patch_settings_file
  write_urls_file
  remove_default_tests
  write_api_file
}