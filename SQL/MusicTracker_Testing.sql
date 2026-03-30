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
WHERE So.SongName = 'Distance'
SELECT * FROM tbl_Artist
SELECT * FROM tbl_Album
SELECT * FROM tbl_Song
SELECT * FROM tbl_NameFixes
SELECT * FROM tbl_Day
ORDER BY DayDate DESC

DELETE FROM tbl_NameFixes

INSERT INTO tbl_NameFixes (Type, OldName, NewName, ArtistContext) VALUES
('song','Not Who I Used to Be (feat. Joey Fleming)','Not Who I Used to Be','Boys of Fall'),
('song','Think it over','Think It Over','Mammoth'),
('artist','Chyl','CHYL',NULL)


SELECT MAX(DatetimePlayed) FROM tbl_Scrobble

SELECT * FROM tbl_Scrobble S
LEFT JOIN tbl_Song So ON So.ID = S.Song_FK
LEFT JOIN tbl_Artist A ON A.ID = So.Artist_FK
WHERE ArtistName = 'Seven Lions' AND SongName LIKE 'Another Way%'

SELECT ID FROM tbl_Song
WHERE SongName COLLATE Latin1_General_CS_AS = 'Not Who I Used to Be'
AND Artist_FK = 59
AND ID != 1650

