# AWS-CSM Selected Sender Write Port

Authority: [../../../docs/wiki/separation_and_responsibility.md](../../../docs/wiki/separation_and_responsibility.md)

`micyte/ports/aws_narrow_write/` defines one bounded internal write seam used by the unified `AWS-CSM` service tool.

This port is not a public portal tool contract.

Implemented in this slice:

- one request contract for updating the selected verified sender on one canonical newsletter operational profile
- one confirmation result contract that returns the updated source payload
- one write-only protocol with no provider-control expansion

Not implemented in this slice:

- provisioning writes
- manual newsletter send
- raw credential editing
- broad provider-admin mutation surfaces
