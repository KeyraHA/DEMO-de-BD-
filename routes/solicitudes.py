# routes/solicitudes.py
from flask import Blueprint, jsonify
from database import query

solicitudes_bp = Blueprint('solicitudes', __name__)

@solicitudes_bp.route('/solicitudes', methods=['GET'])
def get_solicitudes():
    sql = """
        SELECT
            s.id_solicitud,
            s.estado_solicitud,
            s.motivo_prestamo,
            s.monto_solicitud,
            s.fecha_solicitud,
            s.historial_crediticio,
            p.nombre,
            p.apellido,
            p.nombre_documento AS dni,
            c.score_crediticio,
            c.ingreso_mensual
        FROM Solicitud s
        JOIN Cliente c ON s.id_cliente = c.id_cliente
        JOIN Persona p ON c.id_persona = p.id_persona
        ORDER BY s.fecha_solicitud DESC
        LIMIT 200
    """
    rows = query(sql)
    return jsonify([dict(r) for r in rows])

@solicitudes_bp.route('/solicitudes/stats', methods=['GET'])
def get_solicitudes_stats():
    sql = """
        SELECT estado_solicitud, COUNT(*) AS total
        FROM Solicitud
        GROUP BY estado_solicitud
    """
    rows = query(sql)
    return jsonify([dict(r) for r in rows])