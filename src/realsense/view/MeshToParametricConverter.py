import sys
import os
import json
import logging
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QFileDialog, QLineEdit, QSpinBox, QDoubleSpinBox, 
    QCheckBox, QRadioButton, QGroupBox, QMessageBox, QProgressBar, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
import pyvista as pv
from geomdl import NURBS
from geomdl import utilities
from geomdl import exchange

# 定義一個工作線程來處理轉換
class ConversionThread(QThread):
    progress_update = pyqtSignal(int)
    status_update = pyqtSignal(str)
    conversion_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, input_path, u_points, v_points, smoothing_factor, iterations):
        super().__init__()
        self.input_path = input_path
        self.u_points = u_points
        self.v_points = v_points
        self.smoothing_factor = smoothing_factor
        self.iterations = iterations

    def run(self):
        try:
            self.status_update.emit("載入網格中...")
            self.progress_update.emit(0)
            
            # 載入網格
            mesh = self.load_mesh(self.input_path)
            self.progress_update.emit(15)
            self.status_update.emit("網格載入成功。")
            
            # 將網格轉換為點雲
            points = self.mesh_to_points(mesh)
            self.progress_update.emit(30)
            self.status_update.emit("網格轉換為唯一點。")
            
            # 參數化
            self.status_update.emit("計算參數化中...")
            params, eigenvectors, centroid, skeleton = self.improved_parameterization(points)
            self.progress_update.emit(45)
            self.status_update.emit("參數化完成。")
            
            # 擬合 NURBS 曲面
            self.status_update.emit("擬合 NURBS 曲面中...")
            surface = self.fit_nurbs_surface(points, params, self.u_points, self.v_points, eigenvectors, centroid, skeleton)
            self.progress_update.emit(60)
            self.status_update.emit("NURBS 曲面擬合完成。")
            
            # 添加平滑約束
            self.status_update.emit("應用平滑中...")
            surface = self.add_smoothing_constraint(surface, self.smoothing_factor)
            self.progress_update.emit(75)
            self.status_update.emit("平滑應用完成。")
            
            # 優化曲面
            self.status_update.emit("優化曲面中...")
            surface = self.optimize_surface(surface, points, params, self.iterations)
            self.progress_update.emit(90)
            self.status_update.emit("曲面優化完成。")
            
            # 保存結果
            output_path = os.path.splitext(self.input_path)[0] + "_parametric.json"
            self.save_surface(surface, output_path)
            
            self.progress_update.emit(100)
            self.status_update.emit(f"轉換完成！保存至: {output_path}")
            self.conversion_complete.emit(output_path)
        
        except Exception as e:
            error_message = f"轉換失敗: {str(e)}"
            self.error_occurred.emit(error_message)

    def load_mesh(self, file_path):
        try:
            mesh = pv.read(file_path)
            return mesh
        except Exception as e:
            raise Exception(f"載入網格時出錯: {str(e)}")

    def mesh_to_points(self, mesh):
        points = mesh.points
        points = np.unique(points, axis=0)
        return points

    def improved_parameterization(self, points):
        """改進的形狀保持參數化"""
        # 計算主軸
        centroid = np.mean(points, axis=0)
        centered = points - centroid
        
        # 主成分分析找到主方向
        cov = np.cov(centered.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        idx = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
        # 轉換到主軸坐標系
        transformed = centered @ eigenvectors
        
        # 找到骨架線（使用切片法）
        num_slices = 50
        slice_positions = np.linspace(transformed[:, 0].min(), 
                                      transformed[:, 0].max(), 
                                      num_slices)
        skeleton = []
        cross_sections = []
        
        for pos in slice_positions:
            # 找到切片上的點
            slice_mask = np.abs(transformed[:, 0] - pos) < (transformed[:, 0].ptp() / num_slices)
            if np.sum(slice_mask) > 0:
                slice_points = transformed[slice_mask]
                # 計算切片中心
                center = np.mean(slice_points, axis=0)
                skeleton.append(center)
                cross_sections.append(slice_points)
        
        skeleton = np.array(skeleton)
        
        # 計算參數化
        u_params = []
        v_params = []
        point_assignments = []
        
        # 對每個點找到最近的骨架點
        for point in transformed:
            distances = np.linalg.norm(skeleton - point, axis=1)
            closest_idx = np.argmin(distances)
            
            # u參數：基於在骨架上的位置
            u = closest_idx / (len(skeleton) - 1)
            
            # v參數：基於在橫截面上的角度位置
            relative_points = point - skeleton[closest_idx]
            angle = np.arctan2(relative_points[2], relative_points[1])
            # 將角度映射到[0,1]
            v = (angle + np.pi) / (2 * np.pi)
            
            u_params.append(u)
            v_params.append(v)
            point_assignments.append(closest_idx)
        
        # 轉換為numpy數組
        u_params = np.array(u_params)
        v_params = np.array(v_params)
        
        # 確保參數在[0,1]範圍內
        u_params = (u_params - u_params.min()) / (u_params.max() - u_params.min())
        v_params = (v_params - v_params.min()) / (v_params.max() - v_params.min())
        
        return np.column_stack((u_params, v_params)), eigenvectors, centroid, skeleton

    def create_adaptive_control_points(self, points, params, num_u, num_v, eigenvectors, centroid, skeleton):
        """基於骨架的控制點生成"""
        ctrl_pts = np.zeros((num_u * num_v, 3))
        weights = np.ones(num_u * num_v)
        
        # 轉換點到主軸坐標系
        centered = points - centroid
        transformed = centered @ eigenvectors
        
        # 使用骨架生成控制點
        for i in range(num_u):
            u = i / (num_u - 1)
            # 找到對應的骨架位置
            skeleton_idx = int(u * (len(skeleton) - 1))
            skeleton_point = skeleton[skeleton_idx]
            
            for j in range(num_v):
                v = j / (num_v - 1)
                angle = v * 2 * np.pi - np.pi
                
                # 找到當前切片上的點
                slice_mask = np.abs(transformed[:, 0] - skeleton_point[0]) < (transformed[:, 0].ptp() / num_u)
                if np.any(slice_mask):
                    slice_points = transformed[slice_mask]
                    
                    # 計算該角度方向的半徑
                    relative_points = slice_points - skeleton_point
                    point_angles = np.arctan2(relative_points[:, 2], relative_points[:, 1])  # 修正變量名
                    angle_diff = np.abs(point_angles - angle)
                    angle_diff = np.minimum(angle_diff, 2*np.pi - angle_diff)
                    nearby_mask = angle_diff < (np.pi / num_v)
                    
                    if np.any(nearby_mask):
                        nearby_points = slice_points[nearby_mask]
                        radii = np.linalg.norm(nearby_points[:, 1:] - skeleton_point[1:], axis=1)
                        radius = np.mean(radii)
                        
                        # 生成控制點
                        point = skeleton_point.copy()
                        point[1] += radius * np.cos(angle)
                        point[2] += radius * np.sin(angle)
                        
                        # 轉換回原始坐標系
                        ctrl_pts[i * num_v + j] = point @ eigenvectors.T + centroid
                        weights[i * num_v + j] = 1.0
                    else:
                        # 如果找不到合適的點，使用骨架點
                        ctrl_pts[i * num_v + j] = skeleton_point @ eigenvectors.T + centroid
                        weights[i * num_v + j] = 0.5
                else:
                    # 如果切片上沒有點，使用骨架點
                    ctrl_pts[i * num_v + j] = skeleton_point @ eigenvectors.T + centroid
                    weights[i * num_v + j] = 0.5
        
        return ctrl_pts.tolist(), weights.tolist()

    def fit_nurbs_surface(self, points, params, num_u, num_v, eigenvectors, centroid, skeleton):
        """擬合NURBS曲面"""
        try:
            surface = NURBS.Surface()
            
            # 設置基本屬性
            surface.degree_u = 3
            surface.degree_v = 3
            surface.ctrlpts_size_u = num_u
            surface.ctrlpts_size_v = num_v
            
            # 創建控制點，加入skeleton參數
            ctrlpts, weights = self.create_adaptive_control_points(
                points, params, num_u, num_v, eigenvectors, centroid, skeleton
            )
            surface.ctrlpts = ctrlpts
            surface.weights = weights
            
            # 生成節點向量
            surface.knotvector_u = utilities.generate_knot_vector(surface.degree_u, num_u)
            surface.knotvector_v = utilities.generate_knot_vector(surface.degree_v, num_v)
            
            return surface
            
        except Exception as e:
            raise Exception(f"擬合 NURBS 曲面時出錯: {str(e)}")

    def add_smoothing_constraint(self, surface, smoothing_factor):
        """添加平滑約束"""
        ctrlpts = np.array(surface.ctrlpts)
        shape = (surface.ctrlpts_size_u, surface.ctrlpts_size_v, 3)
        ctrlpts_3d = ctrlpts.reshape(shape)
        
        # 使用簡單的平滑方法（均值濾波）
        smoothed = np.zeros_like(ctrlpts_3d)
        for i in range(shape[0]):
            for j in range(shape[1]):
                # 收集相鄰點
                neighbors = []
                for di in [-1, 0, 1]:
                    for dj in [-1, 0, 1]:
                        ni, nj = i + di, j + dj
                        if 0 <= ni < shape[0] and 0 <= nj < shape[1]:
                            neighbors.append(ctrlpts_3d[ni, nj])
                
                smoothed[i, j] = np.mean(neighbors, axis=0)
        
        # 混合原始和平滑後的控制點
        ctrlpts_3d = (1 - smoothing_factor) * ctrlpts_3d + smoothing_factor * smoothed
        surface.ctrlpts = ctrlpts_3d.reshape(-1, 3).tolist()
        
        return surface

    def optimize_surface(self, surface, points, params, iterations):
        """優化NURBS曲面"""
        for iter in range(iterations):
            # 評估當前曲面點
            surf_points = []
            for param in params:
                try:
                    pt = surface.evaluate_single([float(param[0]), float(param[1])])
                    surf_points.append(pt)
                except:
                    continue
            
            if not surf_points:
                continue
            
            surf_points = np.array(surf_points)
            errors = points[:len(surf_points)] - surf_points
            
            # 自適應步長
            step_size = 0.1 * (1 - iter/iterations)
            
            # 更新控制點
            ctrlpts = np.array(surface.ctrlpts)
            weights = np.array(surface.weights)
            
            for i in range(len(ctrlpts)):
                u_idx = i // surface.ctrlpts_size_v
                v_idx = i % surface.ctrlpts_size_v
                u = u_idx / (surface.ctrlpts_size_u - 1)
                v = v_idx / (surface.ctrlpts_size_v - 1)
                
                # 找受影響的點
                influence_radius = 2.0 / max(surface.ctrlpts_size_u, surface.ctrlpts_size_v)
                distances = (params[:, 0] - u) ** 2 + (params[:, 1] - v) ** 2
                influence_mask = distances < influence_radius ** 2
                
                if np.any(influence_mask):
                    weights_mask = np.exp(-distances[influence_mask] / (2 * influence_radius ** 2))
                    weights_mask /= weights_mask.sum()
                    update = np.average(errors[influence_mask], weights=weights_mask, axis=0)
                    ctrlpts[i] += update * step_size * weights[i]
            
            surface.ctrlpts = ctrlpts.tolist()
        
        return surface

    def save_surface(self, surface, output_path):
        """保存NURBS曲面到JSON文件"""
        try:
            exchange.export_json(surface, output_path)
        except Exception as e:
            raise Exception(f"保存曲面時出錯: {str(e)}")

# 定義一個工作線程來處理可視化
class VisualizationThread(QThread):
    error_occurred = pyqtSignal(str)
    
    def __init__(self, surface, density, scale, show_ctrl_pts, view_type):
        super().__init__()
        self.surface = surface
        self.density = density
        self.scale = scale
        self.show_ctrl_pts = show_ctrl_pts
        self.view_type = view_type

    def run(self):
        try:
            # 生成參數網格
            u = np.linspace(0, 1, self.density + 1)
            v = np.linspace(0, 1, self.density + 1)
            points = np.zeros((self.density + 1, self.density + 1, 3))
            
            # 評估每個點
            for i in range(len(u)):
                for j in range(len(v)):
                    try:
                        point = self.surface.evaluate_single([float(u[i]), float(v[j])])
                        points[i, j] = np.array(point) * self.scale
                    except:
                        points[i, j] = np.zeros(3)
            
            # 創建結構化網格
            surf = pv.StructuredGrid(
                points[:, :, 0],
                points[:, :, 1],
                points[:, :, 2]
            )
            
            # 創建 Plotter 並添加曲面
            plotter = pv.Plotter()
            plotter.add_mesh(surf, color='#1E90FF', opacity=0.8, show_edges=True)  # 使用更深的藍色
            
            # 顯示控制點和控制網格
            if self.show_ctrl_pts:
                control_points = np.array(self.surface.ctrlpts) * self.scale
                points_pv = pv.PolyData(control_points)
                plotter.add_mesh(points_pv, color='#FF4500', point_size=10, render_points_as_spheres=True)  # 橙紅色
                
                # 添加控制網格
                u_size = self.surface.ctrlpts_size_u
                v_size = self.surface.ctrlpts_size_v
                
                for i in range(u_size):
                    for j in range(v_size):
                        idx = i * v_size + j
                        if i < u_size - 1:
                            next_idx = (i + 1) * v_size + j
                            line = pv.Line(control_points[idx], control_points[next_idx])
                            plotter.add_mesh(line, color='#D3D3D3', line_width=1)  # 淺灰色
                        if j < v_size - 1:
                            next_idx = i * v_size + (j + 1)
                            line = pv.Line(control_points[idx], control_points[next_idx])
                            plotter.add_mesh(line, color='#D3D3D3', line_width=1)  # 淺灰色
            
            # 設置視角
            if self.view_type == "top":
                plotter.view_xy()
            elif self.view_type == "side":
                plotter.view_yz()
            else:
                plotter.camera_position = 'iso'
            
            plotter.show()
        
        except Exception as e:
            self.error_occurred.emit(f"視覺化失敗: {str(e)}")

# 定義 MeshToNURBSConverterViewer 類
class MeshToNURBSConverterViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_logging()
        self.init_ui()
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('conversion.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def init_ui(self):
        self.setWindowTitle("Mesh to NURBS Converter & Viewer")
        self.setGeometry(200, 200, 900, 600)  # 調整窗口大小為900x600
        
        # 設定全局字體
        font = QFont()
        font.setPointSize(11)  # 調整全局字體大小為11
        self.setFont(font)
        
        # 深色配色，確保文字與背景對比度高
        self.setStyleSheet("""
            QWidget {
                background-color: #2B2B2B;
                color: #FFFFFF;
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
                font-size: 11pt;
            }
            QTabWidget::pane { /* 修改 QTabWidget 的背景 */
                border-top: 2px solid #C2C7CB;
            }
            QTabBar::tab {
                background: #3C3C3C;
                color: #FFFFFF;
                padding: 10px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #1E90FF;
                color: #FFFFFF;
            }
            QTabBar::tab:hover {
                background: #555555;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox {
                background-color: #3C3C3C;
                color: #FFFFFF;
                border: 1px solid #555555;
                padding: 8px;
                border-radius: 4px;
                font-size: 11pt;
            }
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: none;
                padding: 10px 18px;
                border-radius: 4px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #777777;
            }
            QCheckBox, QRadioButton {
                color: #FFFFFF;
                font-size: 11pt;
            }
            QGroupBox {
                border: 1px solid #555555;
                margin-top: 15px;
                padding: 15px;
                border-radius: 4px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                font-size: 11pt;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 5px;
                text-align: center;
                height: 22px;
                font-size: 11pt;
            }
            QProgressBar::chunk {
                background-color: #1E90FF;
                width: 20px;
                border-radius: 3px;
            }
            QLabel {
                font-weight: bold;
                font-size: 11pt;
            }
        """)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 使用 QTabWidget 來創建標籤頁
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # 轉換標籤頁
        self.convert_tab = QWidget()
        self.tabs.addTab(self.convert_tab, "轉換")
        self.setup_convert_tab()
        
        # 視覺化標籤頁
        self.view_tab = QWidget()
        self.tabs.addTab(self.view_tab, "視覺化")
        self.setup_view_tab()
        
        # 狀態欄
        self.status_label = QLabel("準備就緒")
        self.status_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.status_label)
    
    def setup_convert_tab(self):
        layout = QVBoxLayout()
        self.convert_tab.setLayout(layout)
        
        # 文件選擇框架
        file_group = QGroupBox("輸入文件")
        file_layout = QHBoxLayout()
        file_group.setLayout(file_layout)
        
        self.input_path_edit = QLineEdit()
        browse_btn = QPushButton("瀏覽")
        browse_btn.setIcon(QIcon())  # 如果有圖標，這裡可以設置
        browse_btn.clicked.connect(self.browse_input)
        browse_btn.setToolTip("選擇要轉換的 PLY 文件。")
        
        file_layout.addWidget(QLabel("PLY 文件:"))
        file_layout.addWidget(self.input_path_edit)
        file_layout.addWidget(browse_btn)
        
        layout.addWidget(file_group)
        
        # 參數設置框架
        param_group = QGroupBox("參數設置")
        param_layout = QGridLayout()  # 使用QGridLayout來更好地管理控件
        param_group.setLayout(param_layout)
        
        # 控制點設置
        u_label = QLabel("U 控制點數量:")
        self.u_spin = QSpinBox()
        self.u_spin.setRange(2, 1000)
        self.u_spin.setValue(45)
        self.u_spin.setToolTip("設置 U 方向的控制點數量。")
        
        v_label = QLabel("V 控制點數量:")
        self.v_spin = QSpinBox()
        self.v_spin.setRange(2, 1000)
        self.v_spin.setValue(25)
        self.v_spin.setToolTip("設置 V 方向的控制點數量。")
        
        # 平滑度控制
        smoothing_label = QLabel("平滑因子:")
        self.smoothing_spin = QDoubleSpinBox()
        self.smoothing_spin.setRange(0.0, 1.0)
        self.smoothing_spin.setSingleStep(0.05)
        self.smoothing_spin.setValue(0.2)
        self.smoothing_spin.setToolTip("設置曲面的平滑程度。")
        
        # 優化迭代次數
        iterations_label = QLabel("優化迭代次數:")
        self.iter_spin = QSpinBox()
        self.iter_spin.setRange(1, 1000)
        self.iter_spin.setValue(15)
        self.iter_spin.setToolTip("設置優化曲面的迭代次數。")
        
        # 將控件添加到GridLayout中
        param_layout.addWidget(u_label, 0, 0)
        param_layout.addWidget(self.u_spin, 0, 1)
        param_layout.addWidget(v_label, 0, 2)
        param_layout.addWidget(self.v_spin, 0, 3)
        param_layout.addWidget(smoothing_label, 1, 0)
        param_layout.addWidget(self.smoothing_spin, 1, 1)
        param_layout.addWidget(iterations_label, 1, 2)
        param_layout.addWidget(self.iter_spin, 1, 3)
        
        layout.addWidget(param_group)
        
        # 轉換按鈕
        self.convert_btn = QPushButton("轉換")
        self.convert_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setToolTip("點擊此按鈕開始轉換。")
        layout.addWidget(self.convert_btn, alignment=Qt.AlignCenter)
        
        # 進度條
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
    
    def setup_view_tab(self):
        layout = QVBoxLayout()
        self.view_tab.setLayout(layout)
        
        # 文件選擇框架
        file_group = QGroupBox("輸入文件")
        file_layout = QHBoxLayout()
        file_group.setLayout(file_layout)
        
        self.nurbs_input_edit = QLineEdit()
        browse_nurbs_btn = QPushButton("瀏覽")
        browse_nurbs_btn.setIcon(QIcon())  # 如果有圖標，這裡可以設置
        browse_nurbs_btn.clicked.connect(self.browse_nurbs_input)
        browse_nurbs_btn.setToolTip("選擇要可視化的 NURBS JSON 文件。")
        
        file_layout.addWidget(QLabel("NURBS JSON 文件:"))
        file_layout.addWidget(self.nurbs_input_edit)
        file_layout.addWidget(browse_nurbs_btn)
        
        layout.addWidget(file_group)
        
        # 視覺化選項框架
        options_group = QGroupBox("視覺化選項")
        options_layout = QVBoxLayout()
        options_group.setLayout(options_layout)
        
        # 控制點顯示
        self.show_ctrl_checkbox = QCheckBox("顯示控制點")
        self.show_ctrl_checkbox.setChecked(True)
        self.show_ctrl_checkbox.setToolTip("選中以顯示控制點和控制網格。")
        options_layout.addWidget(self.show_ctrl_checkbox)
        
        # 網格密度和縮放因子
        grid_layout = QHBoxLayout()
        
        grid_density_label = QLabel("網格密度:")
        self.grid_density_spin = QSpinBox()
        self.grid_density_spin.setRange(1, 1000)
        self.grid_density_spin.setValue(50)
        self.grid_density_spin.setToolTip("設置可視化網格的密度。")
        
        scale_label = QLabel("縮放因子:")
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.1, 10.0)
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.setValue(1.0)
        self.scale_spin.setToolTip("設置可視化的縮放比例。")
        
        grid_layout.addWidget(grid_density_label)
        grid_layout.addWidget(self.grid_density_spin)
        grid_layout.addWidget(scale_label)
        grid_layout.addWidget(self.scale_spin)
        
        options_layout.addLayout(grid_layout)
        
        # 視角選擇
        view_group = QGroupBox("視角選擇")
        view_layout = QHBoxLayout()
        view_group.setLayout(view_layout)
        
        self.view_type_perspective = QRadioButton("透視")
        self.view_type_perspective.setChecked(True)
        self.view_type_perspective.setToolTip("選擇透視視角。")
        self.view_type_top = QRadioButton("頂視圖")
        self.view_type_top.setToolTip("選擇頂視圖。")
        self.view_type_side = QRadioButton("側視圖")
        self.view_type_side.setToolTip("選擇側視圖。")
        
        view_layout.addWidget(self.view_type_perspective)
        view_layout.addWidget(self.view_type_top)
        view_layout.addWidget(self.view_type_side)
        
        options_layout.addWidget(view_group)
        
        layout.addWidget(options_group)
        
        # 視覺化按鈕
        self.view_btn = QPushButton("視覺化")
        self.view_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.view_btn.clicked.connect(self.start_visualization)
        self.view_btn.setToolTip("點擊此按鈕開始可視化。")
        layout.addWidget(self.view_btn, alignment=Qt.AlignCenter)
    
    def browse_input(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(self, "選擇 PLY 文件", "", "PLY Files (*.ply);;All Files (*)", options=options)
        if filename:
            self.input_path_edit.setText(filename)
    
    def browse_nurbs_input(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(self, "選擇 NURBS JSON 文件", "", "JSON Files (*.json);;All Files (*)", options=options)
        if filename:
            self.nurbs_input_edit.setText(filename)
    
    def start_conversion(self):
        input_path = self.input_path_edit.text()
        if not input_path or not os.path.isfile(input_path):
            QMessageBox.warning(self, "輸入錯誤", "請選擇一個有效的 PLY 文件。")
            return
        
        u_points = self.u_spin.value()
        v_points = self.v_spin.value()
        smoothing_factor = self.smoothing_spin.value()
        iterations = self.iter_spin.value()
        
        # 禁用轉換按鈕以避免重複操作
        self.convert_btn.setEnabled(False)
        
        # 開啟轉換線程
        self.conversion_thread = ConversionThread(input_path, u_points, v_points, smoothing_factor, iterations)
        self.conversion_thread.progress_update.connect(self.update_progress)
        self.conversion_thread.status_update.connect(self.update_status)
        self.conversion_thread.conversion_complete.connect(self.conversion_finished)
        self.conversion_thread.error_occurred.connect(self.conversion_error)
        self.conversion_thread.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def update_status(self, message):
        self.status_label.setText(message)
    
    def conversion_finished(self, output_path):
        self.convert_btn.setEnabled(True)
        QMessageBox.information(self, "成功", f"轉換完成！\n保存至: {output_path}")
        # 自動填入視覺化標籤頁的輸入框
        self.nurbs_input_edit.setText(output_path)
        self.status_label.setText("準備就緒")
    
    def conversion_error(self, error_message):
        self.convert_btn.setEnabled(True)
        QMessageBox.critical(self, "轉換錯誤", error_message)
        self.status_label.setText("準備就緒")
    
    def start_visualization(self):
        nurbs_file = self.nurbs_input_edit.text()
        if not nurbs_file or not os.path.isfile(nurbs_file):
            QMessageBox.warning(self, "輸入錯誤", "請選擇一個有效的 NURBS JSON 文件。")
            return
        
        # 加載和創建 NURBS 曲面
        try:
            surface_data = self.load_nurbs(nurbs_file)
            surface = self.create_nurbs_surface(surface_data)
        except Exception as e:
            QMessageBox.critical(self, "NURBS 載入錯誤", str(e))
            return
        
        density = self.grid_density_spin.value()
        scale = self.scale_spin.value()
        show_ctrl_pts = self.show_ctrl_checkbox.isChecked()
        
        if self.view_type_perspective.isChecked():
            view_type = "perspective"
        elif self.view_type_top.isChecked():
            view_type = "top"
        else:
            view_type = "side"
        
        # 禁用視覺化按鈕以避免重複操作
        self.view_btn.setEnabled(False)
        
        # 創建並啟動視覺化線程
        self.visualization_thread = VisualizationThread(surface, density, scale, show_ctrl_pts, view_type)
        self.visualization_thread.error_occurred.connect(self.visualization_error)
        self.visualization_thread.start()
        
        self.status_label.setText("視覺化中...")
        self.visualization_thread.finished.connect(self.visualization_finished)
    
    def visualization_finished(self):
        self.view_btn.setEnabled(True)
        self.status_label.setText("視覺化完成。")
    
    def visualization_error(self, error_message):
        self.view_btn.setEnabled(True)
        QMessageBox.critical(self, "視覺化錯誤", error_message)
        self.status_label.setText("準備就緒")
    
    # 其他必要的方法
    def load_nurbs(self, file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
            
            if 'shape' in data and 'data' in data['shape'] and len(data['shape']['data']) > 0:
                surface_data = data['shape']['data'][0]
                if self.validate_surface_data(surface_data):
                    return surface_data
            else:
                raise Exception("無效的 JSON 結構")
        except Exception as e:
            raise Exception(f"載入 NURBS JSON 時出錯: {str(e)}")
    
    def validate_surface_data(self, surface_data):
        """驗證NURBS表面數據的有效性"""
        required_fields = ['degree_u', 'degree_v', 'size_u', 'size_v', 
                           'knotvector_u', 'knotvector_v', 'control_points']
        
        # 檢查必要字段
        for field in required_fields:
            if field not in surface_data:
                raise Exception(f"缺少必要字段: {field}")
        
        # 檢查控制點
        if 'points' not in surface_data['control_points']:
            raise Exception("缺少控制點數據")
                
        # 檢查尺寸一致性
        num_points = len(surface_data['control_points']['points'])
        expected_points = surface_data['size_u'] * surface_data['size_v']
        if num_points != expected_points:
            raise Exception(f"控制點數量不匹配。預期: {expected_points}, 獲取: {num_points}")
                
        return True
    
    def create_nurbs_surface(self, surface_data):
        try:
            surface = NURBS.Surface()
            
            # 設置基本屬性
            surface.degree_u = surface_data['degree_u']
            surface.degree_v = surface_data['degree_v']
            surface.ctrlpts_size_u = surface_data['size_u']
            surface.ctrlpts_size_v = surface_data['size_v']
            surface.ctrlpts = surface_data['control_points']['points']
            surface.knotvector_u = surface_data['knotvector_u']
            surface.knotvector_v = surface_data['knotvector_v']
            
            return surface
        except Exception as e:
            raise Exception(f"創建 NURBS 曲面時出錯: {str(e)}")

def main():
    # 啟用高 DPI 支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    
    # 設定全局字體
    font = QFont()
    font.setPointSize(11)  # 調整全局字體大小為11
    app.setFont(font)
    
    window = MeshToNURBSConverterViewer()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
