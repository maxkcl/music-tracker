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

WITH Scrobbles AS (
    SELECT 
        Song_FK,
        YEAR(DatetimePlayed) AS Y,
        MONTH(DatetimePlayed) AS M,
        COUNT(*) AS ScrobbleCount
    FROM tbl_Scrobble
    GROUP BY 
        Song_FK,
        YEAR(DatetimePlayed),
        MONTH(DatetimePlayed)
)

SELECT 
    B.Rank,
    ISNULL(SC.ScrobbleCount, 0) AS Plays,
    S.SongName,
    A.ArtistName,
    M.MonthDate,
    M.Year,
    M.Month,
    S.ID,
    A.ID

FROM tbl_Big16 B
JOIN tbl_Month M ON M.ID = B.Month_FK
JOIN tbl_Song S ON S.ID = B.Song_FK
JOIN tbl_Artist A ON A.ID = S.Artist_FK

LEFT JOIN Scrobbles SC
    ON SC.Song_FK = B.Song_FK
    AND SC.Y = M.Year
    AND SC.M = M.Month

ORDER BY M.MonthDate, B.Rank;

WITH Big16Agg AS (
        SELECT 
            Song_FK,
            SUM(Points) AS TotalPoints,
            COUNT(*) AS Appearances,
            COUNT(CASE WHEN Rank = 1 THEN 1 END) AS FirstPlaces,
            SUM(
                CASE
                    WHEN M.MonthDate >= DATEADD(day, -120, GETDATE())
                    THEN Points ELSE 0
                END
            ) AS RecentPoints
        FROM tbl_Big16
        LEFT JOIN tbl_Month M ON M.ID = Month_FK
        GROUP BY Song_FK
    ),
    ScrobbleAgg AS (
        SELECT 
            Song_FK,
            COUNT(*) AS TotalScrobbles,
            SUM(
                POWER(
                    0.5,
                    CAST(DATEDIFF(day, DatetimePlayed, GETDATE()) AS FLOAT) / 365.25
                )
            ) AS DecayedScrobbles,
            SUM(
                CASE
                    WHEN DatetimePlayed >= DATEADD(day, -60, GETDATE())
                    THEN 1 ELSE 0
                END
            ) AS RecentScrobbles
        FROM tbl_Scrobble
        GROUP BY Song_FK
    )
    SELECT
        s.ID,
        s.SongName,
        a.ArtistName,
        al.AlbumName,
        ISNULL(b.TotalPoints, 0) AS TotalPoints,
        ISNULL(b.Appearances, 0) AS Appearances,
        ISNULL(b.FirstPlaces, 0) AS FirstPlaces,
        ISNULL(b.RecentPoints, 0) AS RecentPoints,
        ISNULL(sc.TotalScrobbles, 0) AS TotalScrobbles,
        ISNULL(sc.DecayedScrobbles, 0) AS DecayedScrobbles,
        ISNULL(sc.RecentScrobbles, 0) AS RecentScrobbles
    FROM tbl_Song s
    LEFT JOIN Big16Agg b ON b.Song_FK = s.ID
    LEFT JOIN ScrobbleAgg sc ON sc.Song_FK = s.ID
    LEFT JOIN tbl_Artist a ON a.ID = s.Artist_FK
    LEFT JOIN tbl_Album al ON al.ID = s.Album_FK
ORDER BY DecayedScrobbles DESC;


SELECT * FROM tbl_SGVSnapshot
SELECT * FROM tbl_SGVSongs

WITH LatestSnapshot AS (
        SELECT MAX(ID) AS SnapshotID
        FROM tbl_SGVSnapshot
    )
    SELECT 
        s.SongName,
        a.ArtistName,
        r.Rating,
        r.TP,
        r.N1s,
        r.MIC,
        r.Plays,
        r.DecayedPlays
    FROM tbl_SGVSongs r
    JOIN LatestSnapshot ls ON r.Snapshot_FK = ls.SnapshotID
    JOIN tbl_Song s ON s.ID = r.Song_FK
    JOIN tbl_Artist a ON a.ID = s.Artist_FK
    WHERE r.N1s > 0






WITH MonthlyPlays AS (
    SELECT 
        YEAR(s.DatetimePlayed) AS yr,
        MONTH(s.DatetimePlayed) AS mn,
        so.Artist_FK,
        COUNT(*) AS Plays
    FROM tbl_Scrobble s
    JOIN tbl_Song so ON so.ID = s.Song_FK
    GROUP BY 
        YEAR(s.DatetimePlayed),
        MONTH(s.DatetimePlayed),
        so.Artist_FK
),

-- Rank artists per month
MonthlyRanks AS (
    SELECT
        yr,
        mn,
        Artist_FK,
        Plays,
        RANK() OVER (
            PARTITION BY yr, mn
            ORDER BY Plays DESC
        ) AS PlaysRank
    FROM MonthlyPlays
),

-- Top song per artist per month
TopSongs AS (
    SELECT *
    FROM (
        SELECT 
            YEAR(s.DatetimePlayed) AS yr,
            MONTH(s.DatetimePlayed) AS mn,
            so.Artist_FK,
            so.SongName,
            COUNT(*) AS SongPlays,
            ROW_NUMBER() OVER (
                PARTITION BY YEAR(s.DatetimePlayed), MONTH(s.DatetimePlayed), so.Artist_FK
                ORDER BY COUNT(*) DESC
            ) AS rn
        FROM tbl_Scrobble s
        JOIN tbl_Song so ON so.ID = s.Song_FK
        GROUP BY 
            YEAR(s.DatetimePlayed),
            MONTH(s.DatetimePlayed),
            so.Artist_FK,
            so.SongName
    ) t
    WHERE rn = 1
),

-- Big16 songs per artist per month
Big16Agg AS (
    SELECT 
        m.Year AS yr,
        m.Month AS mn,
        so.Artist_FK,
        COUNT(*) AS Top16Count,
        STRING_AGG(
            so.SongName + ' (' + CAST(b.Rank AS VARCHAR) + ')',
            ', '
        ) AS Top16Songs
    FROM tbl_Big16 b
    JOIN tbl_Song so ON so.ID = b.Song_FK
    JOIN tbl_Month m ON m.ID = b.Month_FK
    GROUP BY 
        m.Year,
        m.Month,
        so.Artist_FK
)

SELECT 
    m.Year,
    m.Month,

    ISNULL(r.PlaysRank, NULL) AS PlaysRank,
    ISNULL(r.Plays, 0) AS Plays,

    ts.SongName AS TopSong,
    ts.SongPlays AS TopSongPlays,

    ISNULL(b.Top16Count, 0) AS Top16Count,
    ISNULL(b.Top16Songs, '') AS Top16Songs

FROM tbl_Month m

LEFT JOIN MonthlyRanks r
    ON r.yr = m.Year 
    AND r.mn = m.Month
    AND r.Artist_FK = ?

LEFT JOIN TopSongs ts
    ON ts.yr = m.Year 
    AND ts.mn = m.Month
    AND ts.Artist_FK = ?

LEFT JOIN Big16Agg b
    ON b.yr = m.Year 
    AND b.mn = m.Month
    AND b.Artist_FK = ?

ORDER BY m.Year, m.Month