# app.py  — agrega la línea marcada con ← NUEVO
from flask import Flask, jsonify
from flask_cors import CORS
from routes.clientes     import clientes_bp
from routes.prestamos    import prestamos_bp
from routes.pagos        import pagos_bp
from routes.solicitudes  import solicitudes_bp
from routes.evaluaciones import evaluaciones_bp
from routes.reportes     import reportes_bp
from routes.flujo_prestamo import flujo_bp          # ← NUEVO

app = Flask(__name__)
CORS(app)

app.register_blueprint(clientes_bp,     url_prefix='/api')
app.register_blueprint(prestamos_bp,    url_prefix='/api')
app.register_blueprint(pagos_bp,        url_prefix='/api')
app.register_blueprint(solicitudes_bp,  url_prefix='/api')
app.register_blueprint(evaluaciones_bp, url_prefix='/api')
app.register_blueprint(reportes_bp,     url_prefix='/api')
app.register_blueprint(flujo_bp,        url_prefix='/api')   # ← NUEVO

@app.route('/api/ping')
def ping():
    return jsonify({'mensaje': 'Flask funcionando ✅'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)