#!/usr/bin/env python3
"""
Servidor de chat utilizando Web Sockets.
Autor: José Fausto Romero Lujambio
"""

import asyncio
import json
import logging
import signal
import sys
from collections import deque
from datetime import datetime, timezone
from html import escape
from uuid import uuid4

import websockets as ws

logging.basicConfig(level=logging.INFO)

LOGGER = {
    "malformed_message": 'cliente con id "%s" envió un mensaje inválido',
    "invalid_username": 'cliente con id "%s" no tiene un nombre de usuario válido',
    "remaining": "hay %d clientes conectados",
}

SOCKETS = set()
HISTORY = deque(maxlen=1000)  # limitar entradas en el historial


def info(socket) -> dict:
    """Obtener información del cliente conectado."""
    return {
        "id": socket.socket_id,
        "username": socket.username,
        "timestamp": int(1000 * datetime.now(timezone.utc).timestamp()),
    }


def broadcast(packet):
    """Difundir mensaje a clientes conectados."""
    HISTORY.append(packet)  # guardar mensaje en historial
    ws.broadcast(SOCKETS, json.dumps(packet))


async def send_history(socket):
    """Enviar el historial de la sala a un cliente."""
    for packet in HISTORY:
        await socket.send(json.dumps(packet))


async def handler(socket):
    """
    Gestionar y procesar mensajes de clientes.
    Toda la comunicación se realiza mediante la serialización de objetos usando
    JSON.
    """
    socket.socket_id = str(uuid4())  # asignar un UUID a cada socket conectado
    socket.username = None  # esperar a que el cliente informe su nombre

    SOCKETS.add(socket)
    logging.info(LOGGER["remaining"], len(SOCKETS))  # mostrar conexiones activas

    try:
        # enviar a cliente información sobre su conexión (incluyendo el UUID)
        # asignado
        await socket.send(json.dumps(info(socket)))

        # enviar los mensajes en el historial al nuevo cliente conectado
        await send_history(socket)

        # descodificar mensajes envíados por cada cliente
        async for json_packet in socket:
            try:
                client_packet = json.loads(json_packet)

                if socket.username:
                    if "message" in client_packet:
                        packet = info(socket) | {
                            # sanitizar mensaje, limitar a 200 caracteres
                            "message": escape(client_packet["message"][0:200])
                        }
                        broadcast(packet)

                    else:
                        await socket.send(json.dumps({"error": True}))

                elif "username" in client_packet:
                    # sanitizar nombre de usuario, limitar a 60 caracteres
                    socket.username = escape(client_packet["username"][0:60])

                    packet = info(socket) | {"server": "connected"}
                    broadcast(packet)

                else:
                    logging.error(LOGGER["invalid_username"], socket.socket_id)

            except (json.JSONDecodeError, KeyError):
                logging.error(LOGGER["malformed_message"], socket.socket_id)

        # enviar mensaje de desconexión justo antes de terminar la sesión
        broadcast(info(socket) | {"server": "disconnected"})
        await socket.wait_closed()

    finally:
        SOCKETS.remove(socket)  # quitar socket de conexión terminada
        logging.info(LOGGER["remaining"], len(SOCKETS))


async def main():
    """Iniciar servidor de Web Sockets"""
    async with ws.serve(handler, "0.0.0.0", 8080):
        await asyncio.Future()  # run forever


def exit_app(signum, frame):
    print("Exiting...")
    sys.exit(-1)


if __name__ == "__main__":
    # registrar gestor de señales
    signal.signal(signal.SIGINT, exit_app)
    signal.signal(signal.SIGTERM, exit_app)

    # iniciar bucle principal de ejecución
    asyncio.run(main())
