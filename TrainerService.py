from flask import Flask, jsonify, request

app = Flask(__name__)

# Data statis pelatih pribadi
trainers = {
    "1": {"id": "1", "name": "Johnny", "specialty": "Strength Training"},
    "2": {"id": "2", "name": "Lisa", "specialty": "Yoga"},
    "3": {"id": "3", "name": "Jeno", "specialty": "Body Combat"},
    "4": {"id": "4", "name": "Jennie", "specialty": "Pilates"},
    "5": {"id": "5", "name": "Jay", "specialty": "Body Building"}
}

@app.route('/trainers/<id>', methods=['GET'])
def get_trainer(id):
    """
    Mengambil data pelatih pribadi berdasarkan ID.
    Output: Data pelatih atau pesan error jika tidak ditemukan.
    """
    trainer = trainers.get(id, {})
    if not trainer:
        return jsonify({"error": f"Trainer with ID {id} not found"}), 404
    return jsonify(trainer)

@app.route('/trainers', methods=['POST'])
def add_trainer():
    """
    Menambahkan data pelatih pribadi baru.
    Input JSON: {"id": str, "name": str, "specialty": str}
    Output: Pesan sukses, status 201.
    """
    data = request.json
    required_fields = ['id', 'name', 'specialty']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields: id, name, specialty"}), 400

    if data['id'] in trainers:
        return jsonify({"error": "Trainer ID already exists"}), 409

    trainers[data['id']] = data
    return jsonify({"message": "Trainer added successfully"}), 201

if __name__ == '__main__':
    app.run(port=5001, debug=True)