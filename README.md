# Brown Dust II Spine Viewer
A simple tool that uses [Esoteric Skeleton Viewers](https://en.esotericsoftware.com/spine-skeleton-viewer) to view [Brown Dust 2](https://www.browndust2.com/en-us/) Spine animations or any other compatible game that uses Spine.



## Requirements to use this tool:

  - Download and install [.NET SDK 8](https://dotnet.microsoft.com/en-us/download/dotnet/thank-you/sdk-8.0.404-windows-x64-installer).
  - Download and install [Python](https://www.python.org/downloads/), along with all of the addons included (pip, etc) and enable 'PATH' as well.
  - Download and install [Microsoft C++ Build Tools](https://aka.ms/vs/17/release/vs_BuildTools.exe), and after that install the necessary libraries following [this video](https://files.catbox.moe/vqsuix.mp4).
  - Download and install [Zulu JDK](https://cdn.azul.com/zulu/bin/zulu21.40.17-ca-jdk21.0.6-win_x64.msi).
  - Open CMD and type:
    ```
    pip install UnityPy PyQt6 requests
    ```
    Hit Enter to install.
  
  



## Usage:

1. Double-click on _BD2pineViewer.pyw_ and the script will start to download the required files.
2. After to finish the downloads the script will ask the user for the path to your BDX "mods" folder, click OK on the message box.
3. You will see this GUI:


<img src="https://files.catbox.moe/6i8ywk.png" width="700"/>


4. Click on `Browse...` and navigate to your mods folder and select it.
5. The viewer will show the list with your mods, from here you can preview them or rename their folders.


<img src="https://files.catbox.moe/6ajczn.png" width="700"/>


6. This is optional, double-click on _CREATE_SHORTCUT.bat_ if you want to create a shortcut for the viewer on your Desktop.

### Buttons:

`Preview`: Open the corresponding skeleton viewer version to see the Spine animation.

`Refresh Mods List`: If you renamed, moved or deleted the mods then use this button to refresh the mods list to show the changes.

`Rename`: Renames your mods directly from the GUI. It's not necessary to use `_` in this case.


