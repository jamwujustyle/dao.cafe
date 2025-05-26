#!/bin/sh
echo "deleting data from psql tables inside docker"

if ! docker ps > /dev/null 2>&1; then
    echo "error: docker is not running"
    exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -q '^server_db_1$'; then
    echo "error: container 'server_db_1' not found!"
    exit 1
fi



SQL_COMMANDS=$(cat <<EOF
DELETE FROM dao_dao;
DELETE FROM forum_thread;
DELETE FROM dao_contract;
DELETE FROM dao_stake;
DELETE FROM forum_dip;
DELETE FROM forum_vote;
SELECT setval('dao_dao_id_seq', 1, false);
SELECT setval('dao_contract_id_seq', 1, false);
SELECT setval('dao_stake_id_seq', 1, false);
SELECT setval('forum_dip_id_seq', 1, false);
SELECT setval('forum_vote_id_seq', 1, false);
EOF
)

echo "running sql command"
echo "$SQL_COMMANDS"

RESULT=$(docker exec server_db_1 psql -U dev -d db -c "$SQL_COMMANDS" 2>&1)

if [ $? -eq 0 ]; then
    echo "database cleanup successful"
    echo "docker exec output: $RESULT"
else
    echo "error: failed to reset database"
    echo "docker exec output $RESULT"
    exit 1
fi