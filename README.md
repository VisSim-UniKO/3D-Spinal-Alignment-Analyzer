# 3D-Spinal-Alignment-Analyzer

# Slopes Plugin

The slopes plugin calculates all vertebra body endplate alignments of any arbitrary spine. To work properly, the spine must be provided as one STL file per vertebra.

## Installation

The plugin is targeted at the 3D medical imaging software 3D Slicer. Next, you are guided through the process of running the plugin.

1. Visit [www.slicer.org](https://www.slicer.org), download and install version 5.0.3 (or newer at your own risk)
2. Once you have Slicer up and running, select "Edit > Application Settings" from the menu bar
3. Go to 'Developer' option and tick "Enable developer mode:", hit "OK" and restart Slicer
4. Navigate to "Edit > Application Settings", then "Modules > Additional module paths:"
5. On the right, there is a double right arrow. Click it, then click "Add" and navigate to this directory's "SlicerPlugins/Slopes" folder
6. Hit "OK", again. Restart Slicer one last time.

You are ready to go.

## Usage

We assume, you already have an interesting spine to inspect on your computer. Load them into Slicer.

1. Click the "Data" icon. Then "Choose File(s) to Add". Find your STLs (at least two files). Exit the "Add data into the scene" dialoge by clicking "OK"
2. You can now rotate the 3D view with your left mouse button.
3. Click the "Create new Line" icon from the "Markups" panel. It looks like a ruler with a plus symbol in the corner.
4. Now you must place this line in the 3D scene as follows. It should attach to right hand side of the spine donor and also point in that general right direction.
5. Click the "Module Selection" dropdown list. It is the one, reading "Welcome to Slicer" by default.
6. Select the "Data" option. It displays in the Module Panel on the left.
7. You see the "Node" on that Module Panel. In there are the names of your STL files and your line element "L" by default.
8. Right click anywhere on that Module Panel, but the already existing items. Select "Create new folder".
9. Drag'n'drop your STL filenames right inside that new folder.
10. Now from the "Module Selection" dropdown list, choose "Vissim > Slopes"
11. By default, all relevant elements are detected. You only need to click "Apply"

To preserve all calculated data, the plugin consists of a CSV export option.

# Dimension Plugin

Watch this short demo, on how quickly and easily arbitrary amounts of vertebra bodies are measured:

![2023_11_09_Vertebra_Measure](https://github.com/VisSim-UniKO/3D-Spinal-Alignment-Analyzer/assets/12137187/32ef2158-a947-469b-a32b-3977576f9577)
