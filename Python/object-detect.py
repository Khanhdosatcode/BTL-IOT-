import cv2  # Thư viện OpenCV
import numpy as np
import sys  # Thư viện sys để nhận tham số từ dòng lệnh

# Đường dẫn đến bức ảnh từ tham số dòng lệnh
imagePath = sys.argv[1]  # Nhận đường dẫn ảnh từ tham số
# imagePath = 'C:\\Users\\Meo\\Documents\\LearnJS\\Project_Nodejs\\Esp32_IOT\\esp32cam.jpg'

winName = 'Object Detection'
cv2.namedWindow(winName, cv2.WINDOW_AUTOSIZE)

# Tải danh sách các tên lớp từ file coco.names
classNames = []
classFile = 'C:\\Users\\Meo\\Documents\\Learn_Python\\coco.names'
with open(classFile, 'rt') as f:
    classNames = f.read().rstrip('\n').split('\n')

# Đường dẫn đến mô hình và cấu hình
configPath = 'C:\\Users\\Meo\\Documents\\Learn_Python\\ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt'
weightsPath = 'C:\\Users\\Meo\\Documents\\Learn_Python\\frozen_inference_graph.pb'

# Khởi tạo mô hình nhận diện đối tượng
net = cv2.dnn_DetectionModel(weightsPath, configPath)
net.setInputSize(320, 320)
net.setInputScale(1.0 / 127.5)
net.setInputMean((127.5, 127.5, 127.5))
net.setInputSwapRB(True)

# Đọc ảnh từ đường dẫn đã chỉ định
img = cv2.imread(imagePath)

# Kiểm tra xem ảnh có được đọc thành công không
if img is None:
    print("Không thể đọc ảnh từ đường dẫn:", imagePath)
    sys.exit()

# Nhận diện đối tượng với ngưỡng độ chính xác là 0.5
classIds, confs, bbox = net.detect(img, confThreshold=0.5)

# Kết quả nhận diện
# Kết quả nhận diện
results = []
max_confidence = 0  # Khởi tạo giá trị độ tin cậy lớn nhất
best_class_name = ""  # Khởi tạo tên lớp tốt nhất

if len(classIds) != 0:
    for classId, confidence, box in zip(classIds.flatten(), confs.flatten(), bbox):
        # Thêm kết quả vào danh sách
        results.append(f"{classNames[classId - 1]}: {confidence:.2f}")

        # Kiểm tra và cập nhật độ tin cậy lớn nhất
        if confidence > max_confidence:
            max_confidence = confidence
            best_class_name = classNames[classId - 1]

# In kết quả nhận diện
if results:
    # print("Ket qua:", ', '.join(results))
    print(best_class_name)
else:
    print("K phat hien doi tuong nao !")


# Đóng tất cả cửa sổ OpenCV
cv2.destroyAllWindows()
