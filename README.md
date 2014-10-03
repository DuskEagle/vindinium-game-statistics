This README is a WIP.

To set up the database schema:
        sudo -u postgres psql

In the shell that opens up, type the following commands:
        # CREATE DATABASE vindinium
        # CREATE USER <your-unix-username>
        # GRANT ALL PRIVELEGES ON DATABASE vindinium TO <your-unix-username>
        # CREATE EXTENSION intarray

Exit the psql shell, then run
	psql -d vindinium -f create_tables.sql
This creates all of the tables needed for the project.
