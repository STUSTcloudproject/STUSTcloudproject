# 匯入必要的模組
from Controller import Controller
from Model import Model
from View import View
import pythoncom

# 主程式入口點
if __name__ == "__main__":
    # 初始化 COM 庫，確保多執行緒環境中 COM 庫的正確初始化
    pythoncom.CoInitialize()
    try:
        # 創建模型(Model)實例
        model = Model()
        # 創建視圖(View)實例
        view = View()
        # 創建控制器(Controller)實例，並傳入模型和視圖
        controller = Controller(model, view)
        # 啟動控制器運行應用程式
        controller.run()
    finally:
        # 終結 COM 庫的使用，釋放相關資源
        pythoncom.CoUninitialize()
