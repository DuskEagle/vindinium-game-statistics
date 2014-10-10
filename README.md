Vindinium is an Artificial Intelligence programming challenge. You have to take
control of a legendary hero using the programming language of your choice. 
You will fight with other AI for a predetermined number of turns and the hero 
with the greatest amount of gold will win. For more information, see 
[vindinium.org](vindinium.org).

vindinium-game-statistics aims to collect and store Vindinium games in an 
easy-to-query SQL format. For example, using the table schema in this project 
you should be able to craft a query to determine the average lifespan of a hero, 
or the average number of turns a mine is owned for, or how often heroes with 
less than twenty health with no other hero within 3 spaces of them end up dying.

Running this project requires Python 3, pip, PostgreSQL (with development
headers), and a PostgreSQL server installed and running on your system.

To install the necessary Python 3 libraries:

    sudo pip3 install -r REQUIREMENTS.txt

To set up the database schema:

    sudo -u postgres psql

In the shell that opens up, type the following commands:

    CREATE DATABASE vindinium;
    CREATE USER "<your-system-username>";
    GRANT ALL PRIVELEGES ON DATABASE vindinium TO "<your-system-username>";
    CREATE EXTENSION intarray;

Exit the psql shell, then run

    psql -d vindinium -f create_tables.sql

This creates all of the tables needed for the project.

To start streaming games from the Vindinium server to your Postgres database,

    python3 StreamInserter.py vindinium <your-system-username> {optional alternate server url} {optional log level}

Optional log level can be one of "debug", "info", "warn", "error", or "critical".