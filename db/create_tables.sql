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
    mineObstructedDistances INT[] NOT NULL
);

DROP TABLE IF EXISTS Mines CASCADE;
CREATE TABLE Mines(
    id SERIAL PRIMARY KEY,
    gameId VARCHAR(8) NOT NULL REFERENCES Games,
    turnId INT NOT NULL REFERENCES Turns(id),
    mineNumber INT NOT NULL,
    pos INT[] NOT NULL,
    heroId INT REFERENCES Heroes
);

COMMIT;











