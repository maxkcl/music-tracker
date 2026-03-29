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

--DELETE FROM tbl_Scrobble
--DELETE FROM tbl_Song
--DELETE FROM tbl_Album
--DELETE FROM tbl_Artist

SELECT * FROM tbl_Scrobble
SELECT * FROM tbl_Artist
SELECT * FROM tbl_Album
SELECT * FROM tbl_Song
SELECT * FROM tbl_NameFixes