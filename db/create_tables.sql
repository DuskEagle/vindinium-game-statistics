BEGIN;

DROP TABLE IF EXISTS Games CASCADE;
CREATE TABLE Games (
    gameId VARCHAR(8) PRIMARY KEY,
    time TIMESTAMP,
    size INT NOT NULL,
    mineCount INT NOT NULL,
    finished BOOLEAN NOT NULL
);

DROP TABLE IF EXISTS Bots CASCADE;
CREATE TABLE Bots(
    userId VARCHAR(8) PRIMARY KEY,
    name VARCHAR(20) UNIQUE NOT NULL,
    elo INT NOT NULL
);

DROP TABLE IF EXISTS HistoricalBots CASCADE;
CREATE TABLE HistoricalBots(
    id SERIAL PRIMARY KEY,
    userId VARCHAR(8) NOT NULL REFERENCES Bots,
    lastGameId VARCHAR(8) REFERENCES Games(gameId),
    elo INT NOT NULL,
    previousHistoricalBotId INT REFERENCES HistoricalBots(id)
);

DROP TABLE IF EXISTS Turns CASCADE;
CREATE TABLE Turns (
    id SERIAL PRIMARY KEY,
    gameId VARCHAR(8) NOT NULL REFERENCES Games,
    turn INT NOT NULL,
    rawJSON JSON NOT NULL,
    previousTurnId INT REFERENCES Turns(id),
    UNIQUE (gameId, turn)
);

DROP TYPE IF EXISTS dir CASCADE;
CREATE TYPE dir AS ENUM('North', 'South', 'East', 'West', 'Stay');

DROP TABLE IF EXISTS Heroes CASCADE;
CREATE TABLE Heroes(
    id SERIAL PRIMARY KEY,
    userId VARCHAR(8) NOT NULL REFERENCES Bots,
    gameId VARCHAR(8) NOT NULL REFERENCES Games,
    turnId INT NOT NULL REFERENCES Turns(id),
    inGameId INT NOT NULL,
    life INT NOT NULL, 
    gold INT NOT NULL,
    mineCount INT NOT NULL,
    died BOOLEAN NOT NULL,
    pos INT[] NOT NULL,
    spawnPos INT[] NOT NULL,
    lastDir dir,
    crashed boolean NOT NULL,
    heroDistances INT[] NOT NULL,
    heroObstructedDistances INT[] NOT NULL,
    tavernDistances INT[] NOT NULL,
    tavernObstructedDistances INT[] NOT NULL,
    mineDistances INT[] NOT NULL,
    mineObstructedDistances INT[] NOT NULL,
    previousHeroId INT REFERENCES HEROES(id)
);

DROP TABLE IF EXISTS Mines CASCADE;
CREATE TABLE Mines(
    id SERIAL PRIMARY KEY,
    gameId VARCHAR(8) NOT NULL REFERENCES Games,
    turnId INT NOT NULL REFERENCES Turns(id),
    mineNumber INT NOT NULL,
    pos INT[] NOT NULL,
    heroId INT REFERENCES Heroes,
    previousMineId INT REFERENCES Mines(id)
);

---CREATE FUNCTION INSERT_IF_UNIQUE (sql_insert TEXT)
---    RETURNS VOID
---    LANGUAGE plpgsql
---AS $$
---BEGIN
---    EXECUTE sql_insert;
---    RETURN;
---    EXCEPTION WHEN unique_violation THEN
---    RETURN;
---END;
---$$;

---DROP FUNCTION MINIMUM;
---CREATE FUNCTION MINIMUM(anyarray)
---    returns anyelement as $$
---    select min($1[i]) from generate_series(array_lower($1,1),
---    array_upper($1,1)) g(i);
---    $$ language sql immutable strict;
    
---DROP FUNCTION IF EXISTS MINIMUM_AMONG_INDICES;
---CREATE FUNCTION MINIMUM_AMONG_INDICES(anyarray)
---    returns anyelement as $$
---    select min($1[i]) from generate_series(array_lower($1,1),
---    array_upper($1,1)) g(i);
---
---$$ LANGUAGE plpgsql STABLE;
    
COMMIT;











