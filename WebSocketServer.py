import asyncio
import json
import websockets
import aiomysql  # Dùng aiomysql thay cho mysql.connector
# import bcrypt

# Danh sách lưu các kết nối WebSocket client web
esp32_websocket = None
client_websockets = set()

# Kết nối cơ sở dữ liệu với aiomysql (bất đồng bộ)
class MySQLPool:
    def __init__(self):
        self.pool = None

    async def create_pool(self):
        """Tạo pool kết nối cơ sở dữ liệu MySQL."""
        self.pool = await aiomysql.create_pool(
            host='localhost',
            port=3306,
            user='root',
            password='',
            db='parking_db',
            minsize=1,  # Số kết nối tối thiểu
            maxsize=10, # Số kết nối tối đa
            loop=asyncio.get_event_loop()
        )

    async def get_connection(self):
        """Lấy kết nối từ pool."""
        return await self.pool.acquire()

    async def release_connection(self, connection):
        """Trả kết nối về pool."""
        await self.pool.release(connection)

# Khởi tạo connection pool khi ứng dụng bắt đầu
mysql_pool = MySQLPool()

# Kết nối cơ sở dữ liệu
async def get_db_connection():
    """Lấy kết nối MySQL từ pool."""
    connection = await mysql_pool.get_connection()
    return connection

# Hàm lấy dữ liệu hóa đơn từ cơ sở dữ liệu
import aiomysql
from datetime import datetime

from datetime import datetime
import aiomysql
from decimal import Decimal

from datetime import datetime
import aiomysql
from decimal import Decimal

async def fetch_invoice_data():
    connection = await get_db_connection()
    
    if connection is None:
        print("Không thể kết nối tới cơ sở dữ liệu!")
        return []  # Trả về danh sách rỗng nếu không thể kết nối
    
    cursor = None  # Khai báo cursor ngoài try để dễ dàng đóng trong finally
    try:
        # Tạo cursor cho truy vấn
        cursor = await connection.cursor(aiomysql.DictCursor)
        
        # Truy vấn dữ liệu hóa đơn
        query = """
            SELECT
                u.id AS 'Mã người dùng',
                ps.slot_id AS 'Mã chỗ trống',
                rc.rfid_code AS 'Mã RFID',
                i.entry_time AS 'Giờ vào',
                i.exit_time AS 'Giờ ra',
                i.total_amount AS 'Tiền trả'
            FROM
                invoices i
            JOIN
                users u ON i.user_id = u.id
            JOIN
                rfid_cards rc ON u.id = rc.user_id
            JOIN
                parking_slots ps ON i.parking_slot_id = ps.slot_id
            WHERE
                i.entry_time IS NOT NULL;
        """
        
        # Thực thi truy vấn
        await cursor.execute(query)
        result = await cursor.fetchall()  # Lấy kết quả truy vấn

        # Chuyển đổi các trường datetime thành chuỗi và Decimal thành float
        for row in result:
            if row['Giờ vào']:
                row['Giờ vào'] = row['Giờ vào'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(row['Giờ vào'], datetime) else str(row['Giờ vào'])
            if row['Giờ ra']:
                row['Giờ ra'] = row['Giờ ra'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(row['Giờ ra'], datetime) else str(row['Giờ ra'])
            if isinstance(row['Tiền trả'], Decimal):
                # Chuyển đổi Decimal thành float
                row['Tiền trả'] = float(row['Tiền trả'])

        return result

    except aiomysql.MySQLError as e:
        # Xử lý lỗi cơ sở dữ liệu
        print(f"Lỗi cơ sở dữ liệu: {e}")
        return []  # Trả về danh sách rỗng nếu có lỗi xảy ra

    finally:
        # Đảm bảo đóng cursor và connection
        if cursor:
            await cursor.close()
        if connection:
            try:
                # Kiểm tra trước khi gọi await connection.close()
                if connection is not None:
                    await connection.close()
            except Exception as e:
                print(f"Không thể đóng kết nối: {e}")



# Hàm kiểm tra thông tin đăng nhập
# Hàm kiểm tra thông tin đăng nhập
async def check_login(username, password):
    # Lấy kết nối từ pool
    connection = await get_db_connection()

    # Kiểm tra kết nối có hợp lệ không
    if connection is None:
        print("Failed to get a valid database connection.")
        return False, None

    try:
        # Mở cursor
        cursor = await connection.cursor()
        # Truy vấn mật khẩu và vai trò người dùng
        query = "SELECT password, role FROM users WHERE username = %s"
        await cursor.execute(query, (username,))
        user = await cursor.fetchone()

        if user:
            stored_password, role = user
            # Nếu có yêu cầu kiểm tra mật khẩu (ví dụ, sử dụng bcrypt)
            # Nếu bạn không mã hóa mật khẩu, bạn có thể bỏ qua kiểm tra này.
            # if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
            return True, role

        # Nếu không tìm thấy người dùng hoặc mật khẩu không đúng
        return False, None

    except aiomysql.MySQLError as e:
        print(f"Database error: {e}")
        return False, None

    finally:
        # Đảm bảo luôn đóng cursor và trả kết nối về pool
        if cursor:
            await cursor.close()
        if connection:
            await mysql_pool.release_connection(connection)

# Hàm gửi thông điệp đến ESP32
async def send_to_esp32(message):
    if esp32_websocket:
        try:
            await esp32_websocket.send(message)
            print(f"Sent to ESP32: {message}")
        except Exception as e:
            print(f"Error sending to ESP32: {str(e)}")

# Hàm xử lý tin nhắn từ WebSocket client
async def message_received(websocket, message):
    print(f"Message received from client: {message}")
    try:
        data = json.loads(message)
        # Kiểm tra hành động trong thông điệp
        if data.get("action") == "fetch_invoices":
            invoices = await fetch_invoice_data()  # Gọi hàm lấy dữ liệu hóa đơn
            if invoices:
                # Gửi lại dữ liệu cho client sau khi xử lý
                await websocket.send(json.dumps(invoices))  
            else:
                await websocket.send(json.dumps({"error": "Không thể lấy dữ liệu hóa đơn"}))

        # Xử lý yêu cầu trạng thái các ô đỗ xe
        if data.get("action") == "getSlotsStatus":
            # Kết nối đến cơ sở dữ liệu
            connection = await get_db_connection()
            try:
                # Truy vấn trạng thái các ô đỗ xe
                cursor = await connection.cursor(aiomysql.DictCursor)
                await cursor.execute("SELECT slot_id, status FROM parking_slots")
                slots = await cursor.fetchall()

                # Tạo phản hồi từ dữ liệu truy vấn
                response = {
                    "status": "success",
                    "slots": [{"slotId": slot["slot_id"], "status": slot["status"]} for slot in slots]
                }

                # Gửi lại phản hồi cho client
                await websocket.send(json.dumps(response))

            finally:
                await cursor.close()
                connection.close()


        # Xử lý đăng nhập
        elif data.get("type") == "login":
            # Kiểm tra dữ liệu có hợp lệ không
            username = data.get('username')
            password = data.get('password')

            if username and password:
                # Kiểm tra đăng nhập
                is_authenticated, role = await check_login(username, password)
                if is_authenticated:
                    await websocket.send(json.dumps({"status": "success", "role": role}))
                    print(f"User {username} logged in as {role}")
                else:
                    await websocket.send(json.dumps({"status": "fail", "message": "Invalid credentials"}))
                    print("Login failed")
            else:
                # Nếu thiếu username hoặc password
                await websocket.send(json.dumps({"status": "fail", "message": "Username and password are required"}))
                print("Missing username or password")


        # Xử lý các hành động khác như mở/đóng ô đỗ xe, buzzer
        elif data.get("action") in ['open_in', 'close_in', 'open_out', 'close_out', 'buzzer_on', 'buzzer_off']:
            await send_to_esp32(data["action"])
            await websocket.send(f"Command {data['action']} sent to ESP32")
        
        # Xử lý thông tin RFID để vào bãi đỗ
        
        elif "action" in data and data["action"] == "rfid_code_in":
    # Xử lý hành động RFID vào bãi đỗ xe
            rfid_code = data.get("rfid_code")
            if not rfid_code:
                await websocket.send("RFID code is required.")
                return
            # Kết nối cơ sở dữ liệu
            connection = await get_db_connection()
            if connection:
                try:
                    # Mở cursor bất đồng bộ
                    async with connection.cursor(aiomysql.DictCursor) as cursor:

                        # Truy vấn để lấy user_id từ bảng rfid_cards
                        await cursor.execute("SELECT user_id FROM rfid_cards WHERE rfid_code = %s", (rfid_code,))
                        user = await cursor.fetchone()

                        if not user:
                            await websocket.send("RFID not found")
                            return

                        user_id = user["user_id"]

                        # Truy vấn hóa đơn của người dùng và kiểm tra entry_time và exit_time
                        await cursor.execute("""
                            SELECT id, entry_time, exit_time FROM invoices
                            WHERE user_id = %s AND entry_time IS NULL AND exit_time IS NULL
                            ORDER BY issue_date DESC LIMIT 1
                        """, (user_id,))
                        invoice = await cursor.fetchone()

                        if not invoice:
                            # Nếu không có hóa đơn thỏa mãn điều kiện (entry_time và exit_time đều là NULL)
                            await websocket.send("No valid invoice found for this user. Invalid RFID or conditions.")
                            return

                # Cập nhật entry_time cho hóa đơn này
                        await cursor.execute("""
                            UPDATE invoices SET entry_time = NOW()
                            WHERE id = %s AND entry_time IS NULL AND exit_time IS NULL
                        """, (invoice["id"],))
                        await connection.commit()

                # Gửi thông báo thành công
                        await websocket.send("Access granted. Entry time updated.")

                except aiomysql.MySQLError as e:
                    await websocket.send(f"Database error: {str(e)}")
                finally:
            # Đảm bảo đóng cursor và trả kết nối về pool
                    await cursor.close()
                    await mysql_pool.release_connection(connection)
        elif "action" in data and data["action"] == "rfid_code_out":
    # Xử lý hành động RFID ra ngoài bãi đỗ xe
            rfid_code = data.get("rfid_code")
            if not rfid_code:
                await websocket.send("RFID code is required to exit parking.")
                return
    # Kết nối cơ sở dữ liệu
            connection = await get_db_connection()
            if connection:
                try:
                    # Mở cursor bất đồng bộ
                    async with connection.cursor(aiomysql.DictCursor) as cursor:

                        # Truy vấn để lấy user_id từ bảng rfid_cards
                        await cursor.execute("SELECT user_id FROM rfid_cards WHERE rfid_code = %s", (rfid_code,))
                        user = await cursor.fetchone()

                        if not user:
                            await websocket.send("RFID not found")
                            return

                        user_id = user["user_id"]

                        # Truy vấn hóa đơn của người dùng và kiểm tra entry_time và exit_time
                        await cursor.execute("""
                            SELECT id, entry_time, exit_time FROM invoices
                            WHERE user_id = %s AND entry_time IS  NULL AND exit_time IS NOT NULL
                            ORDER BY issue_date DESC LIMIT 1
                        """, (user_id,))
                        invoice = await cursor.fetchone()

                        if not invoice:
                            # Nếu không có hóa đơn thỏa mãn điều kiện
                            await websocket.send("No valid invoice found for this user.")
                            return

                        # Tính số giây đã sử dụng
                        entry_time = invoice["entry_time"]
                        exit_time = invoice["exit_time"]

                        # Convert entry_time và exit_time sang datetime
                        entry_time = entry_time.replace(tzinfo=None)  # Remove timezone if exists
                        exit_time = exit_time.replace(tzinfo=None)

                        # Tính chênh lệch thời gian (giây)
                        time_diff = (exit_time - entry_time).total_seconds()

                        # Tính tiền thanh toán (giá mỗi giây = 20)
                        amount_due = time_diff * 20

                        # Truy vấn balance của người dùng
                        await cursor.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
                        user_data = await cursor.fetchone()

                        if not user_data:
                            await websocket.send("User not found in users table.")
                            return

                        balance = user_data["balance"]

                        if balance < amount_due:
                            await websocket.send("Insufficient balance.")
                            return

                        # Cập nhật lại balance của người dùng sau khi trừ tiền
                        new_balance = balance - amount_due
                        await cursor.execute("""
                            UPDATE users SET balance = %s WHERE id = %s
                        """, (new_balance, user_id))
                        await connection.commit()
                        await cursor.execute("""
                            UPDATE invoices SET exit_time = NOW(), total_amount = %s 
                            WHERE id = %s AND exit_time IS NULL
                        """, (amount_due, invoice["id"]))
                        await connection.commit()
                        # Cập nhật exit_time cho hóa đơn (đảm bảo rằng nó chưa được cập nhật trước đó)
                        await cursor.execute("""
                            UPDATE invoices SET exit_time = NOW() 
                            WHERE id = %s AND exit_time IS NULL
                        """, (invoice["id"],))
                        await connection.commit()

                        # Gửi thông báo về kết quả
                        await websocket.send(f"Exit registered. Payment due: {amount_due} units. New balance: {new_balance}.")

                except json.JSONDecodeError as e:
                     await websocket.send(f"Invalid JSON format: {str(e)}")
        elif data.get('action') == 'update_slot':
            slot_id = data.get('slot_id')
            status = data.get('status')    
                    # Cập nhật trạng thái slot trong cơ sở dữ liệu
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute("""
                        UPDATE parking_slots 
                        SET status = %s 
                        WHERE slot_id = 
                          """, (status, slot_id))
                    connection.commit()
                    print(f"Slot {slot_id} updated to {status}")
                            
                            # Gửi phản hồi cho client
                    response = {
                                "status": "success",
                                "message": f"Slot {slot_id} updated to {status}"
                            }
                    await websocket.send(json.dumps(response))
                except mysql.connector.Error as e:
                    error_message = f"Database error: {str(e)}"
                    await websocket.send(json.dumps({"status": "fail", "message": error_message}))
                finally:
                    cursor.close()
                    connection.close()
        elif  "message" in data and data["message"] == "Fire Detected":
            print("Fire detected! Sending response.")
            for client in client_websockets:
                if client != esp32_websocket:  # Kiểm tra xem client có phải là ESP32 không
                    try:
                        response = json.dumps({"message": "Fire Detected"})
                        await websocket.send(response)  # Gửi thông điệp lại cho client
                    except Exception as e:
                        print(f"Error sending fire alert: {e}")
        elif  "message" in data and data["message"] == "No Fire Dectected" :
            print("No Fỉre Detected.")
            for client in client_websockets:
                if client != esp32_websocket:  # Kiểm tra xem client có phải là ESP32 không
                    try:
                        response = json.dumps({"message": "No Fire Detected"})
                        await websocket.send(response)  # Gửi thông điệp lại cho client
                    except Exception as e:
                        print(f"Error sending fire alert: {e}")
        else: await websocket.send("Invalid message format.")
    except json.JSONDecodeError as e:
        await websocket.send(f"Invalid JSON format: {str(e)}")
# WebSocket server để kết nối client
async def websocket_server(websocket, path):
    global esp32_websocket
    print(f"Client connected from {websocket.remote_address}")
    if websocket.remote_address[0] == "192.168.43.2":  # Địa chỉ IP của ESP32
        if esp32_websocket is None:
            esp32_websocket = websocket
            print("ESP32 WebSocket connected and saved.")
        else:
            print("ESP32 already connected.")
    else:
        client_websockets.add(websocket)
        print("Client connected.")

    try:
        async for message in websocket:
            await message_received(websocket, message)
    except websockets.exceptions.ConnectionClosed:
        print(f"Client {websocket.remote_address} disconnected.")
        if esp32_websocket == websocket:
            esp32_websocket = None
        if websocket in client_websockets:
            client_websockets.remove(websocket)

# Khởi động server WebSocket
async def main():
    # Khởi tạo pool MySQL khi ứng dụng bắt đầu
    await mysql_pool.create_pool()

    # Chạy server WebSocket trên cổng 5000
    server = await websockets.serve(websocket_server, '0.0.0.0', 5000)
    print("WebSocket server running on port 5000...")
    await server.wait_closed()

# Chạy server
asyncio.run(main())
