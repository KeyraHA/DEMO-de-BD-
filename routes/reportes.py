# routes/reportes.py
from flask import Blueprint, jsonify, request
from database import query

reportes_bp = Blueprint('reportes', __name__)

CONSULTAS = {
    'clientes_por_tipo': {
        'titulo': 'Clientes por tipo',
        'sql': """
            SELECT tc.nombre_tipo, COUNT(*) AS total
            FROM Cliente c
            JOIN TipoCliente tc ON c.id_tipo_cliente = tc.id_tipo_cliente
            GROUP BY tc.nombre_tipo ORDER BY total DESC
        """
    },
    'prestamos_por_estado': {
        'titulo': 'Préstamos por estado',
        'sql': """
            SELECT estado_prestamo, COUNT(*) AS total,
                   SUM(monto_aprobado) AS monto_total
            FROM PrestamoPersonal
            GROUP BY estado_prestamo ORDER BY total DESC
        """
    },
    'top_clientes_deuda': {
        'titulo': 'Top 10 clientes con mayor deuda',
        'sql': """
            SELECT p.nombre, p.apellido,
                   COUNT(pp.id_prestamo) AS num_prestamos,
                   SUM(pp.monto_aprobado) AS deuda_total
            FROM PrestamoPersonal pp
            JOIN Cliente c ON pp.id_cliente = c.id_cliente
            JOIN Persona p ON c.id_persona  = p.id_persona
            WHERE pp.estado_prestamo = 'Activo'
            GROUP BY p.nombre, p.apellido
            ORDER BY deuda_total DESC LIMIT 10
        """
    },
    'pagos_por_mes': {
        'titulo': 'Pagos por mes (último año)',
        'sql': """
            SELECT TO_CHAR(fecha_pago, 'YYYY-MM') AS mes,
                   COUNT(*) AS total_pagos,
                   SUM(monto_pago) AS monto_total
            FROM Pago
            WHERE fecha_pago >= NOW() - INTERVAL '12 months'
            GROUP BY mes ORDER BY mes
        """
    },
    'moras_por_rango': {
        'titulo': 'Moras por rango de días',
        'sql': """
            SELECT
                CASE
                    WHEN dias_atraso <= 30  THEN '1-30 días'
                    WHEN dias_atraso <= 60  THEN '31-60 días'
                    WHEN dias_atraso <= 90  THEN '61-90 días'
                    ELSE 'Más de 90 días'
                END AS rango,
                COUNT(*) AS total,
                SUM(monto_mora) AS monto_total
            FROM Mora
            GROUP BY rango ORDER BY MIN(dias_atraso)
        """
    },
    'solicitudes_por_mes': {
        'titulo': 'Solicitudes por mes (último año)',
        'sql': """
            SELECT TO_CHAR(fecha_solicitud, 'YYYY-MM') AS mes,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE estado_solicitud = 'Aprobada') AS aprobadas,
                   COUNT(*) FILTER (WHERE estado_solicitud = 'Rechazada') AS rechazadas
            FROM Solicitud
            WHERE fecha_solicitud >= NOW() - INTERVAL '12 months'
            GROUP BY mes ORDER BY mes
        """
    },
    'asesores_rendimiento': {
        'titulo': 'Rendimiento de asesores',
        'sql': """
            SELECT pa.nombre, pa.apellido,
                   COUNT(e.id_evaluacion) AS total_evaluaciones,
                   COUNT(*) FILTER (WHERE e.resultado = 'Aprobado') AS aprobadas,
                   COUNT(*) FILTER (WHERE e.resultado = 'Rechazado') AS rechazadas,
                   ROUND(AVG(e.puntaje_riesgo)::numeric, 2) AS puntaje_promedio
            FROM Evaluacion e
            JOIN Asesor a   ON e.id_asesor  = a.id_asesor
            JOIN Persona pa ON a.id_persona = pa.id_persona
            GROUP BY pa.nombre, pa.apellido
            ORDER BY total_evaluaciones DESC LIMIT 15
        """
    },
    'distribucion_tasas': {
        'titulo': 'Distribución por tipo de tasa',
        'sql': """
            SELECT t.tipo_tasa, t.frecuencia,
                   COUNT(pp.id_prestamo) AS total_prestamos,
                   ROUND(AVG(pp.monto_aprobado)::numeric, 2) AS monto_promedio
            FROM PrestamoPersonal pp
            JOIN Tasa t ON pp.id_tasa = t.id_tasa
            GROUP BY t.tipo_tasa, t.frecuencia
            ORDER BY total_prestamos DESC
        """
    },
}

@reportes_bp.route('/reportes/consultas', methods=['GET'])
def get_consultas():
    return jsonify([
        {'id': k, 'titulo': v['titulo']}
        for k, v in CONSULTAS.items()
    ])

@reportes_bp.route('/reportes/ejecutar/<consulta_id>', methods=['GET'])
def ejecutar_consulta(consulta_id):
    if consulta_id not in CONSULTAS:
        return jsonify({'error': 'Consulta no encontrada'}), 404
    consulta = CONSULTAS[consulta_id]
    rows = query(consulta['sql'])
    return jsonify({
        'titulo':   consulta['titulo'],
        'columnas': list(rows[0].keys()) if rows else [],
        'datos':    [dict(r) for r in rows],
    })