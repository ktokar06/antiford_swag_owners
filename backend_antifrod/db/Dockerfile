FROM postgres:16-alpine

ENV PGDATA=/var/lib/postgresql/local-data
COPY 001_schema.sql 002_reference.sql /docker-entrypoint-initdb.d/
