/*
ScriptName: DB_MusicTracker_DDL
Coder: Max
Date: 2026-03-27

vers     Date        Coder       Issue
1.0      2026-03-27  Max         Initial
1.1      2026-03-28  Max         Photos
1.2      2026-03-29  Max         Name Fix
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
    ArtistContext NVARCHAR(255) NULL  -- only used for songs
);

CREATE TABLE tbl_Day
(
    DayDate DATE PRIMARY KEY,
    NumPlays INT DEFAULT 0,
    TopSong NVARCHAR(255) NULL,
    TopSongPlays INT DEFAULT 0,
    TopArtist NVARCHAR(255) NULL,
    TopArtistPlays INT DEFAULT 0
);