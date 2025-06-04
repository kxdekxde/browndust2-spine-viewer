# Brown Dust II Spine Viewer + Mod Manager
A simple tool that uses a modified version of [anosu's Spine Viewer](https://github.com/anosu/Spine-Viewer) to view [Brown Dust 2](https://www.browndust2.com/en-us/) Spine animations using exported assets.

## Portable Version:
If you don't want to install the stuff below to use the scripts you can download this portable version ready for usage.


<p align="center">
  👉<a href="https://www.mediafire.com/file/iahk9r91u1xrpta/BD2pineViewer.7z/file"><strong>DOWNLOAD HERE</strong></a>👈
</p>




## Requirements to use the script:

  - Double-click on _install_requirements.bat_ to install the required dependencies and Python 3.13.
  
NOTE: The requirements listed in "requirements.txt" are only for my GUI script, you will need to install the ones necessary for anosu's Spine Viewer separately (Electron, Node.js, etc).
  
  

## Usage:

1. Double-click on _BD2pineViewer.pyw_.
2. The script will ask the user for the path to your BDX "mods" folder, click OK on the message box.
3. You will see this GUI:


<img src="https://files.catbox.moe/6i8ywk.png" width="700"/>


4. Click on `Browse...` and navigate to your mods folder and select it.
5. The viewer will show the list with your mods, from here you can preview them or rename their folders.


<img src="https://files.catbox.moe/6ajczn.png" width="700"/>


6. This is optional, double-click on _CREATE_SHORTCUT.bat_ if you want to create a shortcut for the viewer on your Desktop.

# Update 2.0 Version:

Changed the GUI style to something a bit better.


<img src="https://files.catbox.moe/80tnd1.png" width="700"/>


Added the new function to activate/deactivate mods, with this function you can have multiple mods for the same character in your "mods" folder and to leave the one you want to use activated. You can see that the deactivated mods have got red-colored letters, and the mods active have got green-colored letters.


<img src="https://files.catbox.moe/0p907b.png" width="700"/>


Added the search bar function to filter your mods list by author, character, idle, cutscene, etc.


<img src="https://files.catbox.moe/3x1zcn.png" width="700"/>


### Buttons:

`Preview`: Open the Spine viewer to see the Spine animation. If the mod folder only contains an image then the viewer will use the user default images viewer to open that image.

`Refresh Mods List`: If you renamed, moved or deleted the mods then use this button to refresh the mods list to show the changes.

`Rename`: Renames your mods folders directly from the GUI.

`Activate/Deactivate`: Deactivate or activate mods, with this function you can have multiple mods for the same character and to activate the one you want to use faster.

`Clear`: Clear the search bar with one click.


## How to build the executable with PyInstaller:
```
pyinstaller --onefile --windowed --icon="icon.ico" ^
--add-data "icon.png;." ^
--add-data "spine_viewer_settings.json;." ^
--add-data "BD2 Characters - Characters.csv;." ^
BD2pineViewer.pyw
```
