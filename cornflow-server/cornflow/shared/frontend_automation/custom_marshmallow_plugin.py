# Imports from external libraries
from apispec.ext.marshmallow import MarshmallowPlugin
from marshmallow import fields


class CustomMarshmallowPlugin(MarshmallowPlugin):
    """
    Custom Marshmallow plugin that extends the base MarshmallowPlugin
    to include additional metadata from field definitions in the OpenAPI schema.
    """

    def init_spec(self, spec):
        """Initialize the plugin with the APISpec instance."""
        super().init_spec(spec)

        # Add support for Time fields
        self.converter.field_mapping.update(
            {
                fields.Time: ("string", "time"),
            }
        )

        # Store the original field2property method
        original_field2property = self.converter.field2property

        def enhanced_field2property(field, **kwargs):
            """
            Enhanced field2property that includes additional metadata
            like join_from and columns_to_join.
            """
            # Get the base property from the original converter
            prop = original_field2property(field, **kwargs)

            # Add custom metadata if present
            if hasattr(field, "metadata") and field.metadata:
                metadata = field.metadata

                # Add all custom metadata (not just join_from and columns_to_join)
                for key, value in metadata.items():
                    # Skip standard OpenAPI properties that are already handled
                    if key not in ["title", "description", "default", "example"]:
                        prop[key] = value

            return prop

        # Replace the method with our enhanced version
        self.converter.field2property = enhanced_field2property
