#!/usr/bin/env python3
"""
Servidor de chat utilizando Web Sockets.
Autor: José Fausto Romero Lujambio
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from html import escape
from uuid import uuid4

import websockets as ws

logging.basicConfig(level=logging.INFO)

SOCKETS = set()


def info(socket) -> dict:
    """Obtener información del cliente conectado."""
    return {
        "id": socket.socket_id,
        "username": socket.username,
        "timestamp": int(1000 * datetime.now(timezone.utc).timestamp()),
    }


async def handler(socket):
    """
    Gestionar y procesar mensajes de clientes.
    Toda la comunicación se realiza mediante la serialización de objetos usando
    JSON.
    """
    socket.socket_id = str(uuid4())
    socket.username = None
    SOCKETS.add(socket)

    try:
        # enviar a cliente información sobre su conexión (incluyendo el UUID)
        # asignado
        await socket.send(json.dumps(info(socket)))

        # descodificar mensajes envíados por cada cliente
        async for json_packet in socket:
            try:
                client_packet = json.loads(json_packet)

                if socket.username:
                    if "message" in client_packet:
                        packet = info(socket) | {
                            "message": escape(client_packet["message"])
                        }
                        ws.broadcast(SOCKETS, json.dumps(packet))

                    else:
                        await socket.send(json.dumps({"error": True}))

                elif "username" in client_packet:
                    # sanitizar nombre de usuario
                    socket.username = escape(client_packet["username"][0:60])

                    packet = info(socket) | {"server": "connected"}
                    ws.broadcast(SOCKETS, json.dumps(packet))

                else:
                    logging.error(
                        'Cliente con id "%s" no tiene un nombre de usuario válido.',
                        socket.socket_id,
                    )

            except (json.JSONDecodeError, KeyError):
                logging.error(
                    'Cliente con id "%s" envió un mensaje inválido.', socket.socket_id
                )

        ws.broadcast(SOCKETS, json.dumps(info(socket) | {"server": "disconnected"}))
        await socket.wait_closed()
    finally:
        SOCKETS.remove(socket)


async def main():
    """Iniciar servidor de Web Sockets"""
    async with ws.serve(handler, "", 8765):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")
        sys.exit(-1)
