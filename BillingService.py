from flask import Flask, jsonify, request
import logging
import mysql.connector
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database connection function
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="gym"
    )

@app.route('/billings', methods=['GET'])
def get_billings():
    """Get all billing records"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.*, c.name as customer_name 
            FROM billings b
            LEFT JOIN customer c ON b.customer_id = c.customer_id
        """)
        billings = cursor.fetchall()
        
        return jsonify(billings)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/billings/<int:id>', methods=['GET'])
def get_billing(id):
    """Get billing record by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.*, c.name as customer_name 
            FROM billings b
            LEFT JOIN customer c ON b.customer_id = c.customer_id
            WHERE b.billing_id = %s
        """, (id,))
        billing = cursor.fetchone()
        
        if not billing:
            return jsonify({"error": f"Billing record with ID {id} not found"}), 404
        
        # Get related appointments for this billing
        cursor.execute("""
            SELECT appointment_id, customer_id, trainer_id, booking_date, status 
            FROM appointments 
            WHERE billing_id = %s
        """, (id,))
        appointments = cursor.fetchall()
        
        # Format dates for JSON response
        for appointment in appointments:
            if 'booking_date' in appointment and appointment['booking_date']:
                appointment['booking_date'] = appointment['booking_date'].isoformat()
        
        billing['appointments'] = appointments
        
        return jsonify(billing)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/billings/customer/<int:customer_id>', methods=['GET'])
def get_customer_billings(customer_id):
    """Get all billing records for a specific customer"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if customer exists
        cursor.execute("SELECT customer_id FROM customer WHERE customer_id = %s", (customer_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Customer with ID {customer_id} not found"}), 404
            
        cursor.execute("""
            SELECT b.*, c.name as customer_name 
            FROM billings b
            LEFT JOIN customer c ON b.customer_id = c.customer_id
            WHERE b.customer_id = %s
        """, (customer_id,))
        billings = cursor.fetchall()
        
        return jsonify(billings)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/billings/appointment/<int:appointment_id>', methods=['GET'])
def get_billing_by_appointment_id(appointment_id):
    """Get billing information related to a specific appointment"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get appointment data
        cursor.execute("""
            SELECT a.*, c.name as customer_name, c.membership_type, t.name as trainer_name, t.spesialisasi
            FROM appointments a
            LEFT JOIN customer c ON a.customer_id = c.customer_id
            LEFT JOIN trainer t ON a.trainer_id = t.trainer_id
            WHERE a.appointment_id = %s
        """, (appointment_id,))
        appointment = cursor.fetchone()

        if not appointment:
            return jsonify({"error": f"Appointment with ID {appointment_id} not found"}), 404

        # Get billing information if it exists
        billing_info = None
        if appointment['billing_id']:
            cursor.execute("""
                SELECT * FROM billings WHERE billing_id = %s
            """, (appointment['billing_id'],))
            billing_info = cursor.fetchone()

        # Format dates for appointment
        if 'booking_date' in appointment and appointment['booking_date']:
            appointment['booking_date'] = appointment['booking_date'].isoformat()

        # Calculate billing details if not already assigned
        if not billing_info:
            # Calculate amount based on membership type and trainer specialization
            base_fee = 200000 if appointment['membership_type'] == "Premium" else 150000
            specialty_fee = 50000 if appointment['spesialisasi'] == "Strength Training" else 30000
            total_amount = base_fee + specialty_fee
            
            billing_info = {
                "customer_id": appointment['customer_id'],
                "amount": float(total_amount)
            }

        response = {
            "appointment": appointment,
            "billing": billing_info
        }

        return jsonify(response)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/billings', methods=['POST'])
def create_billing():
    """Create a new billing record"""
    data = request.json
    
    required_fields = ['customer_id', 'amount']
    missing_fields = [field for field in required_fields if field not in data]
    
    if not data or missing_fields:
        error_message = f"Missing required fields: {', '.join(missing_fields)}" if missing_fields else "No data provided"
        return jsonify({"error": error_message}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if customer exists
        cursor.execute("SELECT customer_id FROM customer WHERE customer_id = %s", (data['customer_id'],))
        if not cursor.fetchone():
            return jsonify({"error": f"Customer with ID {data['customer_id']} not found"}), 404
        
        insert_query = """
        INSERT INTO billings (
            customer_id, amount
        ) VALUES (%s, %s)
        """
        
        values = (
            data['customer_id'],
            data['amount']
        )
        
        cursor.execute(insert_query, values)
        conn.commit()
        billing_id = cursor.lastrowid
        
        # If appointments are provided, link them to this billing
        if 'appointment_ids' in data and isinstance(data['appointment_ids'], list):
            for app_id in data['appointment_ids']:
                cursor.execute(
                    "UPDATE appointments SET billing_id = %s WHERE appointment_id = %s",
                    (billing_id, app_id)
                )
            conn.commit()
        
        # Get the created billing with customer name
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.*, c.name as customer_name 
            FROM billings b
            LEFT JOIN customer c ON b.customer_id = c.customer_id
            WHERE b.billing_id = %s
        """, (billing_id,))
        
        new_billing = cursor.fetchone()
            
        return jsonify(new_billing), 201
        
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/billings/<int:id>', methods=['PUT'])
def update_billing(id):
    """Update a billing record"""
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if billing exists
        cursor.execute("SELECT billing_id FROM billings WHERE billing_id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Billing record with ID {id} not found"}), 404
        
        # Only update fields that are provided
        update_fields = []
        values = []
        
        for field in ['customer_id', 'amount']:
            if field in data:
                update_fields.append(f"{field} = %s")
                values.append(data[field])
        
        if not update_fields:
            return jsonify({"error": "No valid fields to update"}), 400
        
        # Add billing_id to values for the WHERE clause
        values.append(id)
        
        update_query = f"""
        UPDATE billings 
        SET {', '.join(update_fields)}
        WHERE billing_id = %s
        """
        
        cursor.execute(update_query, values)
        conn.commit()
        
        # If customer_id is being updated, check if new customer exists
        if 'customer_id' in data:
            cursor.execute("SELECT customer_id FROM customer WHERE customer_id = %s", (data['customer_id'],))
            if not cursor.fetchone():
                return jsonify({"error": f"Customer with ID {data['customer_id']} not found"}), 404
        
        # If appointments are provided, update their billing_id
        if 'appointment_ids' in data and isinstance(data['appointment_ids'], list):
            # First, remove this billing_id from all appointments that may have it
            cursor.execute(
                "UPDATE appointments SET billing_id = NULL WHERE billing_id = %s",
                (id,)
            )
            
            # Then add this billing_id to specified appointments
            for app_id in data['appointment_ids']:
                cursor.execute(
                    "UPDATE appointments SET billing_id = %s WHERE appointment_id = %s",
                    (id, app_id)
                )
            conn.commit()
        
        # Get the updated billing
        cursor.execute("""
            SELECT b.*, c.name as customer_name 
            FROM billings b
            LEFT JOIN customer c ON b.customer_id = c.customer_id
            WHERE b.billing_id = %s
        """, (id,))
        
        updated_billing = cursor.fetchone()
        
        return jsonify(updated_billing)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/billings/<int:id>', methods=['DELETE'])
def delete_billing(id):
    """Delete a billing record"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if billing exists
        cursor.execute("SELECT billing_id FROM billings WHERE billing_id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Billing record with ID {id} not found"}), 404
        
        # Remove billing_id reference from appointments
        cursor.execute("UPDATE appointments SET billing_id = NULL WHERE billing_id = %s", (id,))
        
        # Delete the billing
        cursor.execute("DELETE FROM billings WHERE billing_id = %s", (id,))
        conn.commit()
        
        return jsonify({"message": f"Billing record with ID {id} has been deleted"}), 200
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/billings/stats', methods=['GET'])
def get_billing_stats():
    """Get billing statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Total billings
        cursor.execute("SELECT COUNT(*) as total_count FROM billings")
        total_result = cursor.fetchone()
        
        # Total billing amount
        cursor.execute("SELECT SUM(amount) as total_amount FROM billings")
        amount_result = cursor.fetchone()
        total_amount = float(amount_result['total_amount']) if amount_result['total_amount'] else 0
        
        # Count by customer
        cursor.execute("""
            SELECT c.name, COUNT(b.billing_id) as count, SUM(b.amount) as total
            FROM billings b
            JOIN customer c ON b.customer_id = c.customer_id
            GROUP BY b.customer_id
            ORDER BY total DESC
        """)
        customer_stats = cursor.fetchall()
        
        # Format totals for JSON response
        for stat in customer_stats:
            if 'total' in stat and stat['total']:
                stat['total'] = float(stat['total'])
        
        stats = {
            "total_count": total_result['total_count'],
            "total_amount": total_amount,
            "by_customer": customer_stats
        }
        
        return jsonify(stats)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/billings/calculate', methods=['POST'])
def calculate_billing():
    """Calculate billing amount for specific customer and trainer"""
    data = request.json
    
    if not data or 'customer_id' not in data or 'trainer_id' not in data:
        return jsonify({"error": "Missing required customer_id and/or trainer_id"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get customer data
        cursor.execute("SELECT * FROM customer WHERE customer_id = %s", (data['customer_id'],))
        customer = cursor.fetchone()
        if not customer:
            return jsonify({"error": f"Customer with ID {data['customer_id']} not found"}), 404
        
        # Get trainer data
        cursor.execute("SELECT * FROM trainer WHERE trainer_id = %s", (data['trainer_id'],))
        trainer = cursor.fetchone()
        if not trainer:
            return jsonify({"error": f"Trainer with ID {data['trainer_id']} not found"}), 404
        
        # Calculate billing amount based on membership type and trainer specialization
        base_fee = 200000 if customer['membership_type'] == "Premium" else 150000
        specialty_fee = 50000 if trainer['spesialisasi'] == "Strength Training" else 30000
        total_amount = base_fee + specialty_fee
        
        billing_calculation = {
            "customer_id": customer['customer_id'],
            "customer_name": customer['name'],
            "membership_type": customer['membership_type'],
            "trainer_id": trainer['trainer_id'],
            "trainer_name": trainer['name'],
            "trainer_specialty": trainer['spesialisasi'],
            "base_fee": base_fee,
            "specialty_fee": specialty_fee,
            "total_amount": total_amount
        }
        
        return jsonify(billing_calculation)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(port=5003, debug=True)