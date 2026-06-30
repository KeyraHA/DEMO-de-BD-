# routes/pagos.py
from flask import Blueprint, jsonify
from database import query

pagos_bp = Blueprint('pagos', __name__)

@pagos_bp.route('/pagos', methods=['GET'])
def get_pagos():
    sql = """
        SELECT
            pg.id_pago,
            pg.nro_cuota,
            pg.monto_pago,
            pg.fecha_pago,
            pg.tipo_pago,
            pg.numero_operacion,
            pg.estado_pago,
            p.nombre,
            p.apellido,
            mp.nombre_medio_pago,
            pp.id_prestamo,
            pp.monto_aprobado
        FROM Pago pg
        JOIN Cuota cu           ON pg.id_cuota      = cu.id_cuota
        JOIN CronogramaPagos cr ON cu.id_cronograma = cr.id_cronograma
        JOIN PrestamoPersonal pp ON cr.id_prestamo  = pp.id_prestamo
        JOIN Cliente c          ON pp.id_cliente    = c.id_cliente
        JOIN Persona p          ON c.id_persona     = p.id_persona
        JOIN MedioPago mp       ON pg.id_medio_pago = mp.id_medio_pago
        ORDER BY pg.fecha_pago DESC
        LIMIT 300
    """
    rows = query(sql)
    return jsonify([dict(r) for r in rows])

@pagos_bp.route('/moras', methods=['GET'])
def get_moras():
    sql = """
        SELECT
            m.id_mora,
            m.dias_atraso,
            m.monto_mora,
            m.fecha_calculo,
            m.dias_gracia,
            cu.nro_cuota,
            cu.monto_total,
            cu.fecha_vencimiento,
            p.nombre,
            p.apellido,
            pp.id_prestamo,
            pp.monto_aprobado
        FROM Mora m
        JOIN Cuota cu            ON m.id_cuota       = cu.id_cuota
        JOIN CronogramaPagos cr  ON cu.id_cronograma = cr.id_cronograma
        JOIN PrestamoPersonal pp ON cr.id_prestamo   = pp.id_prestamo
        JOIN Cliente c           ON pp.id_cliente    = c.id_cliente
        JOIN Persona p           ON c.id_persona     = p.id_persona
        ORDER BY m.dias_atraso DESC
        LIMIT 200
    """
    rows = query(sql)
    return jsonify([dict(r) for r in rows])

@pagos_bp.route('/pagos/stats', methods=['GET'])
def get_pagos_stats():
    total     = query("SELECT COUNT(*) AS total, SUM(monto_pago) AS monto FROM Pago", fetch='one')
    por_medio = query("""
        SELECT mp.nombre_medio_pago, COUNT(*) AS total, SUM(pg.monto_pago) AS monto
        FROM Pago pg
        JOIN MedioPago mp ON pg.id_medio_pago = mp.id_medio_pago
        GROUP BY mp.nombre_medio_pago
        ORDER BY total DESC
    """)
    return jsonify({
        'total_pagos': total['total'],
        'monto_total': float(total['monto'] or 0),
        'por_medio':   [dict(r) for r in por_medio],
    })