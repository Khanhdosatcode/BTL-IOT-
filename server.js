const express = require('express');
const bodyParser = require('body-parser');
const mysql = require('mysql2');
const axios = require('axios');
const fs = require('fs');
const multer = require('multer');
const { spawn } = require('child_process');

const ESP32_IP = '192.168.38.126';
const IMAGE_PATH = 'esp32cam.jpg';

const app = express();
const port = 3000;

// Cau hinh multer de luu tru tam thoi cac tep tai len
const upload = multer({ dest: 'uploads/' });

app.use(bodyParser.json());
app.use(express.static(__dirname));

// Cau hinh ket noi MySQL
const db = mysql.createConnection({
  host: 'localhost',    // Hoac IP cua server MySQL
  user: 'root',         // Username MySQL
  password: '',         // Password MySQL
  database: 'parking_db' // Ten CSDL
});

// Kiem tra ket noi toi MySQL
db.connect((err) => {
  if (err) {
    console.error('Khong the ket noi toi MySQL:', err.stack);
    return;
  }
  console.log('Da ket noi toi MySQL');
});

// Luu anh tu ESP32
async function captureImage() {
  try {
    const response = await axios.get(`http://${ESP32_IP}/take-picture`, { responseType: 'arraybuffer' });
    fs.writeFileSync(IMAGE_PATH, response.data);
    console.log(`Anh da duoc luu thanh cong tai ${IMAGE_PATH}`);
  } catch (error) {
    console.error('Co loi xay ra khi chup anh:', error.message);
  }
}

app.get('/take-picture', async (req, res) => {
  await captureImage();
  res.send('Chup anh thanh cong!');
});

// Nhan anh va gui den chuong trinh AI
app.post('/upload', upload.single('image'), (req, res) => {
  const imagePath = req.file.path;

  // Chay chuong trinh AI voi anh da tai len
  const pythonProcess = spawn('python', ['C:\\Users\\Meo\\Documents\\Learn_Python\\object-detect.py', imagePath]);

  pythonProcess.stdout.on('data', (data) => {
    console.log(`Ket qua nhan dien: ${data}`);
    res.send(data.toString()); // Gui ket qua ve cho client
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Loi: ${data}`);
    res.status(500).send('Da xay ra loi trong qua trinh xu ly anh.');
  });
});



// Ket thuc entrypoint
app.listen(port, () => {
  console.log(`Server running on http://localhost:${port}`);
});
