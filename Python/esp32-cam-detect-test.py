import cv2
import urllib.request
import numpy as np
import requests  # Thư viện để gửi HTTP requests

# Địa chỉ IP của camera
# url = 'http://192.168.0.117/cam-hi.jpg'
url = 'http://192.168.0.117/'
result_url = 'http://192.168.0.x/result'  # Địa chỉ IP của ESP32 
winName = 'ESP32 CAMERA'
cv2.namedWindow(winName, cv2.WINDOW_AUTOSIZE)

# Tải danh sách các tên lớp từ file coco.names
classNames = []
classFile = 'coco.names'
with open(classFile, 'rt') as f:
    classNames = f.read().rstrip('\n').split('\n')

# Đường dẫn đến mô hình và cấu hình
configPath = 'ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt'
weightsPath = 'frozen_inference_graph.pb'

# Khởi tạo mô hình nhận diện đối tượng
net = cv2.dnn_DetectionModel(weightsPath, configPath)
net.setInputSize(320, 320)
net.setInputScale(1.0 / 127.5)
net.setInputMean((127.5, 127.5, 127.5))
net.setInputSwapRB(True)

while True:
    imgResponse = urllib.request.urlopen(url)
    imgNp = np.array(bytearray(imgResponse.read()), dtype=np.uint8)
    img = cv2.imdecode(imgNp, -1)

    classIds, confs, bbox = net.detect(img, confThreshold=0.5)

    vehicle_type = "unknown"
    if len(classIds) != 0:
        for classId, confidence, box in zip(classIds.flatten(), confs.flatten(), bbox):
            cv2.rectangle(img, box, color=(0, 255, 0), thickness=3)
            vehicle_type = classNames[classId - 1]  # Lấy loại phương tiện

            cv2.putText(img, vehicle_type, (box[0] + 10, box[1] + 30),
                        cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)

    #Gửi loại phương tiện về ESP32 
    requests.post(result_url, json={"vehicle": vehicle_type})

    cv2.imshow(winName, img)

    tecla = cv2.waitKey(5) & 0xFF
    if tecla == 27:
        break

cv2.destroyAllWindows()
