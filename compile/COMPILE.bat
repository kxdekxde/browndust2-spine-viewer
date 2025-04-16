pyinstaller --onefile --windowed --icon="icon.ico" ^
--add-data "icon.png;." ^
--add-data "spine_viewer_settings.json;." ^
--add-data "BD2 Characters - Characters.csv;." ^
--add-data "%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages\\UnityPy\\resources;UnityPy/resources" ^
--additional-hooks-dir=. ^
BD2pineViewer.pyw
