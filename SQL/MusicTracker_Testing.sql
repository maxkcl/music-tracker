USE DB_MusicTracker
GO

SELECT * FROM tbl_Scrobble S
LEFT JOIN tbl_Song So ON So.ID = S.Song_FK
LEFT JOIN tbl_Artist A ON A.ID = So.Artist_FK
ORDER BY DatetimePlayed DESC

SELECT Song_FK, SongName, COUNT(*) AS Plays FROM tbl_Scrobble S
LEFT JOIN tbl_Song So ON S.Song_FK = So.ID
GROUP BY Song_FK, SongName
ORDER BY Plays DESC

SELECT * FROM tbl_Song S
LEFT JOIN tbl_Artist A ON A.ID = S.Artist_FK
WHERE A.ArtistName = 'Mammoth'
ORDER BY SongName

--DELETE FROM tbl_Scrobble
--DELETE FROM tbl_Song
--DELETE FROM tbl_Album
--DELETE FROM tbl_Artist

SELECT * FROM tbl_Scrobble S
LEFT JOIN tbl_Song So ON So.ID = S.Song_FK
ORDER BY DatetimePlayed DESC
SELECT * FROM tbl_Artist
SELECT * FROM tbl_Album
SELECT * FROM tbl_Song
SELECT * FROM tbl_NameFixes
SELECT * FROM tbl_RedirectSong
SELECT * FROM tbl_RedirectArtist
SELECT D.*, S.SongName, A.ArtistName FROM tbl_Day D
LEFT JOIN tbl_Song S ON S.ID = D.TopSong_FK
LEFT JOIN tbl_Artist A ON A.ID = D.TopArtist_FK
ORDER BY DayDate DESC

--DELETE FROM tbl_NameFixes

SELECT MAX(DatetimePlayed) FROM tbl_Scrobble

SELECT * FROM tbl_Scrobble S
LEFT JOIN tbl_Song So ON So.ID = S.Song_FK
LEFT JOIN tbl_Artist A ON A.ID = So.Artist_FK
WHERE ArtistName = 'Seven Lions' AND SongName LIKE 'Another Way%'

SELECT ID FROM tbl_Song
WHERE SongName COLLATE Latin1_General_CS_AS = 'Not Who I Used to Be'
AND Artist_FK = 59
AND ID != 1650

SELECT DayDate, NumPlays, S.SongName, TopSongPlays, A.ArtistName, TopArtistPlays FROM tbl_Day D
LEFT JOIN tbl_Song S ON S.ID = D.TopSong_FK
LEFT JOIN tbl_Artist A ON A.ID = D.TopArtist_FK
ORDER BY TopArtistPlays DESC

SELECT TOP 50 COUNT(DatetimePlayed) AS [Total Plays], ArtistName AS [Name] FROM tbl_Scrobble S
LEFT JOIN tbl_Song So ON So.ID = S.Song_FK
LEFT JOIN tbl_Artist A ON A.ID = So.Artist_FK
WHERE MONTH(DatetimePlayed) = 12 AND YEAR(DatetimePlayed) = 2020
GROUP BY Artist_FK, ArtistName
ORDER BY [Total Plays] DESC

WITH MonthlyRanks AS (
    SELECT 
        YEAR(s.DatetimePlayed) AS yr,
        MONTH(s.DatetimePlayed) AS mn,
        a.ArtistName AS artist,
        COUNT(*) AS plays,
        ROW_NUMBER() OVER (
            PARTITION BY YEAR(s.DatetimePlayed), MONTH(s.DatetimePlayed)
            ORDER BY COUNT(*) DESC
        ) AS rn
    FROM tbl_Scrobble s
    JOIN tbl_Song so ON so.ID = s.Song_FK
    JOIN tbl_Artist a ON a.ID = so.Artist_FK
    WHERE s.DatetimePlayed >= '2020-12-01'
    GROUP BY 
        YEAR(s.DatetimePlayed),
        MONTH(s.DatetimePlayed),
        a.ArtistName
)

SELECT *
FROM MonthlyRanks
WHERE rn <= 50
ORDER BY yr, mn, plays DESC;

SELECT * FROM tbl_Song
WHERE SongName LIKE 'Three Cheers For Five Years'

SELECT S.* FROM tbl_Scrobble S
LEFT JOIN tbl_Song So ON So.ID = S.Song_FK
WHERE So.SongName LIKE 'Three Cheers For Five Years'

SELECT OldName, A.ID FROM tbl_NameFixes N
LEFT JOIN tbl_Artist A ON A.ArtistName = N.NewName
WHERE A.ID IS NOT NULL

--INSERT INTO tbl_RedirectArtist (OldName, Redirect_FK)
--SELECT OldName, A.ID FROM tbl_NameFixes N
--LEFT JOIN tbl_Artist A ON A.ArtistName = N.NewName
--WHERE A.ID IS NOT NULL

--INSERT INTO tbl_RedirectSong (OldName, Artist_FK, Redirect_FK)
--SELECT OldName, N.Artist_FK, S.ID FROM tbl_NameFixes N
--LEFT JOIN tbl_Song S ON S.SongName = N.NewName AND S.Artist_FK = N.Artist_FK
--WHERE Type = 'song'

SELECT * FROM tbl_Song
WHERE SongName = 'Safe & Sound'
AND Artist_FK = 104
AND ID != 1529

SELECT * FROM tbl_Scrobble S
LEFT JOIN tbl_Song So ON So.ID = S.Song_FK
WHERE So.SongName = 'OK'

SELECT * FROM tbl_Song
WHERE SongName LIKE 'One Two Things%'

SELECT * FROM tbl_Day
WHERE TopSong_FK = 744

--DELETE FROM tbl_Big16
--SELECT * FROM tbl_Big16
--ORDER BY Month_FK, Rank

SELECT * FROM tbl_Song
ORDER BY ID DESC

SELECT TOP 1 ID FROM tbl_Song
WHERE Artist_FK = 544
AND SongName = 'Waking Up'