# Import from external libraries
from datetime import datetime
from flask import current_app
from flask_apispec import doc

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import ConnectionModel
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import SERVICE_ROLE


class ConnectionCleanupEndpoint(BaseMetaResource):
    """
    Endpoint used to clean up the unused images
    """

    ROLES_WITH_ACCESS = [SERVICE_ROLE]

    @doc(description="Delete expired connections", tags=["Internal"])
    @authenticate(auth_class=Auth())
    def delete(self):
        """
        API method to delete expired connections from the database.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by the superuser created for the airflow webserver
        """
        # Delete expired connections
        socketio = getattr(current_app, "__socketio_obj")
        disconnected = [
            conn
            for conn in ConnectionModel.get_all_objects()
            if conn.expiration <= datetime.utcnow()
        ]
        for conn in disconnected:
            socketio.disconnect(conn.session_id)
            conn.delete()
        count = len(disconnected)
        return {"message": f"{count} connections were deleted from the database"}, 200
