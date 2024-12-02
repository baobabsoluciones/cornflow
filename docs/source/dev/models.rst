Models
==========================

Instance model
------------------

.. autoclass:: cornflow.models.InstanceModel
  :members: update
  :show-inheritance:
  :member-order: bysource


Execution model
------------------

.. autoclass:: cornflow.models.ExecutionModel
  :members: update, update_config, update_state, update_log_txt
  :show-inheritance:
  :member-order: bysource


Case model
-----------

.. autoclass:: cornflow.models.CaseModel
  :members: from_parent_id, patch, update, move_to, apply_patch, 
  :show-inheritance:
  :member-order: bysource


User model
------------------

.. autoclass:: cornflow.models.UserModel
  :members: update, comes_from_external_provider, check_hash, get_all_users, get_one_user, get_one_user_by_email, get_one_user_by_username, check_username_in_use, generate_random_password, is_admin, is_service_user
  :show-inheritance:
  :member-order: bysource
   



