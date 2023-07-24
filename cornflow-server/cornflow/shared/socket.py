from datetime import datetime, timedelta
from flask import request
from flask_socketio import SocketIO

from cornflow.shared.authentication import Auth
from cornflow.models import ConnectionModel


def initialize_socket(socket_app: SocketIO):

    @socket_app.on('connect')
    def handle_connection():
        try:
            user = Auth().get_user_from_header(request.headers)
            ConnectionModel({"user_id": user.id, "session_id": request.sid}).save()
            return True
        except Exception as e:
            return False

    @socket_app.on('disconnect')
    def handle_disconnection():
        connections = ConnectionModel.get_all_objects(session_id=request.sid).all()
        for connection in connections:
            connection.delete()
        return True


def clean_disconnected():
    # Remove connections created more than a day ago
    disconnected = [
        conn
        for conn in ConnectionModel.get_all_objects()
        if conn.created_at <= datetime.utcnow() - timedelta(days=1)
    ]
    for conn in disconnected:
        conn.delete()

    return


def emit_socket(data, event=None, user_id=None):
    from flask import current_app
    socketio = getattr(current_app, "__socketio_obj")
    current_app.logger.info(
        f"Sending message '{data['text']}' "
        f"to {'all users' if user_id is None else 'user ' + str(user_id)}"
    )

    try:
        clean_disconnected()

        if event is None:
            if user_id is None:
                socketio.send(data=data)
                current_app.logger.info("Here: 0")
                return
            sessions_ids = [
                conn.session_id
                for conn in ConnectionModel.get_all_objects(user_id=user_id).all()
            ]
            for session_id in sessions_ids:
                socketio.send(data, to=session_id)
            current_app.logger.info("Here: 1")
            return

        if user_id is not None:
            sessions_ids = [
                conn.session_id
                for conn in ConnectionModel.get_all_objects(user_id=user_id).all()
            ]

            for session_id in sessions_ids:
                socketio.emit(event, data, to=session_id)
            current_app.logger.info("Here: 2")
            return
        socketio.emit(event, data)
        current_app.logger.info("Here: 3")
    except Exception as e:
        current_app.logger.info(str(e))
        raise e

