from flask import Flask, jsonify, request
import requests
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# Fungsi koneksi ke database MySQL
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",          # Sesuaikan dengan user MySQL kamu
        password="",          # Sesuaikan dengan password MySQL kamu
        database="gym"        # Sesuaikan dengan nama database kamu
    )

@app.route('/billings/<appointment_id>', methods=['GET'])
def get_billing_by_appointment_id(appointment_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Ambil data appointment berdasarkan ID
        cursor.execute("SELECT * FROM appointments WHERE id = %s", (appointment_id,))
        appointment = cursor.fetchone()

        if not appointment:
            return jsonify({"error": f"Appointment with ID {appointment_id} not found"}), 404

        # Ambil data customer
        try:
            customer_response = requests.get(f"http://localhost:5000/customers/{appointment['customer_id']}", timeout=5)
            customer_response.raise_for_status()
            customer = customer_response.json()
        except requests.RequestException as e:
            return jsonify({"error": f"Failed to fetch customer data: {str(e)}"}), 503

        # Ambil data trainer
        try:
            trainer_response = requests.get(f"http://localhost:5001/trainers/{appointment['trainer_id']}", timeout=5)
            trainer_response.raise_for_status()
            trainer = trainer_response.json()
        except requests.RequestException as e:
            return jsonify({"error": f"Failed to fetch trainer data: {str(e)}"}), 503

        # Hitung total tagihan
        base_fee = 200000 if customer['membership_type'] == "Premium" else 150000
        specialty_fee = 50000 if trainer['specialty'] == "Strength Training" else 30000
        total_amount = base_fee + specialty_fee

        billing = {
            "appointment_id": appointment_id,
            "customer_name": customer['name'],
            "trainer_name": trainer['name'],
            "date": appointment['date'],
            "amount": total_amount
        }

        return jsonify(billing)

    except Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(port=5003, debug=True)
