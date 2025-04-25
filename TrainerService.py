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

@app.route('/trainers', methods=['GET'])
def get_trainers():
    """Get all trainers from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM trainer")
        trainers = cursor.fetchall()
        return jsonify(trainers)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/trainers/<int:id>', methods=['GET'])
def get_trainer(id):
    """Get a trainer by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM trainer WHERE trainer_id = %s", (id,))
        trainer = cursor.fetchone()
        
        if not trainer:
            return jsonify({"error": f"Trainer with ID {id} not found"}), 404
        
        return jsonify(trainer)
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/trainers', methods=['POST'])
def add_trainer():
    """Add a new trainer"""
    data = request.json
    required_fields = ['name', 'email', 'no_telp', 'spesialisasi']
    
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": f"Missing required fields: {', '.join(required_fields)}"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        INSERT INTO trainer (name, email, no_telp, spesialisasi) 
        VALUES (%s, %s, %s, %s)
        """
        values = (
            data['name'], 
            data['email'], 
            data['no_telp'], 
            data['spesialisasi']
        )
        
        cursor.execute(query, values)
        conn.commit()
        trainer_id = cursor.lastrowid
        
        logger.info(f"Added new trainer with ID: {trainer_id}")
        
        return jsonify({
            "trainer_id": trainer_id,
            "name": data['name'],
            "email": data['email'],
            "no_telp": data['no_telp'],
            "spesialisasi": data['spesialisasi']
        }), 201
    
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/trainers/<int:id>', methods=['PUT'])
def update_trainer(id):
    """Update a trainer by ID"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM trainer WHERE trainer_id = %s", (id,))
        trainer = cursor.fetchone()
        
        if not trainer:
            return jsonify({"error": f"Trainer with ID {id} not found"}), 404
        
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
        
        if 'spesialisasi' in data:
            update_fields.append("spesialisasi = %s")
            values.append(data['spesialisasi'])
        
        if not update_fields:
            return jsonify({"error": "No valid fields to update"}), 400
        
        values.append(id)
        
        update_query = f"UPDATE trainer SET {', '.join(update_fields)} WHERE trainer_id = %s"
        cursor = conn.cursor()
        cursor.execute(update_query, values)
        conn.commit()
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM trainer WHERE trainer_id = %s", (id,))
        updated_trainer = cursor.fetchone()
        
        return jsonify(updated_trainer)
    
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/trainers/<int:id>', methods=['DELETE'])
def delete_trainer(id):
    """Delete a trainer by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT trainer_id FROM trainer WHERE trainer_id = %s", (id,))
        trainer = cursor.fetchone()
        
        if not trainer:
            return jsonify({"error": f"Trainer with ID {id} not found"}), 404
        
        cursor.execute("DELETE FROM trainer WHERE trainer_id = %s", (id,))
        conn.commit()
        
        return jsonify({"message": f"Trainer with ID {id} successfully deleted"})
    
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(port=5001, debug=True)