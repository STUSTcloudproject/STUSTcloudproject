# 項目目錄結構和介紹

## 目錄結構

```plaintext
MVC_gui/
├── docs/
│   └── directory_structure.md
├── src/
│   ├── custom_widgets/
│   │   ├── __init__.py
│   │   ├── MainQWidget.py
│   │   ├── ButtonWidget.py
│   │   ├── SettingsWidget.py
│   │   ├── ConfigurableTree.py
│   │   ├── Text_display_panel.py
│   │   ├── ImagesDisplayPanel.py
│   │   ├── ConfirmDialog.py
│   │   ├── TerminalWidget.py
│   │   ├── ErrorDialog.py
│   │   ├── ContentSplitterWidget.py
│   │   ├── ColoredWidget.py
│   │   └── README.md
│   ├── icon/
│   │   ├── camera.png
│   │   ├── home.png
│   │   ├── play.png
│   │   ├── record.png
│   │   ├── runsystem.png
│   │   ├── stop.png
│   │   └── view.png
│   ├── realsense/
│   │   ├── __init__.py
│   │   ├── record/
│   │   │   ├── __init__.py
│   │   │   ├── RealSenseRecorder.py
│   │   │   ├── realsense_helper.py
│   │   │   ├── point_cloud_manager.py
│   │   │   └── README.md
│   │   ├── run_system/
│   │   │   ├── __init__.py
│   │   │   ├── run_system.py
│   │   │   ├── make_fragments.py
│   │   │   ├── register_fragments.py
│   │   │   ├── refine_registration.py
│   │   │   ├── integrate_scene.py
│   │   │   ├── slac.py
│   │   │   ├── slac_integrate.py
│   │   │   ├── optimize_posegraph.py
│   │   │   ├── opencv_pose_estimation.py
│   │   │   ├── color_map_optimization_for_..._system.py
│   │   │   ├── data_loader.py
│   │   │   ├── initialize_config.py
│   │   │   ├── open3d_example.py
│   │   │   └── README.md
│   │   └── view/
│   │   │   ├── __init__.py
│   │   │   ├── view.py
│   │   │   ├── online_processing.py
│   │   │   ├── online_processing_pc_vis.py
│   │   │   ├── registration_manual_automatic.py
│   │   │   ├── remove_point_cloud_gui.py
│   │   │   ├── PointCloud_Mesh_Editor.py
│   │   │   ├── visualization.py
│   │   │   └── README.md
│   │   └── README.md
│   ├── config.json
│   ├── realsense.json
│   ├── main.py
│   ├── Model.py
│   ├── View.py
│   ├── Controller.py
│   ├── gui.py
│   ├── config_manager.py
│   ├── realsense.py
│   ├── widgets.py
│   ├── tool.py
│   └── README.md
└── README.md
