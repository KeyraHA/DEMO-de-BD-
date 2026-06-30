# routes/clientes.py
from flask import Blueprint, jsonify, request
from database import query

clientes_bp = Blueprint('clientes', __name__)

# GET todos los clientes con sus datos de persona
@clientes_bp.route('/clientes', methods=['GET'])
def get_clientes():
    sql = """
        SELECT
            c.id_cliente,
            p.nombre,
            p.apellido,
            p.tipo_documento,
            p.nombre_documento AS dni,
            p.correo,
            p.genero,
            p.f_nacimiento,
            c.celular,
            c.ingreso_mensual,
            c.score_crediticio,
            c.estado_cliente,
            c.fecha_registro,
            tc.nombre_tipo AS tipo_cliente
        FROM Cliente c
        JOIN Persona p       ON c.id_persona      = p.id_persona
        JOIN TipoCliente tc  ON c.id_tipo_cliente = tc.id_tipo_cliente
        ORDER BY c.id_cliente
    """
    rows = query(sql)
    return jsonify([dict(r) for r in rows])

# GET un cliente por id
@clientes_bp.route('/clientes/<int:id>', methods=['GET'])
def get_cliente(id):
    sql = """
        SELECT
            c.id_cliente,
            p.nombre, p.apellido,
            p.tipo_documento, p.nombre_documento AS dni,
            p.correo, p.genero, p.f_nacimiento,
            c.celular, c.ingreso_mensual,
            c.score_crediticio, c.estado_cliente,
            c.fecha_registro,
            tc.nombre_tipo AS tipo_cliente
        FROM Cliente c
        JOIN Persona p       ON c.id_persona      = p.id_persona
        JOIN TipoCliente tc  ON c.id_tipo_cliente = tc.id_tipo_cliente
        WHERE c.id_cliente = %s
    """
    row = query(sql, (id,), fetch='one')
    if not row:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    return jsonify(dict(row))

# GET estadísticas para el Dashboard
@clientes_bp.route('/clientes/stats', methods=['GET'])
def get_stats():
    total     = query("SELECT COUNT(*) AS total FROM Cliente", fetch='one')
    activos   = query("SELECT COUNT(*) AS total FROM Cliente WHERE estado_cliente = 'Activo'", fetch='one')
    morosos   = query("""
        SELECT COUNT(DISTINCT cu.id_cronograma) AS total
        FROM Cuota cu
        WHERE cu.estado_cuota = 'Vencida'
    """, fetch='one')
    prestamos = query("SELECT COUNT(*) AS total FROM PrestamoPersonal", fetch='one')
    pagos     = query("SELECT COUNT(*) AS total FROM Pago", fetch='one')

    return jsonify({
        'total_clientes':  total['total'],
        'clientes_activos': activos['total'],
        'morosos':         morosos['total'],
        'total_prestamos': prestamos['total'],
        'total_pagos':     pagos['total'],
    })