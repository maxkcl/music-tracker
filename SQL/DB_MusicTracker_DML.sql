/*
ScriptName: DB_MusicTracker_DML
Coder: Max
Date: 2026-03-29

vers     Date        Coder       Issue
1.0      2026-03-29  Max         Initial
*/

USE DB_MusicTracker
GO

WITH AllDays AS (
    SELECT CAST('2020-12-03' AS DATE) As DayDate
    UNION ALL
    SELECT DATEADD(DAY, 1, DayDate)
    FROM AllDays
    WHERE DayDate < CAST(GETDATE() AS DATE)
)
INSERT INTO tbl_Day (DayDate)
SELECT DayDate
FROM AllDays
OPTION (MAXRECURSION 0);

-- Total plays per day
UPDATE d
SET d.NumPlays = s.PlayCount
FROM tbl_Day d
JOIN (
    SELECT CAST(DatetimePlayed AS DATE) AS DayDate, COUNT(*) AS PlayCount
    FROM tbl_Scrobble
    GROUP BY CAST(DatetimePlayed AS DATE)
) s ON d.DayDate = s.DayDate;

-- Top song per day
WITH SongRank AS (
    SELECT 
        CAST(s.DatetimePlayed AS DATE) AS DayDate,
        so.SongName,
        COUNT(*) AS Plays,
        ROW_NUMBER() OVER (PARTITION BY CAST(s.DatetimePlayed AS DATE) ORDER BY COUNT(*) DESC) AS rn
    FROM tbl_Scrobble s
    JOIN tbl_Song so ON s.Song_FK = so.ID
    GROUP BY CAST(s.DatetimePlayed AS DATE), so.SongName
)
UPDATE d
SET d.TopSong = sr.SongName,
    d.TopSongPlays = sr.Plays
FROM tbl_Day d
JOIN SongRank sr ON d.DayDate = sr.DayDate AND sr.rn = 1;

-- Top artist per day
WITH ArtistRank AS (
    SELECT 
        CAST(s.DatetimePlayed AS DATE) AS DayDate,
        a.ArtistName,
        COUNT(*) AS Plays,
        ROW_NUMBER() OVER (PARTITION BY CAST(s.DatetimePlayed AS DATE) ORDER BY COUNT(*) DESC) AS rn
    FROM tbl_Scrobble s
    JOIN tbl_Song so ON s.Song_FK = so.ID
    JOIN tbl_Artist a ON so.Artist_FK = a.ID
    GROUP BY CAST(s.DatetimePlayed AS DATE), a.ArtistName
)
UPDATE d
SET d.TopArtist = ar.ArtistName,
    d.TopArtistPlays = ar.Plays
FROM tbl_Day d
JOIN ArtistRank ar ON d.DayDate = ar.DayDate AND ar.rn = 1;