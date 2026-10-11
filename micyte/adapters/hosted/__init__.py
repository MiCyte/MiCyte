"""A hosted service reached by key: the fills an instance binds to employ a host's mail
and website seams from a machine the host does not run.

The ports are MiCyte's (`micyte.ports.email_provider`, `micyte.ports.site_hosting`); what
is here is a transport — a base URL, an alias and the key the host minted for it — and two
adapters that speak the host's key door. Nothing here names a host: the base URL is the
credential's, and the door's shape (``<base>/<port>/<action>``) is the contract.
"""

from .credential import HostedServiceCredential, read_hosted_credential, write_hosted_credential
from .email import HostedEmailAdapter
from .site import HostedSiteAdapter
from .transport import HostedServiceClient, HostedServiceRefused

__all__ = [
    "HostedEmailAdapter",
    "HostedServiceClient",
    "HostedServiceCredential",
    "HostedServiceRefused",
    "HostedSiteAdapter",
    "read_hosted_credential",
    "write_hosted_credential",
]
