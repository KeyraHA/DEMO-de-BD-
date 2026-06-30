# routes/evaluaciones.py
from flask import Blueprint, jsonify
from database import query

evaluaciones_bp = Blueprint('evaluaciones', __name__)

@evaluaciones_bp.route('/evaluaciones', methods=['GET'])
def get_evaluaciones():
    sql = """
        SELECT
            e.id_evaluacion,
            e.resultado,
            e.capacidad_pago,
            e.estado_evaluacion,
            e.observaciones,
            e.fecha_evaluacion,
            e.puntaje_riesgo,
            s.monto_solicitud,
            s.motivo_prestamo,
            p.nombre,
            p.apellido,
            pa.nombre AS nombre_asesor,
            pa.apellido AS apellido_asesor
        FROM Evaluacion e
        JOIN Solicitud s   ON e.id_solicitud = s.id_solicitud
        JOIN Cliente c     ON s.id_cliente   = c.id_cliente
        JOIN Persona p     ON c.id_persona   = p.id_persona
        JOIN Asesor a      ON e.id_asesor    = a.id_asesor
        JOIN Persona pa    ON a.id_persona   = pa.id_persona
        ORDER BY e.fecha_evaluacion DESC
        LIMIT 200
    """
    rows = query(sql)
    return jsonify([dict(r) for r in rows])