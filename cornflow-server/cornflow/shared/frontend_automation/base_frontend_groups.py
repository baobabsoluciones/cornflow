from abc import ABC, abstractmethod
from typing import Union, Dict
from .frontend_automation import _get_logger


class BaseFrontendSection(ABC):
    def __init_subclass__(cls, **kwargs):
        """
        Checks that the subclass has defined the required properties.
        """
        super().__init_subclass__(**kwargs)
        if cls.title is None or cls.icon is None or cls.name is None:
            raise ValueError(
                f"Frontend section {cls.__name__} must define 'name', 'title', and 'icon' properties."
            )

    @property
    @abstractmethod
    def name(self):
        """Name of the frontend section."""
        pass

    @property
    @abstractmethod
    def title(self) -> Union[str, Dict[str, str]]:
        """
        Title of the frontend section.
        Can be a string or a dictionary with language codes as keys and translations as values.
        """
        pass

    @property
    @abstractmethod
    def icon(self) -> str:
        """Icon of the frontend section."""
        pass

    @property
    def order(self) -> int:
        """Order of the frontend section in the UI."""
        return 0


class BaseFrontendGroup(ABC):
    def __init_subclass__(cls, **kwargs):
        """
        Checks that the subclass has defined the required properties.
        """
        super().__init_subclass__(**kwargs)
        if cls.title is None or cls.icon is None or cls.name is None:
            raise ValueError(
                f"Frontend group {cls.__name__} must define 'name', 'title', and 'icon' properties."
            )

    @property
    @abstractmethod
    def name(self):
        """Name of the frontend group."""
        pass

    @property
    @abstractmethod
    def title(self) -> Union[str, Dict[str, str]]:
        """
        Title of the frontend group.
        Can be a string or a dictionary with language codes as keys and translations as values.
        """
        pass

    @property
    @abstractmethod
    def icon(self) -> str:
        """Icon of the frontend group."""
        pass

    @property
    @abstractmethod
    def frontend_section(self) -> BaseFrontendSection:
        """Frontend section the group will be shown in."""
        pass

    @property
    def order(self) -> int:
        """Order of the frontend group in the UI."""
        return 0


class BaseFrontendTable(ABC):
    def __init_subclass__(cls, **kwargs):
        """
        Checks that the subclass has defined the required properties.
        """
        super().__init_subclass__(**kwargs)
        logger = _get_logger()
        if cls.frontend_group is not None and cls.icon is not None:
            logger.warning(
                f"Frontend table {cls.__name__} has both 'frontend_group' and 'icon' defined. "
                f"'icon' will be ignored in favor of the icon from the frontend group."
            )
        if cls.frontend_group is None and cls.icon is None:
            logger.warning(
                f"Frontend table {cls.__name__} has neither 'frontend_group' nor 'icon' defined. "
                f"The frontend will use default values."
            )
        if cls.frontend_group is not None and cls.frontend_section is not None:
            logger.warning(
                f"Frontend table {cls.__name__} has both 'frontend_group' and 'frontend_section' defined. "
                "The frontend will use the frontend_group infos and ignore the frontend_section."
            )

    @property
    @abstractmethod
    def icon(self) -> str:
        """Icon of the frontend table."""
        pass

    @property
    @abstractmethod
    def title(self) -> Union[str, Dict[str, str]]:
        """
        Title of the frontend table.
        Can be a string or a dictionary with language codes as keys and translations as values.
        """
        pass

    @property
    @abstractmethod
    def frontend_group(self) -> BaseFrontendGroup:
        """Frontend group to which the table belongs."""
        pass

    @property
    @abstractmethod
    def frontend_section(self) -> BaseFrontendSection:
        """
        Frontend section to which the table belongs, in case it is not associated to
        any group
        """
        pass

    @property
    def order(self) -> int:
        """Order of the frontend table in the UI."""
        return 0

    @property
    @abstractmethod
    def schemas(self) -> list:
        """Schema list (e.g., ['ie_scheduling_dag', 'ie_scheduling_master_dag', 'ie_exams'])."""
        pass
