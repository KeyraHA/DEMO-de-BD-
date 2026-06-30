# routes/flujo_prestamo.py
# Flujo completo: Registrar cliente real → solicitud → evaluación → préstamo
from flask import Blueprint, jsonify, request
from database import get_connection
import psycopg2.extras
from datetime import date, timedelta

flujo_bp = Blueprint('flujo', __name__)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def next_id(cursor, tabla, campo_pk):
    cursor.execute(f"SELECT COALESCE(MAX({campo_pk}), 0) + 1 FROM {tabla}")
    return cursor.fetchone()[0]


def clasificar_tipo_cliente(ingreso_mensual: float) -> int:
    """
    1 = Banca Personas (Retail)      → ingreso < 12 000
    2 = Pequeña Empresa (Negocios)   → 12 000 ≤ ingreso < 80 000
    3 = Corporate                    → ingreso ≥ 80 000
    """
    if ingreso_mensual >= 80_000:
        return 3
    elif ingreso_mensual >= 12_000:
        return 2
    return 1


def calcular_score(ingreso_mensual: float, historial: str) -> float:
    """Score simple basado en ingreso + historial para la demo."""
    base = min(ingreso_mensual / 100, 400)   # máx 400 pts por ingreso
    bonus = {"bueno": 200, "regular": 100, "malo": 0}.get(historial.lower(), 50)
    return round(min(300 + base + bonus, 850), 2)


def evaluar_solicitud(monto: float, ingreso: float, score: float, historial: str):
    """
    Lógica de negocio sencilla para la demo:
    - resultado:       'Aprobado' | 'Observado' | 'Rechazado'
    - capacidad_pago:  30 % del ingreso mensual
    - puntaje_riesgo:  0-100  (100 = sin riesgo)
    """
    capacidad_pago = round(ingreso * 0.30, 2)
    puntaje_riesgo = round((score - 300) / 550 * 100, 2)   # normaliza 300-850 → 0-100

    if score >= 650 and monto <= capacidad_pago * 24:
        resultado = "Aprobado"
    elif score >= 500 and monto <= capacidad_pago * 36:
        resultado = "Observado"
    else:
        resultado = "Rechazado"

    observacion = (
        f"Score {score:.0f}. Capacidad de pago estimada: S/ {capacidad_pago:.2f}/mes."
    )
    return resultado, capacidad_pago, puntaje_riesgo, observacion


# ─────────────────────────────────────────────
# PASO 1 — Registrar cliente nuevo
# POST /api/flujo/cliente
# ─────────────────────────────────────────────

@flujo_bp.route('/flujo/cliente', methods=['POST'])
def registrar_cliente():
    """
    Body JSON esperado:
    {
      "nombre":          "Juan",
      "apellido":        "Pérez",
      "tipo_documento":  "DNI",          // DNI | Pasaporte | CE
      "nombre_documento":"12345678",
      "genero":          "M",            // M | F
      "f_nacimiento":    "1990-05-15",
      "correo":          "juan@mail.com",
      "celular":         "987654321",
      "ingreso_mensual": 3500.00
    }
    """
    data = request.get_json(force=True)

    required = ["nombre", "apellido", "tipo_documento", "nombre_documento",
                "genero", "f_nacimiento", "correo", "celular", "ingreso_mensual"]
    missing = [f for f in required if f not in data or str(data[f]).strip() == ""]
    if missing:
        return jsonify({"error": f"Campos faltantes: {', '.join(missing)}"}), 400

    ingreso = float(data["ingreso_mensual"])
    id_tipo = clasificar_tipo_cliente(ingreso)
    score   = calcular_score(ingreso, "bueno")   # historial "bueno" por defecto al crear

    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Verificar DNI duplicado
        cur.execute(
            "SELECT id_persona FROM Persona WHERE nombre_documento = %s AND tipo_documento = %s",
            (data["nombre_documento"], data["tipo_documento"])
        )
        if cur.fetchone():
            return jsonify({"error": "Ya existe una persona con ese documento."}), 409

        id_persona = next_id(cur, "Persona", "id_persona")
        id_cliente = next_id(cur, "Cliente", "id_cliente")

        cur.execute("""
            INSERT INTO Persona
                (id_persona, tipo_documento, nombre_documento, genero, nombre, apellido, f_nacimiento, correo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_persona,
            data["tipo_documento"],
            data["nombre_documento"],
            data["genero"],
            data["nombre"],
            data["apellido"],
            data["f_nacimiento"],
            data["correo"],
        ))

        cur.execute("""
            INSERT INTO Cliente
                (id_cliente, id_persona, id_tipo_cliente, celular,
                 ingreso_mensual, score_crediticio, estado_cliente, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s, 'Activo', %s)
        """, (
            id_cliente,
            id_persona,
            id_tipo,
            data["celular"],
            ingreso,
            score,
            date.today().isoformat(),
        ))

        conn.commit()
        return jsonify({
            "mensaje":     "Cliente registrado correctamente",
            "id_cliente":  id_cliente,
            "id_persona":  id_persona,
            "tipo_cliente": id_tipo,
            "score_crediticio": score,
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# PASO 2 — Crear solicitud de préstamo
# POST /api/flujo/solicitud
# ─────────────────────────────────────────────

@flujo_bp.route('/flujo/solicitud', methods=['POST'])
def crear_solicitud():
    """
    Body JSON esperado:
    {
      "id_cliente":          1,
      "monto_solicitud":     10000.00,
      "motivo_prestamo":     "Consumo",    // Consumo | Capital de Trabajo | Vehicular | Salud
      "historial_crediticio":"El cliente cuenta con comportamiento de pago óptimo."
    }
    """
    data = request.get_json(force=True)

    required = ["id_cliente", "monto_solicitud", "motivo_prestamo"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Campos faltantes: {', '.join(missing)}"}), 400

    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Verificar que el cliente existe
        cur.execute("SELECT id_cliente, ingreso_mensual, score_crediticio FROM Cliente WHERE id_cliente = %s",
                    (data["id_cliente"],))
        cliente = cur.fetchone()
        if not cliente:
            return jsonify({"error": "Cliente no encontrado"}), 404

        monto  = float(data["monto_solicitud"])
        ingreso = float(cliente["ingreso_mensual"])
        score   = float(cliente["score_crediticio"])

        # Pre-evaluar para asignar estado
        resultado, _, _, _ = evaluar_solicitud(
            monto, ingreso, score,
            data.get("historial_crediticio", "bueno")
        )
        estado_map = {"Aprobado": "Aprobada", "Observado": "Pendiente", "Rechazado": "Rechazada"}
        estado_sol = estado_map[resultado]

        id_solicitud = next_id(cur, "Solicitud", "id_solicitud")

        cur.execute("""
            INSERT INTO Solicitud
                (id_solicitud, id_cliente, estado_solicitud, motivo_prestamo,
                 monto_solicitud, historial_crediticio, fecha_solicitud)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            id_solicitud,
            data["id_cliente"],
            estado_sol,
            data["motivo_prestamo"],
            monto,
            data.get("historial_crediticio", "El cliente cuenta con comportamiento de pago óptimo."),
            date.today().isoformat(),
        ))

        conn.commit()
        return jsonify({
            "mensaje":       "Solicitud creada correctamente",
            "id_solicitud":  id_solicitud,
            "estado_solicitud": estado_sol,
            "pre_evaluacion": resultado,
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# PASO 3 — Evaluar solicitud (auto o manual)
# POST /api/flujo/evaluacion
# ─────────────────────────────────────────────

@flujo_bp.route('/flujo/evaluacion', methods=['POST'])
def evaluar():
    """
    Body JSON esperado:
    {
      "id_solicitud": 1,
      "id_asesor":    1        // Si no se envía, usa el asesor con id=1
    }
    Devuelve la evaluación creada con resultado y si fue aprobada.
    """
    data = request.get_json(force=True)

    if "id_solicitud" not in data:
        return jsonify({"error": "Falta id_solicitud"}), 400

    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Traer datos de la solicitud + cliente
        cur.execute("""
            SELECT s.id_solicitud, s.monto_solicitud, s.historial_crediticio,
                   c.ingreso_mensual, c.score_crediticio, c.id_cliente
            FROM Solicitud s
            JOIN Cliente c ON s.id_cliente = c.id_cliente
            WHERE s.id_solicitud = %s
        """, (data["id_solicitud"],))
        sol = cur.fetchone()
        if not sol:
            return jsonify({"error": "Solicitud no encontrada"}), 404

        # Verificar que no tenga ya una evaluación
        cur.execute("SELECT id_evaluacion FROM Evaluacion WHERE id_solicitud = %s", (data["id_solicitud"],))
        if cur.fetchone():
            return jsonify({"error": "Esta solicitud ya tiene una evaluación registrada"}), 409

        # Obtener asesor (usa el enviado o el primero activo disponible)
        id_asesor = data.get("id_asesor")
        if not id_asesor:
            cur.execute("SELECT id_asesor FROM Asesor WHERE estado_asesor = 'Activo' LIMIT 1")
            asesor = cur.fetchone()
            if not asesor:
                return jsonify({"error": "No hay asesores activos en el sistema"}), 500
            id_asesor = asesor["id_asesor"]

        resultado, capacidad, puntaje, observacion = evaluar_solicitud(
            float(sol["monto_solicitud"]),
            float(sol["ingreso_mensual"]),
            float(sol["score_crediticio"]),
            sol["historial_crediticio"] or "regular",
        )

        id_evaluacion = next_id(cur, "Evaluacion", "id_evaluacion")
        f_evaluacion  = (date.today() + timedelta(days=1)).isoformat()

        cur.execute("""
            INSERT INTO Evaluacion
                (id_evaluacion, id_asesor, id_solicitud, resultado, capacidad_pago,
                 estado_evaluacion, observaciones, fecha_evaluacion, puntaje_riesgo)
            VALUES (%s, %s, %s, %s, %s, 'Completado', %s, %s, %s)
        """, (
            id_evaluacion,
            id_asesor,
            data["id_solicitud"],
            resultado,
            capacidad,
            observacion,
            f_evaluacion,
            puntaje,
        ))

        conn.commit()
        return jsonify({
            "mensaje":        "Evaluación registrada",
            "id_evaluacion":  id_evaluacion,
            "resultado":      resultado,
            "capacidad_pago": float(capacidad),
            "puntaje_riesgo": float(puntaje),
            "observaciones":  observacion,
            "aprobado":       resultado == "Aprobado",
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# PASO 4 — Aprobar y crear préstamo
# POST /api/flujo/prestamo
# ─────────────────────────────────────────────

@flujo_bp.route('/flujo/prestamo', methods=['POST'])
def crear_prestamo():
    """
    Body JSON esperado:
    {
      "id_evaluacion": 1,
      "plazo_meses":   12,     // 6 | 12 | 18 | 24 | 36 | 48 | 60
      "id_tasa":       1       // id de la tasa en tabla Tasa (opcional, usa la primera si no se envía)
    }
    Solo funciona si la evaluación tiene resultado = 'Aprobado'.
    Crea el PrestamoPersonal + CronogramaPagos + Cuotas.
    """
    data = request.get_json(force=True)

    if "id_evaluacion" not in data or "plazo_meses" not in data:
        return jsonify({"error": "Faltan campos: id_evaluacion, plazo_meses"}), 400

    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Validar evaluación
        cur.execute("""
            SELECT e.id_evaluacion, e.resultado, s.id_cliente, s.monto_solicitud
            FROM Evaluacion e
            JOIN Solicitud s ON e.id_solicitud = s.id_solicitud
            WHERE e.id_evaluacion = %s
        """, (data["id_evaluacion"],))
        ev = cur.fetchone()
        if not ev:
            return jsonify({"error": "Evaluación no encontrada"}), 404
        if ev["resultado"] != "Aprobado":
            return jsonify({"error": f"No se puede crear préstamo: evaluación está '{ev['resultado']}'"}), 400

        # Verificar que no exista ya un préstamo para esta evaluación
        cur.execute("SELECT id_prestamo FROM PrestamoPersonal WHERE id_evaluacion = %s", (data["id_evaluacion"],))
        if cur.fetchone():
            return jsonify({"error": "Ya existe un préstamo para esta evaluación"}), 409

        # Obtener tasa
        id_tasa = data.get("id_tasa")
        if not id_tasa:
            cur.execute("SELECT id_tasa, valor_tasa FROM Tasa LIMIT 1")
            tasa_row = cur.fetchone()
            if not tasa_row:
                return jsonify({"error": "No hay tasas configuradas en el sistema"}), 500
            id_tasa    = tasa_row["id_tasa"]
            valor_tasa = float(tasa_row["valor_tasa"])
        else:
            cur.execute("SELECT valor_tasa FROM Tasa WHERE id_tasa = %s", (id_tasa,))
            tasa_row = cur.fetchone()
            if not tasa_row:
                return jsonify({"error": "Tasa no encontrada"}), 404
            valor_tasa = float(tasa_row["valor_tasa"])

        plazo      = int(data["plazo_meses"])
        monto      = float(ev["monto_solicitud"])
        id_cliente = ev["id_cliente"]
        f_inicio   = date.today()

        # Cuota mensual (amortización francesa)
        tasa_m = valor_tasa / 100 / 12
        if tasa_m > 0:
            cuota_mensual = round(monto * tasa_m / (1 - (1 + tasa_m) ** -plazo), 2)
        else:
            cuota_mensual = round(monto / plazo, 2)

        # Crear préstamo
        id_prestamo = next_id(cur, "PrestamoPersonal", "id_prestamo")
        cur.execute("""
            INSERT INTO PrestamoPersonal
                (id_prestamo, id_cliente, id_evaluacion, id_aval, id_tasa,
                 monto_aprobado, fecha_inicio, plazo_meses, estado_prestamo)
            VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, 'Activo')
        """, (id_prestamo, id_cliente, data["id_evaluacion"], id_tasa, monto, f_inicio.isoformat(), plazo))

        # Crear cronograma
        id_cronograma = next_id(cur, "CronogramaPagos", "id_cronograma")
        cur.execute("""
            INSERT INTO CronogramaPagos
                (id_cronograma, id_prestamo, periodicidad, tipo_cronograma)
            VALUES (%s, %s, 'Mensual', 'Frances')
        """, (id_cronograma, id_prestamo))

        # Crear cuotas
        id_cuota_base = next_id(cur, "Cuota", "id_cuota")
        cuotas = []
        for n in range(1, plazo + 1):
            f_vence = (f_inicio.replace(day=1) + timedelta(days=32 * n)).replace(day=f_inicio.day)
            cuotas.append((
                id_cuota_base + n - 1,
                id_cronograma,
                n,
                cuota_mensual,
                f_vence.isoformat(),
                None,          # fecha_pago
                'Pendiente',
            ))

        cur.executemany("""
            INSERT INTO Cuota
                (id_cuota, id_cronograma, nro_cuota, monto_total, fecha_vencimiento, fecha_pago, estado_cuota)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, cuotas)

        conn.commit()
        return jsonify({
            "mensaje":        "Préstamo creado exitosamente",
            "id_prestamo":    id_prestamo,
            "id_cronograma":  id_cronograma,
            "monto_aprobado": monto,
            "plazo_meses":    plazo,
            "cuota_mensual":  cuota_mensual,
            "total_cuotas":   plazo,
            "fecha_inicio":   f_inicio.isoformat(),
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# EXTRA — Consultas de apoyo para el flujo
# ─────────────────────────────────────────────

@flujo_bp.route('/flujo/tasas', methods=['GET'])
def get_tasas():
    """Lista todas las tasas disponibles."""
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT id_tasa, tipo_tasa, frecuencia, valor_tasa FROM Tasa ORDER BY id_tasa")
        rows = cur.fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        cur.close()
        conn.close()


@flujo_bp.route('/flujo/asesores', methods=['GET'])
def get_asesores():
    """Lista asesores activos."""
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT a.id_asesor, p.nombre, p.apellido, a.estado_asesor
            FROM Asesor a
            JOIN Persona p ON a.id_persona = p.id_persona
            WHERE a.estado_asesor = 'Activo'
            ORDER BY a.id_asesor
        """)
        rows = cur.fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        cur.close()
        conn.close()


@flujo_bp.route('/flujo/cliente/<string:dni>', methods=['GET'])
def buscar_cliente_dni(dni):
    """Busca un cliente por número de documento."""
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT c.id_cliente, p.nombre, p.apellido,
                   p.tipo_documento, p.nombre_documento AS dni,
                   p.correo, c.celular, c.ingreso_mensual,
                   c.score_crediticio, c.estado_cliente,
                   tc.nombre_tipo AS tipo_cliente
            FROM Cliente c
            JOIN Persona p      ON c.id_persona      = p.id_persona
            JOIN TipoCliente tc ON c.id_tipo_cliente = tc.id_tipo_cliente
            WHERE p.nombre_documento = %s
        """, (dni,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Cliente no encontrado"}), 404
        return jsonify(dict(row))
    finally:
        cur.close()
        conn.close()