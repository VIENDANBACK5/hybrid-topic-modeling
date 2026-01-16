#!/bin/bash
set -e

# Force timezone to Asia/Ho_Chi_Minh for all connections
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    ALTER DATABASE "$POSTGRES_DB" SET timezone = 'Asia/Ho_Chi_Minh';
    ALTER SYSTEM SET timezone = 'Asia/Ho_Chi_Minh';
EOSQL

# Set for template databases
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "template1" <<-EOSQL
    ALTER DATABASE template1 SET timezone = 'Asia/Ho_Chi_Minh';
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    ALTER DATABASE postgres SET timezone = 'Asia/Ho_Chi_Minh';
EOSQL
