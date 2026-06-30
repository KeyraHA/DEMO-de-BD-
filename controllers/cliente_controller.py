from flask import jsonify, request
from models.cliente_model import ClienteModel


class ClienteController:

    # ...

    @staticmethod
    def crear_cliente():

        data = request.get_json()

        respuesta = ClienteModel.crear_cliente(data)

        return jsonify(respuesta)