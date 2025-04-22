from flask import Flask, jsonify, request

app = Flask(__name__)

# Data statis pelanggan gym
customers = {
    "1": {"id": "1", "name": "Giselle", "membership_type": "Premium"},
    "2": {"id": "2", "name": "Winter", "membership_type": "Basic"},
    "3": {"id": "3", "name": "Suho", "membership_type": "Basic"},
    "4": {"id": "4", "name": "Dino", "membership_type": "Premium"},
    "5": {"id": "5", "name": "Bobby", "membership_type": "Premium"},
}

@app.route('/customers/<id>', methods=['GET'])
def get_customer(id):
    """
    Mengambil data pelanggan gym berdasarkan ID.
    Output: Data pelanggan atau pesan error jika tidak ditemukan.
    """
    customer = customers.get(id, {})
    if not customer:
        return jsonify({"error": f"Customer with ID {id} not found"}), 404
    return jsonify(customer)

@app.route('/customers', methods=['POST'])
def add_customer():
    """
    Menambahkan data pelanggan baru.
    Input JSON: {"id": str, "name": str, "membership_type": str}
    Output: Pesan sukses, status 201.
    """
    data = request.json
    required_fields = ['id', 'name', 'membership_type']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields: id, name, membership_type"}), 400

    if data['id'] in customers:
        return jsonify({"error": "Customer ID already exists"}), 409

    customers[data['id']] = data
    return jsonify({"message": "Customer added successfully"}), 201

if __name__ == '__main__':
    app.run(port=5000, debug=True)