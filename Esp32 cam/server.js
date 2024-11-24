const express = require('express');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3000; // Cổng cho server Express
const ESP32_IP = '192.168.0.117'; // Địa chỉ IP của ESP32-CAM
const IMAGE_PATH = 'esp32cam.jpg'; // Tên tệp để lưu ảnh

// Cấu hình để phục vụ các tệp tĩnh (HTML, CSS, JS)
app.use(express.static('public'));

// Hàm chụp ảnh từ ESP32-CAM
async function captureImage() {
  try {
    const response = await axios.get(`http://${ESP32_IP}/take-picture`, {
      responseType: 'arraybuffer'
    });
    fs.writeFileSync(IMAGE_PATH, response.data);
    console.log(`Ảnh đã được lưu thành công tại ${IMAGE_PATH}`);
  } catch (error) {
    console.error('Có lỗi xảy ra khi chụp ảnh:', error.message);
  }
}

// Route cho giao diện chính
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Route để xử lý yêu cầu chụp ảnh
app.get('/take-picture', async (req, res) => {
  await captureImage();
  res.send('Chụp ảnh thành công!'); // Gửi phản hồi cho client
});

// Khởi động server
app.listen(PORT, () => {
  console.log(`Server đang chạy tại http://localhost:${PORT}`);
});
