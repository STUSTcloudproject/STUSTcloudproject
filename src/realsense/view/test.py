from online_registration import OnlineRegistration
import sys
import open3d.visualization.gui as gui

def main():
    gui.Application.instance.initialize()
    w = OnlineRegistration(1600, 900)
    gui.Application.instance.run()

if __name__ == "__main__":
    print("Starting Open3D Online Processing PC Visualizer")
    main()