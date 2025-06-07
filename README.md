# Brown Dust II Mod Manager
A simple tool that uses a modified version of [anosu Spine Viewer](https://github.com/anosu/Spine-Viewer) to view [Brown Dust 2](https://www.browndust2.com/en-us/) Spine animations using exported assets. And it works with the "mods" folder from the mod applier tool BrownDustX by Synae.

IMPORTANT: This mod manager works with a folder structure `mod author->mod subfolder->assets + .modfile`, example:
```
\linr熊\Celia_Bunny_Reverse_Cut\cutscene_char060403 (.atlas + .skel/.json + .png)
```

## Portable Version:
If you don't want to install the stuff below to use the script you can download this portable version ready for usage.


<p align="center">
  👉<a href="https://www.mediafire.com/file/klcvbrtve4twnvg/BrownDust2ModManager.7z/file"><strong>DOWNLOAD HERE</strong></a>👈
</p>


## Portable Version Usage:

1. Double-click on _BrownDust2ModManager.exe_.
2. The manager will ask you for the path to your BrownDustX "mods" folder, click OK on the message box.
3. You will see this GUI:


<img src="https://files.catbox.moe/t9eu8n.png" width="700"/>


4. Click on `Browse...` and navigate to your mods folder and select it.
5. The mod manager will display the list with your mods.


<img src="https://files.catbox.moe/6nc236.png" width="700"/>


### Buttons:

`Preview`: Open the Spine viewer to see the Spine animation. If the mod folder only contains an image then the viewer will use the user default images viewer to open that image.

`Refresh Mods List`: If you renamed, moved or deleted the mods then use this button to refresh the mods list to show the changes.

`Open Folder`: Open the mod folder.

`Activate/Deactivate`: Deactivate or activate mods, with this function you can have multiple mods for the same character and to activate the one you want to use faster.

`Clear`: Clear the search bar with one click.



## Requirements to use the script:

  - Double-click on _install_requirements.bat_ to install the required dependencies and Python 3.13.
  
NOTE: The requirements listed in "requirements.txt" are only for my GUI script, you will need to install the ones necessary for anosu's Spine Viewer separately (Electron, Node.js, etc).
  
  

## Script Usage:

1. Double-click on _BrownDust2ModManager.pyw_.
2. The script will ask the user for the path to your BDX "mods" folder, click OK on the message box.
3. You will see this GUI:


<img src="https://files.catbox.moe/t9eu8n.png" width="700"/>


4. Click on `Browse...` and navigate to your mods folder and select it.
5. The mod manager will display the list with your mods.


<img src="https://files.catbox.moe/6nc236.png" width="700"/>


6. This is optional, double-click on _CREATE_SHORTCUT.bat_ if you want to create a shortcut for the mod manager on your Desktop.


## How to build the executable with PyInstaller:
```
pyinstaller --onefile --windowed --icon="icon.ico" ^
--add-data "icon.png;." ^
--add-data "spine_viewer_settings.json;." ^
--add-data "characters.json;." ^
BrownDust2ModManager.pyw
```
