from flask import Flask, jsonify, request
import requests
import logging
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Koneksi ke database MySQL
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",  # ganti sesuai user MySQL kamu
        password="",  # ganti sesuai password MySQL kamu
        database="gym"
    )

@app.route('/gym-appointments', methods=['POST', 'GET'])
def handle_gym_appointments():
    if request.method == 'POST':
        data = request.json
        logger.debug(f"Received POST data: {data}")

        required_fields = ['customer_id', 'trainer_id', 'date']
        missing_fields = [field for field in required_fields if field not in data]
        if not data or missing_fields:
            error_message = f"Missing required fields: {', '.join(missing_fields)}" if missing_fields else "No data provided"
            logger.error(error_message)
            return jsonify({"error": error_message}), 400

        # Ambil data customer
        try:
            customer_response = requests.get(f"http://localhost:5000/customers/{data['customer_id']}", timeout=5)
            customer_response.raise_for_status()
            customer = customer_response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch customer: {str(e)}")
            return jsonify({"error": f"Failed to fetch customer data: {str(e)}"}), 503

        # Ambil data trainer
        try:
            trainer_response = requests.get(f"http://localhost:5001/trainers/{data['trainer_id']}", timeout=5)
            trainer_response.raise_for_status()
            trainer = trainer_response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch trainer: {str(e)}")
            return jsonify({"error": f"Failed to fetch trainer data: {str(e)}"}), 503

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO appointments (customer_id, trainer_id, date, status) VALUES (%s, %s, %s, %s)",
                (data['customer_id'], data['trainer_id'], data['date'], "scheduled")
            )
            conn.commit()
            appointment_id = cursor.lastrowid
            logger.info(f"Created appointment ID: {appointment_id}")
        except Error as e:
            logger.error(f"Database error: {e}")
            return jsonify({"error": str(e)}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        appointment = {
            "id": appointment_id,
            "customer": customer,
            "trainer": trainer,
            "date": data['date'],
            "status": "scheduled"
        }

        return jsonify(appointment), 201

    elif request.method == 'GET':
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM appointments")
            appointments = cursor.fetchall()
        except Error as e:
            logger.error(f"Database error: {e}")
            return jsonify({"error": str(e)}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        return jsonify(appointments)

@app.route('/gym-appointments/<id>', methods=['GET'])
def get_gym_appointment(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM appointments WHERE id = %s", (id,))
        appointment = cursor.fetchone()
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    if not appointment:
        logger.warning(f"Appointment with ID {id} not found")
        return jsonify({"error": f"Gym appointment with ID {id} not found"}), 404

    # Tambahkan pengambilan detail customer dan trainer
    try:
        customer_response = requests.get(f"http://localhost:5000/customers/{appointment['customer_id']}", timeout=5)
        customer_response.raise_for_status()
        customer = customer_response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch customer: {str(e)}")
        customer = {"error": "Failed to fetch customer data"}

    try:
        trainer_response = requests.get(f"http://localhost:5001/trainers/{appointment['trainer_id']}", timeout=5)
        trainer_response.raise_for_status()
        trainer = trainer_response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch trainer: {str(e)}")
        trainer = {"error": "Failed to fetch trainer data"}

    # Gabungkan semua data
    detailed_appointment = {
        "id": appointment["id"],
        "customer": customer,
        "trainer": trainer,
        "date": appointment["date"],
        "status": appointment["status"]
    }

    return jsonify(detailed_appointment)

if __name__ == '__main__':
    app.run(port=5002, debug=True)
