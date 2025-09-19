from abc import ABC, abstractmethod

class StorageProvider(ABC):
    """
    Abstract base class for storage providers.
    """
    @abstractmethod
    def save(self, content, filename, content_type='application/xml', source_url=None, who=None, what=None):
        """
        Saves content to the storage provider.
        """
        pass
