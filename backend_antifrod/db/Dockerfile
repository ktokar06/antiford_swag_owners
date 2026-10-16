FROM postgres:16-alpine

# Данные в слое контейнера, не в VOLUME базового образа.
ENV PGDATA=/var/lib/postgresql/local-data
COPY 001_schema.sql 002_reference.sql /docker-entrypoint-initdb.d/
