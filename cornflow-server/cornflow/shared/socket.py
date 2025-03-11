from flask import request
from flask_socketio import SocketIO

from cornflow.shared.authentication import Auth
from cornflow.models import ConnectionModel, UserModel


def initialize_socket(socket_app: SocketIO):

    @socket_app.on("connect")
    def handle_connection(auth):
        from flask import current_app

        current_app.logger.info("Connection attempt")

        try:
            token = auth.get("token")
            decoded_token = Auth().decode_token(token)
            user_id = decoded_token["user_id"]
            current_app.logger.info("User authenticated")
            ConnectionModel(
                {
                    "user_id": user_id,
                    "session_id": request.sid,
                    "expires_at": decoded_token["expiration"],
                }
            ).save()
            current_app.logger.info("Returning True")
            return True
        except Exception as e:
            current_app.logger.info(f"Returning False: {e}")
            return False

    @socket_app.on("disconnect")
    def handle_disconnection():
        from flask import current_app

        current_app.logger.info(f"User with sid {request.sid} disconnected")
        connections = ConnectionModel.get_all_objects(session_id=request.sid).all()
        for connection in connections:
            connection.delete()
        return True


def emit_socket(data, event, user_id=None):
    from flask import current_app

    socketio = getattr(current_app, "__socketio_obj")
    current_app.logger.info(
        f"Sending message '{data['message']}' "
        f"to {'all users' if user_id is None else 'user ' + str(user_id)}"
    )

    try:
        if user_id is None:
            current_app.logger.info("Sending message to all connected devices")
            socketio.emit(event, data)
        else:
            # Sending message to all connected devices of a user.
            sessions_ids = [
                conn.session_id
                for conn in ConnectionModel.get_all_objects(user_id=user_id).all()
                if not conn.is_expired()
            ]
            current_app.logger.info(
                f"Sending message to {len(sessions_ids)} {'devices' if len(sessions_ids) > 1 else 'device'}"
            )
            for session_id in sessions_ids:
                socketio.emit(event, data, to=session_id)

    except Exception as e:
        current_app.logger.info(str(e))
        raise e
