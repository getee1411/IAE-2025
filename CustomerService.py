from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import Error
import logging

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

@app.route('/customers', methods=['GET'])
def get_customers():
    """Get all customers from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customer")
        customers = cursor.fetchall()
        return jsonify(customers)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/customers/<int:id>', methods=['GET'])
def get_customer(id):
    """Get a customer by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customer WHERE customer_id = %s", (id,))
        customer = cursor.fetchone()
        
        if not customer:
            return jsonify({"error": f"Customer with ID {id} not found"}), 404
        
        return jsonify(customer)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/customers', methods=['POST'])
def add_customer():
    """Add a new customer"""
    data = request.json
    required_fields = ['name', 'email', 'no_telp', 'alamat', 'membership_type']
    
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": f"Missing required fields: {', '.join(required_fields)}"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        INSERT INTO customer (name, email, no_telp, alamat, membership_type) 
        VALUES (%s, %s, %s, %s, %s)
        """
        values = (
            data['name'], 
            data['email'], 
            data['no_telp'], 
            data['alamat'], 
            data['membership_type']
        )
        
        cursor.execute(query, values)
        conn.commit()
        customer_id = cursor.lastrowid
        
        logger.info(f"Added new customer with ID: {customer_id}")
        
        return jsonify({
            "customer_id": customer_id,
            "name": data['name'],
            "email": data['email'],
            "no_telp": data['no_telp'],
            "alamat": data['alamat'],
            "membership_type": data['membership_type']
        }), 201
    
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/customers/<int:id>', methods=['PUT'])
def update_customer(id):
    """Update a customer by ID"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM customer WHERE customer_id = %s", (id,))
        customer = cursor.fetchone()
        
        if not customer:
            return jsonify({"error": f"Customer with ID {id} not found"}), 404
        
        update_fields = []
        values = []
        
        if 'name' in data:
            update_fields.append("name = %s")
            values.append(data['name'])
        
        if 'email' in data:
            update_fields.append("email = %s")
            values.append(data['email'])
        
        if 'no_telp' in data:
            update_fields.append("no_telp = %s")
            values.append(data['no_telp'])
        
        if 'alamat' in data:
            update_fields.append("alamat = %s")
            values.append(data['alamat'])
        
        if 'membership_type' in data:
            update_fields.append("membership_type = %s")
            values.append(data['membership_type'])
        
        if not update_fields:
            return jsonify({"error": "No valid fields to update"}), 400
        
        values.append(id)
        
        update_query = f"UPDATE customer SET {', '.join(update_fields)} WHERE customer_id = %s"
        cursor.execute(update_query, values)
        conn.commit()
        
        cursor.execute("SELECT * FROM customer WHERE customer_id = %s", (id,))
        updated_customer = cursor.fetchone()
        
        return jsonify(updated_customer)
    
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/customers/<int:id>', methods=['DELETE'])
def delete_customer(id):
    """Delete a customer by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT customer_id FROM customer WHERE customer_id = %s", (id,))
        customer = cursor.fetchone()
        
        if not customer:
            return jsonify({"error": f"Customer with ID {id} not found"}), 404
        
        cursor.execute("DELETE FROM customer WHERE customer_id = %s", (id,))
        conn.commit()
        
        return jsonify({"message": f"Customer with ID {id} successfully deleted"})
    
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(port=5000, debug=True)