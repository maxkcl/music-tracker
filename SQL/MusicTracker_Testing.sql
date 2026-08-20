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
SELECT * FROM tbl_Big16
ORDER BY Month_FK, Rank

SELECT * FROM tbl_Scrobble
ORDER BY ID DESC

SELECT 
        s.ID,
        s.SongName,
        r.Rating,
        r.Plays,
        r.TP,
        r.N1s,
        r.MIC
    FROM tbl_Song s
    LEFT JOIN tbl_SGVSongs r 
        ON r.Song_FK = s.ID
    WHERE s.Artist_FK = ?
    AND r.Snapshot_FK = (
        SELECT MAX(ID) FROM tbl_SGVSnapshot
    )
    ORDER BY r.Rating DESC

SELECT * FROM tbl_Song
ORDER BY ID DESC

SELECT TOP 1 ID FROM tbl_Song
WHERE Artist_FK = 544
AND SongName = 'Waking Up'

SELECT * FROM tbl_SGVSongs SGV
LEFT JOIN tbl_Song S ON S.ID = SGV.Song_FK
LEFT JOIN tbl_Artist A ON A.ID = S.Artist_FK
WHERE A.ArtistName = 'ODESZA'
AND S.SongName = 'Line of Sight'

SELECT * FROM tbl_SGVSnapshot
SELECT * FROM tbl_SGVSongs WHERE Snapshot_FK = 11



SET NOCOUNT ON;

    WITH MonthlyPlays AS (
        SELECT 
            YEAR(DatetimePlayed) AS yr,
            MONTH(DatetimePlayed) AS mn,
            COUNT(*) AS Plays
        FROM tbl_Scrobble
        WHERE Song_FK = 158
        GROUP BY YEAR(DatetimePlayed), MONTH(DatetimePlayed)
    ),

    RankedSongs AS (
        SELECT 
            YEAR(s.DatetimePlayed) AS yr,
            MONTH(s.DatetimePlayed) AS mn,
            s.Song_FK,
            COUNT(*) AS Plays,
            RANK() OVER (
                PARTITION BY YEAR(s.DatetimePlayed), MONTH(s.DatetimePlayed)
                ORDER BY COUNT(*) DESC
            ) AS PlaysRank
        FROM tbl_Scrobble s
        GROUP BY 
            YEAR(s.DatetimePlayed), 
            MONTH(s.DatetimePlayed), 
            s.Song_FK
    ),

    MonthlyRanks AS (
        SELECT *
        FROM RankedSongs
        WHERE Song_FK = 158
    ),

    Big16 AS (
        SELECT 
            m.Year AS yr,
            m.Month AS mn,
            b.Rank AS Big16Rank
        FROM tbl_Big16 b
        JOIN tbl_Month m ON m.ID = b.Month_FK
        WHERE b.Song_FK = 158
    )

    SELECT 
        m.Year,
        m.Month,
        mp.Plays,
        mr.PlaysRank,
        b.Big16Rank,
        CASE 
            WHEN Big16Rank = 1 THEN 1
            ELSE 0
        END AS IsN1
        
    FROM tbl_Month m
    LEFT JOIN MonthlyPlays mp 
        ON mp.yr = m.Year AND mp.mn = m.Month
    LEFT JOIN MonthlyRanks mr 
        ON mr.yr = m.Year AND mr.mn = m.Month
    LEFT JOIN Big16 b
        ON b.yr = m.Year AND b.mn = m.Month
    ORDER BY m.Year, m.Month

SELECT * FROM tbl_Song S
LEFT JOIN tbl_Artist A ON A.ID = S.Artist_FK
LEFT JOIN tbl_Album Al ON Al.ID = S.Album_FK
WHERE SongName = 'Anywhere'

SELECT * FROM tbl_RedirectSong RS
LEFT JOIN tbl_Song S ON S.ID = RS.Redirect_FK
WHERE SongName = 'Anywhere'

SELECT * FROM tbl_RedirectAlbum

SELECT A.AlbumName
FROM tbl_RedirectAlbum RA
JOIN tbl_Album A ON A.ID = RA.Redirect_FK
WHERE RA.OldName = 'Rain City Drive (Deluxe Edition)'
AND RA.SongName = 'Waiting On You'
AND (RA.Artist_FK IS NULL OR RA.Artist_FK = 547)

SELECT * FROM tbl_Song
WHERE Artist_FK = 25

SELECT S.ID, SongName, Artist_FK, ArtistName
FROM tbl_Song S
LEFT JOIN tbl_Artist A ON A.ID = S.Artist_FK
WHERE SongName LIKE '%?%';

SELECT Sc.*, Artist_FK FROM tbl_Scrobble Sc
LEFT JOIN tbl_Song S ON S.ID = Sc.Song_FK
LEFT JOIN tbl_Artist A ON A.ID = S.Artist_FK
WHERE Song_FK = 9790

SELECT * FROM tbl_SGVSnapshot
SELECT * FROM tbl_SGVSongs