USE DB_MusicTracker
GO

SELECT * FROM tbl_Scrobble S
LEFT JOIN tbl_Song So ON So.ID = S.Song_FK
LEFT JOIN tbl_Artist A ON A.ID = So.Artist_FK
ORDER BY Song_FK DESC