#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be available at $DB_HOST:$DB_PORT..."

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; do
  sleep 2
done

echo "PostgreSQL is available, checking for table 'cars' in DB '$DB_NAME'..."

while ! PGPASSWORD=$DB_PASS psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "\dt cars" 2>/dev/null | grep -q "cars"; do
  echo "Table 'cars' not found yet, waiting..."
  sleep 2
done

echo "Table 'cars' found! Starting Scrapy..."

exec "$@"
