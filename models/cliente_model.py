from database import get_connection


class ClienteModel:

    # ... aquí ya tienes obtener_clientes()

    @staticmethod
    def crear_cliente(data):

        conn = get_connection()
        cursor = conn.cursor()

        try:

            # Obtener nuevo id_persona
            cursor.execute("""
                SELECT COALESCE(MAX(id_persona),0)+1
                FROM persona;
            """)

            id_persona = cursor.fetchone()[0]

            # Obtener nuevo id_cliente
            cursor.execute("""
                SELECT COALESCE(MAX(id_cliente),0)+1
                FROM cliente;
            """)

            id_cliente = cursor.fetchone()[0]

            # Insertar Persona
            cursor.execute("""
                INSERT INTO persona(
                    id_persona,
                    tipo_documento,
                    nombre_documento,
                    genero,
                    nombre,
                    apellido,
                    f_nacimiento,
                    correo
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (

                id_persona,
                data["tipo_documento"],
                data["nombre_documento"],
                data["genero"],
                data["nombre"],
                data["apellido"],
                data["f_nacimiento"],
                data["correo"]

            ))

            # Insertar Cliente
            cursor.execute("""
                INSERT INTO cliente(
                    id_cliente,
                    id_persona,
                    id_tipo_cliente,
                    score_crediticio,
                    celular,
                    fecha_registro,
                    estado_cliente,
                    ingreso_mensual
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (

                id_cliente,
                id_persona,
                data["id_tipo_cliente"],
                data["score_crediticio"],
                data["celular"],
                data["fecha_registro"],
                data["estado_cliente"],
                data["ingreso_mensual"]

            ))

            conn.commit()

            return {
                "mensaje": "Cliente creado correctamente"
            }

        except Exception as e:

            conn.rollback()

            return {
                "error": str(e)
            }

        finally:

            cursor.close()
            conn.close()