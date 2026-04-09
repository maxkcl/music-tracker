/*
ScriptName: DB_MusicTracker_DML
Coder: Max
Date: 2026-03-29

vers     Date        Coder       Issue
1.0      2026-03-29  Max         Initial
1.1      2026-03-30  Max         tbl_Day fix
*/

USE DB_MusicTracker
GO

-- Break in case of fire
--DROP TABLE tbl_Day
--CREATE TABLE tbl_Day
--(
--    DayDate DATE PRIMARY KEY,
--    NumPlays INT DEFAULT 0,
--    TopSong_FK INT REFERENCES tbl_Song(ID),
--    TopSongPlays INT DEFAULT 0,
--    TopArtist_FK INT REFERENCES tbl_Artist(ID),
--    TopArtistPlays INT DEFAULT 0
--);
--WITH AllDays AS (
--    SELECT CAST('2020-12-03' AS DATE) As DayDate
--    UNION ALL
--    SELECT DATEADD(DAY, 1, DayDate)
--    FROM AllDays
--    WHERE DayDate < CAST(GETDATE() AS DATE)
--)
--INSERT INTO tbl_Day (DayDate)
--SELECT DayDate
--FROM AllDays
--OPTION (MAXRECURSION 0);

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
        so.ID,
        COUNT(*) AS Plays,
        ROW_NUMBER() OVER (PARTITION BY CAST(s.DatetimePlayed AS DATE) ORDER BY COUNT(*) DESC) AS rn
    FROM tbl_Scrobble s
    JOIN tbl_Song so ON s.Song_FK = so.ID
    GROUP BY CAST(s.DatetimePlayed AS DATE), so.ID
)
UPDATE d
SET d.TopSong_FK = sr.ID,
    d.TopSongPlays = sr.Plays
FROM tbl_Day d
JOIN SongRank sr ON d.DayDate = sr.DayDate AND sr.rn = 1;

-- Top artist per day
WITH ArtistRank AS (
    SELECT 
        CAST(s.DatetimePlayed AS DATE) AS DayDate,
        a.ID,
        COUNT(*) AS Plays,
        ROW_NUMBER() OVER (PARTITION BY CAST(s.DatetimePlayed AS DATE) ORDER BY COUNT(*) DESC) AS rn
    FROM tbl_Scrobble s
    JOIN tbl_Song so ON s.Song_FK = so.ID
    JOIN tbl_Artist a ON so.Artist_FK = a.ID
    GROUP BY CAST(s.DatetimePlayed AS DATE), a.ID
)
UPDATE d
SET d.TopArtist_FK = ar.ID,
    d.TopArtistPlays = ar.Plays
FROM tbl_Day d
JOIN ArtistRank ar ON d.DayDate = ar.DayDate AND ar.rn = 1;

-- Insert tbl_Month
--DECLARE @StartDate DATE = '2016-06-01';
--DECLARE @EndDate   DATE = '2026-03-01';

--WHILE @StartDate <= @EndDate
--BEGIN
--    INSERT INTO tbl_Month (MonthDate, Year, Month)
--    VALUES (
--        @StartDate,
--        YEAR(@StartDate),
--        MONTH(@StartDate)
--    );

--    SET @StartDate = DATEADD(MONTH, 1, @StartDate);
--END;
--SELECT * FROM tbl_Month

-- Big 16 Artist Backfill
INSERT INTO tbl_Artist (ArtistName, ImageURL)
VALUES
('SCNDL', NULL),
('Aero Chord', NULL),
('Hot Date!', NULL),
('KIDS SEE GHOSTS', NULL)

SELECT * FROM tbl_Album A
LEFT JOIN tbl_Artist Ar ON Ar.ID = A.Artist_FK
WHERE Ar.ArtistName = 'Stonebank'

INSERT INTO tbl_Song ()
VALUES