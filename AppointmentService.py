from flask import Flask, jsonify, request
import logging
import mysql.connector
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="gym"
    )

@app.route('/appointments', methods=['GET'])
def get_appointments():
    """Get all appointments"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, c.name as customer_name, t.name as trainer_name 
            FROM appointments a
            LEFT JOIN customer c ON a.customer_id = c.customer_id
            LEFT JOIN trainer t ON a.trainer_id = t.trainer_id
        """)
        appointments = cursor.fetchall()
        
        for appointment in appointments:
            if 'booking_date' in appointment and appointment['booking_date']:
                appointment['booking_date'] = appointment['booking_date'].isoformat()
        
        return jsonify(appointments)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/appointments/<int:id>', methods=['GET'])
def get_appointment(id):
    """Get appointment by ID with customer and trainer details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, c.name as customer_name, t.name as trainer_name 
            FROM appointments a
            LEFT JOIN customer c ON a.customer_id = c.customer_id
            LEFT JOIN trainer t ON a.trainer_id = t.trainer_id
            WHERE a.appointment_id = %s
        """, (id,))
        appointment = cursor.fetchone()
        
        if not appointment:
            logger.warning(f"Appointment with ID {id} not found")
            return jsonify({"error": f"Appointment with ID {id} not found"}), 404
        
        if 'booking_date' in appointment and appointment['booking_date']:
            appointment['booking_date'] = appointment['booking_date'].isoformat()
        
        return jsonify(appointment)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/appointments', methods=['POST'])
def create_appointment():
    """Create a new appointment"""
    data = request.json
    logger.debug(f"Received POST data: {data}")

    required_fields = ['customer_id', 'trainer_id', 'booking_date', 'status']
    missing_fields = [field for field in required_fields if field not in data]
    
    if not data or missing_fields:
        error_message = f"Missing required fields: {', '.join(missing_fields)}" if missing_fields else "No data provided"
        logger.error(error_message)
        return jsonify({"error": error_message}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT customer_id FROM customer WHERE customer_id = %s", (data['customer_id'],))
        if not cursor.fetchone():
            return jsonify({"error": f"Customer with ID {data['customer_id']} not found"}), 404
        
        cursor.execute("SELECT trainer_id FROM trainer WHERE trainer_id = %s", (data['trainer_id'],))
        if not cursor.fetchone():
            return jsonify({"error": f"Trainer with ID {data['trainer_id']} not found"}), 404
        
        insert_query = """
        INSERT INTO appointments (
            customer_id, trainer_id, booking_date, status
        ) VALUES (%s, %s, %s, %s)
        """
        
        values = (
            data['customer_id'],
            data['trainer_id'],
            data['booking_date'],
            data['status']
        )
        
        cursor.execute(insert_query, values)
        conn.commit()
        appointment_id = cursor.lastrowid
        logger.info(f"Created appointment ID: {appointment_id}")
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, c.name as customer_name, t.name as trainer_name 
            FROM appointments a
            LEFT JOIN customer c ON a.customer_id = c.customer_id
            LEFT JOIN trainer t ON a.trainer_id = t.trainer_id
            WHERE a.appointment_id = %s
        """, (appointment_id,))
        
        new_appointment = cursor.fetchone()
        
        if 'booking_date' in new_appointment and new_appointment['booking_date']:
            new_appointment['booking_date'] = new_appointment['booking_date'].isoformat()
        
        return jsonify(new_appointment), 201
    
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/appointments/<int:id>', methods=['PUT'])
def update_appointment(id):
    """Update an appointment by ID"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT appointment_id FROM appointments WHERE appointment_id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Appointment with ID {id} not found"}), 404
        
        update_fields = []
        values = []
        
        fields_mapping = {
            'customer_id': 'customer_id',
            'trainer_id': 'trainer_id',
            'booking_date': 'booking_date',
            'billing_id': 'billing_id',
            'status': 'status'
        }
        
        for key, db_field in fields_mapping.items():
            if key in data:
                update_fields.append(f"{db_field} = %s")
                values.append(data[key])
        
        if not update_fields:
            return jsonify({"error": "No valid fields to update"}), 400
        
        values.append(id)
        
        update_query = f"UPDATE appointments SET {', '.join(update_fields)} WHERE appointment_id = %s"
        cursor.execute(update_query, values)
        conn.commit()
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, c.name as customer_name, t.name as trainer_name 
            FROM appointments a
            LEFT JOIN customer c ON a.customer_id = c.customer_id
            LEFT JOIN trainer t ON a.trainer_id = t.trainer_id
            WHERE a.appointment_id = %s
        """, (id,))
        
        updated_appointment = cursor.fetchone()
        
        if 'booking_date' in updated_appointment and updated_appointment['booking_date']:
            updated_appointment['booking_date'] = updated_appointment['booking_date'].isoformat()
        
        return jsonify(updated_appointment)
    
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/appointments/<int:id>', methods=['DELETE'])
def delete_appointment(id):
    """Delete an appointment by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT appointment_id FROM appointments WHERE appointment_id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Appointment with ID {id} not found"}), 404
        
        cursor.execute("DELETE FROM appointments WHERE appointment_id = %s", (id,))
        conn.commit()
        
        return jsonify({"message": f"Appointment with ID {id} successfully deleted"})
    
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/appointments/customer/<int:customer_id>', methods=['GET'])
def get_customer_appointments(customer_id):
    """Get all appointments for a specific customer"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT customer_id FROM customer WHERE customer_id = %s", (customer_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Customer with ID {customer_id} not found"}), 404
        
        cursor.execute("""
            SELECT a.*, t.name as trainer_name 
            FROM appointments a
            LEFT JOIN trainer t ON a.trainer_id = t.trainer_id
            WHERE a.customer_id = %s
        """, (customer_id,))
        
        appointments = cursor.fetchall()
        
        for appointment in appointments:
            if 'booking_date' in appointment and appointment['booking_date']:
                appointment['booking_date'] = appointment['booking_date'].isoformat()
        
        return jsonify(appointments)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/appointments/trainer/<int:trainer_id>', methods=['GET'])
def get_trainer_appointments(trainer_id):
    """Get all appointments for a specific trainer"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT trainer_id FROM trainer WHERE trainer_id = %s", (trainer_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Trainer with ID {trainer_id} not found"}), 404
        
        cursor.execute("""
            SELECT a.*, c.name as customer_name 
            FROM appointments a
            LEFT JOIN customer c ON a.customer_id = c.customer_id
            WHERE a.trainer_id = %s
        """, (trainer_id,))
        
        appointments = cursor.fetchall()
        
        for appointment in appointments:
            if 'booking_date' in appointment and appointment['booking_date']:
                appointment['booking_date'] = appointment['booking_date'].isoformat()
        
        return jsonify(appointments)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(port=5002, debug=True)