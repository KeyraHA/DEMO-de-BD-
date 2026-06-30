# routes/prestamos.py
from flask import Blueprint, jsonify
from database import query

prestamos_bp = Blueprint('prestamos', __name__)

@prestamos_bp.route('/prestamos', methods=['GET'])
def get_prestamos():
    sql = """
        SELECT
            pp.id_prestamo,
            pp.monto_aprobado,
            pp.fecha_inicio,
            pp.plazo_meses,
            pp.estado_prestamo,
            p.nombre,
            p.apellido,
            p.nombre_documento AS dni,
            t.valor_tasa,
            t.tipo_tasa,
            t.frecuencia,
            e.resultado AS resultado_evaluacion,
            e.puntaje_riesgo
        FROM PrestamoPersonal pp
        JOIN Cliente c  ON pp.id_cliente   = c.id_cliente
        JOIN Persona p  ON c.id_persona    = p.id_persona
        JOIN Tasa t     ON pp.id_tasa      = t.id_tasa
        JOIN Evaluacion e ON pp.id_evaluacion = e.id_evaluacion
        ORDER BY pp.id_prestamo DESC
        LIMIT 200
    """
    rows = query(sql)
    return jsonify([dict(r) for r in rows])

@prestamos_bp.route('/prestamos/<int:id>/cronograma', methods=['GET'])
def get_cronograma(id):
    sql = """
        SELECT
            cu.id_cuota,
            cu.nro_cuota,
            cu.monto_total,
            cu.fecha_vencimiento,
            cu.fecha_pago,
            cu.estado_cuota,
            cr.periodicidad,
            cr.tipo_cronograma
        FROM Cuota cu
        JOIN CronogramaPagos cr ON cu.id_cronograma = cr.id_cronograma
        WHERE cr.id_prestamo = %s
        ORDER BY cu.nro_cuota
    """
    rows = query(sql, (id,))
    return jsonify([dict(r) for r in rows])

@prestamos_bp.route('/prestamos/stats', methods=['GET'])
def get_prestamos_stats():
    sql = """
        SELECT estado_prestamo, COUNT(*) AS total, SUM(monto_aprobado) AS monto_total
        FROM PrestamoPersonal
        GROUP BY estado_prestamo
    """
    rows = query(sql)
    return jsonify([dict(r) for r in rows])