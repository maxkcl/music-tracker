/*
ScriptName: DB_MusicTracker_DDL
Coder: Max
Date: 2026-03-27

vers     Date        Coder       Issue
1.0      2026-03-27  Max         Initial
1.1      2026-03-28  Max         Photos
1.2      2026-03-29  Max         Name Fix
1.3      2026-03-31  Max         Name Fix Fix
1.4      2026-04-22  Max         SGV Song Rating Table
*/

USE master
GO
IF EXISTS(SELECT * FROM sys.databases WHERE name='DB_MusicTracker')
DROP DATABASE DB_MusicTracker

CREATE DATABASE DB_MusicTracker
GO
USE DB_MusicTracker

CREATE TABLE tbl_Artist
(
ID INT IDENTITY(1,1) PRIMARY KEY,
ArtistName VARCHAR(255),
ImageURL VARCHAR(500)
)

CREATE TABLE tbl_Album
(
ID INT IDENTITY(1,1) PRIMARY KEY,
AlbumName VARCHAR(255),
ImageURL VARCHAR(500),
Artist_FK INT REFERENCES tbl_Artist(ID)
UNIQUE(AlbumName, Artist_FK)
)

CREATE TABLE tbl_Song
(
ID INT IDENTITY(1,1) PRIMARY KEY,
SongName VARCHAR(255),
Artist_FK INT REFERENCES tbl_Artist(ID),
Album_FK INT REFERENCES tbl_Album(ID),
UNIQUE(SongName, Artist_FK, Album_FK)
)

CREATE TABLE tbl_Scrobble
(
ID INT IDENTITY(1,1) PRIMARY KEY,
Song_FK INT REFERENCES tbl_Song(ID),
DatetimePlayed DATETIME2,
UNIQUE(Song_FK, DatetimePlayed)
)

CREATE TABLE tbl_NameFixes (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    Type NVARCHAR(20),        -- 'artist' or 'song'
    OldName NVARCHAR(255),
    NewName NVARCHAR(255),
    Artist_FK INT REFERENCES tbl_Artist(ID) NULL  -- only used for songs
);

CREATE TABLE tbl_Day
(
    DayDate DATE PRIMARY KEY,
    NumPlays INT DEFAULT 0,
    TopSong_FK INT REFERENCES tbl_Song(ID),
    TopSongPlays INT DEFAULT 0,
    TopArtist_FK INT REFERENCES tbl_Artist(ID),
    TopArtistPlays INT DEFAULT 0
);

CREATE TABLE tbl_RedirectArtist (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    OldName NVARCHAR(255),
    Redirect_FK INT REFERENCES tbl_Artist(ID)
);

CREATE TABLE tbl_RedirectSong (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    OldName NVARCHAR(255),
    Artist_FK INT REFERENCES tbl_Artist(ID),
    Redirect_FK INT REFERENCES tbl_Song(ID)
);
DROP TABLE tbl_RedirectAlbum
CREATE TABLE tbl_RedirectAlbum (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    OldName NVARCHAR(255),
    Artist_FK INT REFERENCES tbl_Artist(ID),
    SongName NVARCHAR(255),
    Redirect_FK INT REFERENCES tbl_Album(ID)
);

CREATE TABLE tbl_Month (
    ID INT IDENTITY PRIMARY KEY,
    MonthDate DATE NOT NULL,  -- e.g. 2024-01-01
    Year INT NOT NULL,
    Month INT NOT NULL,
    UNIQUE (Year, Month)
);

CREATE TABLE tbl_Big16 (
    ID INT IDENTITY PRIMARY KEY,
    Month_FK INT NOT NULL,
    Song_FK INT NOT NULL,
    Rank INT NOT NULL CHECK (Rank BETWEEN 1 AND 16),
    Points INT NOT NULL,

    FOREIGN KEY (Month_FK) REFERENCES tbl_Month(ID),
    FOREIGN KEY (Song_FK) REFERENCES tbl_Song(ID),

    UNIQUE (Month_FK, Rank),      -- only one song per rank
    UNIQUE (Month_FK, Song_FK)    -- no duplicates per month
);

DROP TABLE tbl_SGVSongs
DROP TABLE tbl_SGVSnapshot
CREATE TABLE tbl_SGVSnapshot (
    ID INT IDENTITY PRIMARY KEY,
    CreatedAt DATETIME DEFAULT GETDATE()
);

CREATE TABLE tbl_SGVSongs (
    ID INT IDENTITY PRIMARY KEY,
    Snapshot_FK INT NOT NULL,
    Song_FK INT NOT NULL,
    Rating INT NOT NULL,
    
    TP INT NOT NULL,
    N1s INT NOT NULL,
    MIC INT NOT NULL,
    Plays INT NOT NULL,
    DecayedPlays INT NOT NULL,

    BaseRating FLOAT,
    LegacyScore FLOAT,
    RecencyScore FLOAT,

    SnapshotDate DATETIME DEFAULT GETDATE(),

    FOREIGN KEY (Snapshot_FK) REFERENCES tbl_SGVSnapshot(ID),
    FOREIGN KEY (Song_FK) REFERENCES tbl_Song(ID)
);