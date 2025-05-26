#!/bin/sh

echo "entering database as dev"

docker exec -it server_db_1 psql -U dev -d db