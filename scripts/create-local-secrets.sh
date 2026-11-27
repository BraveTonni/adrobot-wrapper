#!/usr/bin/env sh
# Создаёт локальные .env и секреты для Docker Compose.
#
# Существующие файлы не перезаписываются, поэтому команду безопасно
# повторять. Ключ Keitaro сервис получить не может: его вводят вручную.
set -eu

cd "$(dirname "$0")/.."
umask 077

SECRETS=backend/.secrets
mkdir -p "$SECRETS"
chmod 700 "$SECRETS" 2>/dev/null || true
[ -f .env ] || cp .env.example .env

# openssl в некоторых окружениях добавляет перевод строки; в секретах
# и в URL базы его быть не должно.
random() {
  openssl rand -hex 32 | tr -d '\r\n'
}

keep_or_create() {
  [ -f "$1" ] || printf '%s' "$2" > "$1"
}

keep_or_create "$SECRETS/keitaro_api_key" "replace-with-keitaro-api-key"
keep_or_create "$SECRETS/api_access_token" "$(random)"
keep_or_create "$SECRETS/frontend_auth_password" "$(random)"

if [ ! -f "$SECRETS/postgres_password" ] ||
  [ ! -f "$SECRETS/database_url" ]; then
  keep_or_create "$SECRETS/postgres_password" "$(random)"
  printf 'postgresql+asyncpg://adrobot:%s@db:5432/adrobot' \
    "$(tr -d '\r\n' < "$SECRETS/postgres_password")" \
    > "$SECRETS/database_url"
fi

chmod 600 .env "$SECRETS"/* 2>/dev/null || true

if grep -q "replace-with-keitaro-api-key" "$SECRETS/keitaro_api_key"; then
  echo "Укажите ключ Keitaro в $SECRETS/keitaro_api_key, затем запустите make run."
else
  echo "Секреты готовы. Запуск: make run."
fi
