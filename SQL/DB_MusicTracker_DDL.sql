/*
ScriptName: DB_MusicTracker_DDL
Coder: Max
Date: 2026-03-27

vers     Date        Coder       Issue
1.0      2026-03-27  Max         Initial
1.1      2026-03-28  Max         Photos
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
